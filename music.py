import pygame
import os
import time
import threading
from mutagen import mp3
import platform
import logging
if platform.system() == "Windows":
    from fake_rpi.RPi import GPIO
else:
    import RPi.GPIO as GPIO
    
# Konfiguracja logowania dla modułu music
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class musicHandling: 
    """
    Klasa odpowiedzialna za odtwarzanie dźwięków dzwonków, przeddzwonków i alarmów,
    oraz sterowanie przekaźnikiem wzmacniacza.
    """
    def __init__(self, filesPath, AMP_OUTPUT_PIN):
        pygame.mixer.init()
        self.AMP_OUTPUT_PIN = AMP_OUTPUT_PIN
        self.soundFilesPath = filesPath
        self._sampleSoundLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Files/DomyslnyDzwiek.mp3")
        
        self._play_lock = threading.Lock() 
        self._is_alarm_playing = False 
        self._is_bell_playing = False
        self._is_prebell_playing = False
        threading.Thread(target=self._update_audio_loop, daemon=True).start()

    def _update_audio_loop(self):
        """
        Pętla do aktualizacji plików dźwiękowych
        """
        while True:
            self._musicFileBell = self._find_mp3_file("1")
            self._musicFilePrebell = self._find_mp3_file("2")
            self._musicFileAlarm = self._find_mp3_file("0")

            # Upewnij się, że nazwy plików są poprawne, nawet jeśli plik nie został znaleziony
            self.musicFileNameBell = os.path.basename(self._musicFileBell) if self._musicFileBell else "Brak pliku"
            self.musicFileNamePrebell = os.path.basename(self._musicFilePrebell) if self._musicFilePrebell else "Brak pliku"
            self.musicFileNameAlarm = os.path.basename(self._musicFileAlarm) if self._musicFileAlarm else "Brak pliku"
            time.sleep(5)

    def _find_mp3_file(self, start_letter):
        """
        Szuka pliku MP3 zaczynającego się na daną literę w katalogu soundFilesPath.
        Zwraca pełną ścieżkę do pliku lub domyślny plik/None jeśli nie znaleziono.
        """
        for root, dirs, files in os.walk(self.soundFilesPath):
            for filename in files:
                if filename.lower().endswith(".mp3") and filename.startswith(start_letter):
                    file_path = os.path.join(root, filename)
                    if os.path.exists(file_path):
                        logger.info(f"Znaleziono plik dla '{start_letter}': {file_path}")
                        return file_path
        logger.warning(f"Nie znaleziono pliku MP3 zaczynającego się na '{start_letter}' w lokalizacji {self.soundFilesPath}. Użycie domyślnego: {self._sampleSoundLocation}")
        if os.path.exists(self._sampleSoundLocation):
            return self._sampleSoundLocation
        else:
            logger.error(f"Domyślny plik dźwiękowy nie istnieje: {self._sampleSoundLocation}")
            return None # Zwróć None, jeśli nawet domyślny plik jest niedostępny


    def _get_mp3_length(self, file_path):
        """Zwraca długość pliku MP3 w sekundach."""
        if not file_path or not os.path.exists(file_path):
            return 0
        try:
            audio = mp3.Open(file_path)
            return audio.info.length
        except Exception as e:
            logger.error(f"Błąd odczytu długości pliku MP3 {file_path}: {e}")
            return 0 

    def _amp_relay(self, state: bool):
        """
        Steruje przekaźnikiem wzmacniacza.
        Na Windowsie tylko symuluje działanie. Na Linuksie próbuje użyć `gpio` (wymaga WiringPi).
        """
        if platform.system() == "Windows":
            logger.info(f"Symulacja: Przekaźnik wzmacniacza ustawiony na: {'Włączony' if state else 'Wyłączony'}")
        else:
            try:
                GPIO.setmode(GPIO.BOARD)
                GPIO.setup(self.AMP_OUTPUT_PIN, GPIO.OUT)
                GPIO.output(self.AMP_OUTPUT_PIN, GPIO.HIGH if state else GPIO.LOW)
                logger.info(f"Przekaźnik wzmacniacza GPIO {self.AMP_OUTPUT_PIN} ustawiony na: {'Włączony' if state else 'Wyłączony'}")
            except Exception as e:
                logger.error(f"Błąd sterowania GPIO {self.AMP_OUTPUT_PIN}: {e}")

    def _play_sound_thread(self, file_path, is_alarm=False):
        """
        Wątek do odtwarzania dźwięku.
        `is_alarm`: True, jeśli dźwięk to alarm (będzie odtwarzany w pętli i nadrzędnie).
        """
        # Krytyczna sekcja: sprawdzanie stanu i rozpoczynanie odtwarzania
        with self._play_lock:
            # Jeśli alarm już gra i próbujemy odtworzyć coś innego niż alarm, zignoruj
            if self._is_alarm_playing and not is_alarm:
                logger.info("Alarm już gra, inny dźwięk nie zostanie odtworzony.")
                return

            if not file_path or not os.path.exists(file_path):
                logger.error(f"Brak pliku dźwiękowego lub plik nie istnieje: {file_path}")
                return

            try:
                # Zatrzymujemy bieżące odtwarzanie, jeśli jest aktywne
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    logger.info("Zatrzymano poprzednie odtwarzanie muzyki.")

                self._amp_relay(state=True)
                time.sleep(0.5) # Krótka pauza na włączenie wzmacniacza

                pygame.mixer.music.load(file_path)
                if is_alarm:
                    pygame.mixer.music.play(-1) # Odtwarzaj w nieskończoność dla alarmu
                    self._is_alarm_playing = True
                    logger.info(f"Rozpoczęto odtwarzanie alarmu (pętla): {file_path}")
                else:
                    pygame.mixer.music.play()
                    self._is_alarm_playing = False # Upewnij się, że flaga alarmu jest False dla dzwonków/przeddzwonków
                    logger.info(f"Rozpoczęto odtwarzanie: {file_path}")
            except pygame.error as e:
                logger.error(f"Błąd Pygame podczas ładowania/odtwarzania {file_path}: {e}")
                self._amp_relay(state=False) 
                return # Zakończ wątek, jeśli wystąpi błąd
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd podczas rozpoczynania odtwarzania {file_path}: {e}")
                self._amp_relay(state=False)
                return # Zakończ wątek

        # Sekcja poza blokadą _play_lock: czekanie na zakończenie utworu (tylko dla dzwonków/przeddzwonków)
        if not is_alarm:
            try:
                # Odtwarzanie w nowym wątku nie blokuje UI, ale sam wątek będzie czekał
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                logger.info(f"Zakończono odtwarzanie: {file_path}")
            except Exception as e:
                logger.error(f"Błąd podczas oczekiwania na zakończenie odtwarzania {file_path}: {e}")
            finally:
                # Upewnij się, że wzmacniacz zostanie wyłączony po zakończeniu odtwarzania
                # (lub jeśli wątek zostanie przerwany/zakończy się błędem)
                self._amp_relay(state=False)


    def playBell(self):
        """Odtwarza dźwięk dzwonka. Zatrzymuje poprzednie odtwarzanie."""
        self.stopMusic() # Zatrzymuje cokolwiek gra
        if self._musicFileBell:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFileBell, False)).start()
            self._is_bell_playing = True
        else:
            logger.warning("Brak pliku dzwonka do odtworzenia.")
        self.isMusicStopped()
        
    def playPrebell(self):
        """Odtwarza dźwięk przeddzwonka. Zatrzymuje poprzednie odtwarzanie."""
        self.stopMusic() # Zatrzymuje cokolwiek gra
        if self._musicFilePrebell:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFilePrebell, False)).start()
            self._is_prebell_playing = True
        else:
            logger.warning("Brak pliku przeddzwonka do odtworzenia.")
        self.isMusicStopped()

    def playAlarm(self):
        """Odtwarza dźwięk alarmu w pętli. Zatrzymuje poprzednie odtwarzanie (w tym dzwonek/przeddzwonek)."""
        self.stopMusic() # Zatrzymuje cokolwiek gra
        if self._musicFileAlarm:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFileAlarm, True)).start()
            self._is_alarm_playing = True
        else:
            logger.warning("Brak pliku alarmu do odtworzenia.")

    def stopMusic(self):
        """Zatrzymuje odtwarzanie muzyki i wyłącza wzmacniacz."""
        with self._play_lock: # Użyj blokady, aby bezpiecznie zatrzymać odtwarzanie
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                logger.info("Zatrzymano odtwarzanie muzyki.")
            self._is_alarm_playing = False # Resetuj flagę alarmu
            self._amp_relay(state=False) # Zawsze wyłącz wzmacniacz przy zatrzymaniu
        self.isMusicStopped()

    def is_playing(self):
        """Sprawdza, czy odtwarzany jest jakikolwiek dźwięk."""
        with self._play_lock: # Użyj blokady, aby bezpiecznie sprawdzić stan
            return pygame.mixer.music.get_busy()
    
    def isMusicStopped(self):
        while pygame.mixer.music.get_busy():
            pass
        else:
            self._is_bell_playing = False
            self._is_prebell_playing = False
            