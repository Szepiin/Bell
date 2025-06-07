from datetime import datetime, timedelta
import json
import os
import logging

# Konfiguracja logowania dla modułu schedule
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class scheduleHandling:
    """
    Klasa odpowiedzialna za zarządzanie harmonogramem dzwonków,
    ładowanie/zapisywanie danych oraz sprawdzanie aktualnego stanu.
    """
    def __init__(self):
        self.data = {
            "bellSchedule": [],        # Lista czasów dzwonków (np. ["08:00", "12:30"])
            "prebellIntervals": [],    # Lista interwałów przeddzwonka (np. [1, 0.5])
            "bellActive": []           # Lista statusów aktywności dzwonków (np. [True, False])
        }
        self.noWeekend = True          # Czy dzwonki są wyłączone w weekend
        self.nextOccurrence = None     # Następny zaplanowany dzwonek
        
        # Flagi, które będą ustawiane przez checkSchedule, informując o potrzebie akcji
        self.timeTo = {
            "turnAmpOn": False,
            "playBell": False,
            "playPrebell": False,
            "turnAmpOff": False
        }
        
        self.__scheduleLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Files/schedule.json")
        self._loadScheduleFromJson()
        self.checkSchedule() # Pierwsze sprawdzenie przy starcie aplikacji

    def _loadScheduleFromJson(self):
        """Ładuje harmonogram z pliku JSON."""
        if os.path.exists(self.__scheduleLocation):
            try:
                with open(self.__scheduleLocation, 'r') as f:
                    data_to_read = json.load(f)
                    self.data["bellSchedule"] = data_to_read.get('bell_schedule', [])
                    self.data["prebellIntervals"] = data_to_read.get('pre_bell_intervals', [])
                    self.data["bellActive"] = data_to_read.get('pre_bell_active', [])
                    self.noWeekend = data_to_read.get('no_weekend', True)
                logger.info(f"Harmonogram załadowany z: {self.__scheduleLocation}")
            except json.JSONDecodeError as e:
                logger.error(f"Błąd dekodowania JSON z pliku {self.__scheduleLocation}: {e}")
                # W przypadku błędu dekodowania, można zainicjalizować puste dane
                self.data = {"bellSchedule": [], "prebellIntervals": [], "bellActive": []}
                self.noWeekend = True
            except IOError as e:
                logger.error(f"Błąd odczytu pliku {self.__scheduleLocation}: {e}")
                # W przypadku błędu odczytu, można zainicjalizować puste dane
                self.data = {"bellSchedule": [], "prebellIntervals": [], "bellActive": []}
                self.noWeekend = True
        else:
            logger.warning(f"Plik harmonogramu nie istnieje: {self.__scheduleLocation}. Tworzenie pustego harmonogramu.")
            self.saveScheduleToJson() # Zapisz pusty harmonogram

    def checkSchedule(self):
        """
        Sprawdza harmonogram i aktualizuje flagi dotyczące dzwonienia.
        Ta funkcja jest wywoływana co sekundę w głównej pętli aplikacji (BellApp._update_main_loop).
        """
        now = datetime.now()
        
        # Resetuj flagi przed każdą kontrolą, aby uniknąć wielokrotnego wyzwalania
        for key in self.timeTo:
            self.timeTo[key] = False

        if self.noWeekend and now.weekday() >= 5:  # Sobota (5) lub Niedziela (6)
            self.nextOccurrence = "Brak dzwonków w weekend"
            return

        active_bells = []
        for i, bell_time_str in enumerate(self.data["bellSchedule"]):
            if self.data["bellActive"][i]:
                try:
                    # Załóżmy, że dzwonki są dla bieżącego dnia
                    bell_time = datetime.strptime(bell_time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                    active_bells.append((bell_time, self.data["prebellIntervals"][i]))
                except ValueError as e:
                    logger.error(f"Błąd parsowania czasu dzwonka '{bell_time_str}': {e}")
                    continue

        active_bells.sort() # Sortuj, aby łatwo znaleźć następne zdarzenie

        found_next_occurrence = False
        self.nextOccurrence = "Brak dzwonków" # Domyślna wartość, jeśli nie ma aktywnych

        for bell_time, prebell_interval in active_bells:
            prebell_time = bell_time - timedelta(minutes=prebell_interval)
            turn_amp_on_time = prebell_time - timedelta(seconds=10) # 10 sekund przed przeddzwonkiem
            turn_amp_off_time = bell_time + timedelta(seconds=2) # 2 sekundy po dzwonku (na zakończenie dźwięku)

            # Sprawdź, czy aktualny czas jest w przedziale aktywacji dla każdej akcji
            # Używamy małego okna czasowego (np. 1 sekunda), aby akcja wyzwoliła się tylko raz
            
            # Włączenie wzmacniacza
            if now >= turn_amp_on_time and now < turn_amp_on_time + timedelta(seconds=1):
                self.timeTo["turnAmpOn"] = True
                logger.debug(f"Akcja: turnAmpOn dla dzwonka o {bell_time.strftime('%H:%M')}")
            
            # Odtworzenie przeddzwonka
            if now >= prebell_time and now < prebell_time + timedelta(seconds=1):
                self.timeTo["playPrebell"] = True
                logger.debug(f"Akcja: playPrebell dla dzwonka o {bell_time.strftime('%H:%M')}")

            # Odtworzenie dzwonka
            if now >= bell_time and now < bell_time + timedelta(seconds=1):
                self.timeTo["playBell"] = True
                logger.debug(f"Akcja: playBell dla dzwonka o {bell_time.strftime('%H:%M')}")
            
            # Wyłączenie wzmacniacza
            if now >= turn_amp_off_time and now < turn_amp_off_time + timedelta(seconds=1):
                self.timeTo["turnAmpOff"] = True
                logger.debug(f"Akcja: turnAmpOff dla dzwonka o {bell_time.strftime('%H:%M')}")


            # Znajdź następne zdarzenie (dzwonek)
            if bell_time > now and not found_next_occurrence:
                self.nextOccurrence = "Następny dzwonek o " + bell_time.strftime("%H:%M")
                found_next_occurrence = True
            
        if not found_next_occurrence and active_bells:
            # Jeśli nie znaleziono przyszłego dzwonka dzisiaj, znajdź pierwszy jutro
            # Dźwięki przeszły już dzisiaj, więc następny jest jutro
            next_day_bell = min(active_bells, key=lambda x: x[0]) # Znajdź najwcześniejszy dzwonek
            self.nextOccurrence = "Następny dzwonek o " + (next_day_bell[0] + timedelta(days=1)).strftime("%H:%M")
        elif not active_bells:
            self.nextOccurrence = "Brak aktywnych dzwonków"
        # else: nextOccurrence zostało już ustawione przez `found_next_occurrence` lub domyślnie

    def saveScheduleToJson(self):
        """Zapisuje harmonogram do pliku JSON."""
        data_to_save = {
            'bell_schedule': self.data["bellSchedule"],
            'pre_bell_intervals': self.data["prebellIntervals"],
            'pre_bell_active': self.data["bellActive"],
            'no_weekend': self.noWeekend
        }
        try:
            with open(self.__scheduleLocation, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"Harmonogram zapisany do: {self.__scheduleLocation}")
        except IOError as e:
            logger.error(f"Błąd zapisu pliku {self.__scheduleLocation}: {e}")

    def addSchedule(self):
        """Dodaje nowy dzwonek do harmonogramu."""
        from constants import MAX_BELLS, DEFAULT_BELL_INTERVAL # Importuj stałe
        if len(self.data['bellSchedule']) >= MAX_BELLS:
            logger.warning(f"Osiągnięto maksymalną liczbę dzwonków ({MAX_BELLS}). Nie można dodać więcej.")
            return False # Sygnalizuj, że dodanie się nie powiodło

        #default_time = datetime.now().strftime("%H:%M")
        self.data["bellSchedule"].append("00:00")
        self.data["prebellIntervals"].append(DEFAULT_BELL_INTERVAL)
        self.data["bellActive"].append(True)

        self._sort_schedule()
        self.saveScheduleToJson()
        logger.info(f"Dodano nowy dzwonek")
        return True # Sygnalizuj sukces

    def deleteSchedule(self, index):
        """Usuwa dzwonek o podanym indeksie z harmonogramu."""
        if 0 <= index < len(self.data["bellSchedule"]):
            deleted_time = self.data["bellSchedule"][index]
            del self.data["bellSchedule"][index]
            del self.data["prebellIntervals"][index]
            del self.data["bellActive"][index]
            self.saveScheduleToJson()
            logger.info(f"Usunięto dzwonek: {deleted_time} (indeks: {index})")
            return True
        else:
            logger.warning(f"Próba usunięcia dzwonka o nieprawidłowym indeksie: {index}")
            return False

    def _sort_schedule(self):
        """Sortuje harmonogram po czasie dzwonka."""
        if not self.data["bellSchedule"]: # Zabezpieczenie przed pustą listą
            return
        
        sorted_data = sorted(zip(self.data["bellSchedule"], self.data["prebellIntervals"], self.data["bellActive"]),
                            key=lambda x: datetime.strptime(x[0], "%H:%M"))
        
        self.data["bellSchedule"], self.data["prebellIntervals"], self.data["bellActive"] = (
            list(t) for t in zip(*sorted_data)
        )

    def getFormattedScheduleList(self):
        """Zwraca sformatowaną listę dzwonków."""
        formatted_list = []
        if not self.data["bellSchedule"]:
            return ["Brak zdefiniowanych dzwonków"]

        for i, time_str in enumerate(self.data["bellSchedule"]):
            status = "✅ Aktywny" if self.data["bellActive"][i] else "❌ Nieaktywny"
            formatted_list.append(f"{status} Dzwonek {i + 1}: {time_str}")
        return formatted_list