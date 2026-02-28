import pygame
import os
import time
import threading
from mutagen import mp3
import platform
import logging

from constants import MAX_MUSIC_LEN
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
        try:
            # Próba normalnego uruchomienia dźwięku
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.music.set_volume(0.8)
            logger.info("Zainicjalizowano system audio.")
        except pygame.error:
            # Jeśli się nie uda (brak karty), uruchom w trybie "dummy" (cisza, ale bez błędu)
            logger.warning("Brak urządzenia audio! Uruchamianie w trybie 'dummy' (bez dźwięku).")
            os.environ["SDL_AUDIODRIVER"] = "dummy"
            pygame.mixer.init()
        self.AMP_OUTPUT_PIN = AMP_OUTPUT_PIN
        self.soundFilesPath = filesPath
        self._sampleSoundLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Files/DomyslnyDzwiek.mp3")
        self._play_id = 0
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
        #logger.warning(f"Nie znaleziono pliku MP3 zaczynającego się na '{start_letter}' w lokalizacji {self.soundFilesPath}. Użycie domyślnego: {self._sampleSoundLocation}")
        if os.path.exists(self._sampleSoundLocation):
            return self._sampleSoundLocation
        else:
            logger.error(f"Domyślny plik dźwiękowy nie istnieje: {self._sampleSoundLocation}")
            return None # Zwróć None, jeśli nawet domyślny plik jest niedostępny


    def _get_mp3_length(self, file_path):
        """Zwraca długość pliku MP3 w sekundach."""
        if not file_path or not os.path.exists(file_path):
            return MAX_MUSIC_LEN
        try:
            audio = mp3.Open(file_path)
            return audio.info.length
        except Exception as e:
            logger.error(f"Błąd odczytu długości pliku MP3 {file_path}: {e}")
            return MAX_MUSIC_LEN

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
        Wątek odtwarza dźwięk i kończy go po MAX_MUSIC_LEN.
        WAŻNE: Ten wątek NIE wyłącza wzmacniacza po zakończeniu.
        """
        sound_duration = 0
        if not is_alarm:
            full_len = self._get_mp3_length(file_path)
            sound_duration = min(full_len, MAX_MUSIC_LEN) # Max 15s
        
        with self._play_lock:
            self._play_id += 1
            current_play_id = self._play_id
            if self._is_alarm_playing and not is_alarm:
                return

            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                # ZAWSZE upewnij się, że wzmacniacz jest włączony przed graniem
                self._amp_relay(state=True)

                pygame.mixer.music.load(file_path)
                if is_alarm:
                    pygame.mixer.music.play(-1)
                    self._is_alarm_playing = True
                    logger.info(f"START ALARMU: {os.path.basename(file_path)}")
                else:
                    pygame.mixer.music.play()
                    self._is_alarm_playing = False 
                    logger.info(f"START ODTWARZANIA: {os.path.basename(file_path)} (Max: {sound_duration:.1f}s)")
            
            except Exception as e:
                logger.error(f"Błąd odtwarzania: {e}")
                self._amp_relay(state=False)
                return 

        # Czekanie na koniec dźwięku
        if not is_alarm:
            if sound_duration > 0:
                time.sleep(sound_duration)
            else:
                time.sleep(3)
                
            if self._play_id == current_play_id and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                logger.info("Koniec czasu odtwarzania (muzyka stop, wzmacniacz nadal ON).")
                
            self.isMusicStopped()

    def playBell(self):
        # Stopujemy poprzednie, ale nie wyłączamy wzmacniacza (false), bo zaraz będziemy grać
        self.stopMusic(turn_amp_off=False) 
        if self._musicFileBell:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFileBell, False)).start()
            self._is_bell_playing = True
        
    def playPrebell(self):
        self.stopMusic(turn_amp_off=False)
        if self._musicFilePrebell:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFilePrebell, False)).start()
            self._is_prebell_playing = True

    def playAlarm(self):
        self.stopMusic(turn_amp_off=False)
        if self._musicFileAlarm:
            threading.Thread(target=self._play_sound_thread, args=(self._musicFileAlarm, True)).start()
            self._is_alarm_playing = True

    def stopMusic(self, turn_amp_off=True):
        """Ręczne zatrzymanie (np. przycisk w GUI). Domyślnie wyłącza wzmacniacz."""
        with self._play_lock:
            self._play_id += 1
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self._is_alarm_playing = False
            
            if turn_amp_off:
                self._amp_relay(state=False)
                
        self.isMusicStopped()

    def is_playing(self):
        return pygame.mixer.music.get_busy()
    
    def isMusicStopped(self):
        if not pygame.mixer.music.get_busy():
            self._is_bell_playing = False
            self._is_prebell_playing = False