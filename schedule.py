from datetime import datetime, timedelta
import json
import os
import logging
import constants

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
        
        self.__scheduleLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Files/schedule.json") if not constants.SCHEDULE_PATH_LINUX else constants.SCHEDULE_PATH_LINUX

        self.daily_events = [] 
        self.current_date = None
        self.needs_rebuild = True
        
        self._loadScheduleFromJson()
        self.checkSchedule()

    def _build_daily_events(self, target_datetime):
        """
        Buduje listę wszystkich akcji na dany dzień. 
        Odporne na obciążenie CPU - każde zadanie musi zostać 'odhaczone'.
        """
        self.daily_events = []
        self.current_date = target_datetime.date()
        self.needs_rebuild = False
        
        if self.noWeekend and target_datetime.weekday() >= 5:
            return # W weekend lista zostaje pusta

        for i, time_str in enumerate(self.data["bellSchedule"]):
            if not self.data["bellActive"][i]:
                continue
                
            try:
                # Zamiana stringa na obiekt datetime w konkretnym dniu
                h, m = map(int, time_str.split(':'))
                bell_time = target_datetime.replace(hour=h, minute=m, second=0, microsecond=0)
            except ValueError:
                continue

            pre_interval = self.data["prebellIntervals"][i]
            prebell_time = bell_time - timedelta(minutes=pre_interval)
            
            if pre_interval == 0:
                amp_on_time = bell_time - timedelta(seconds=constants.AMP_ON_DELAY)
            else:
                amp_on_time = prebell_time - timedelta(seconds=constants.AMP_ON_DELAY)
                
            amp_off_time = bell_time + timedelta(seconds=constants.AMP_OFF_DELAY)
            
            # Wrzucamy do kolejki (akcja, czas, status wykonania, to_log)
            self.daily_events.append({"action": "turnAmpOn", "time": amp_on_time, "done": False})
            if pre_interval > 0:
                self.daily_events.append({"action": "playPrebell", "time": prebell_time, "done": False})
            self.daily_events.append({"action": "playBell", "time": bell_time, "done": False})
            self.daily_events.append({"action": "turnAmpOff", "time": amp_off_time, "done": False})
            
        # Sortujemy zdarzenia chronologicznie!
        self.daily_events.sort(key=lambda x: x["time"])

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
        """Zupełnie nowe, odporne na przestoje sprawdzanie zdarzeń."""
        now = datetime.now()
        
        # Resetujemy impulsy wyjściowe
        for key in self.timeTo:
            self.timeTo[key] = False

        # Przebuduj harmonogram na dziś, jeśli to nowy dzień lub zmodyfikowano dane
        if self.current_date != now.date() or self.needs_rebuild:
            self._build_daily_events(now)

        found_next_occurrence = False
        self.nextOccurrence = "Brak dzwonków"

        # SPRAWDZANIE ZDARZEŃ Z KOLEJKI
        for event in self.daily_events:
            # Jeśli czas minął, a zdarzenie nie było jeszcze wykonane -> WYKONAJ
            if not event["done"] and now >= event["time"]:
                event["done"] = True
                # Zabezpieczenie na wypadek, gdyby Raspberry było uśpione przez pół dnia
                # Wykonujemy tylko te opóźnienia, które są nie starsze niż minuta!
                if (now - event["time"]).total_seconds() <= 60:
                    self.timeTo[event["action"]] = True
                    logger.info(f"Odhaczono akcję: {event['action']} (zaplanowaną na {event['time'].strftime('%H:%M:%S')})")
                else:
                    logger.warning(f"Zignorowano starą akcję: {event['action']} z {event['time'].strftime('%H:%M:%S')}")

            # Szukanie następnego dzwonka do wyświetlenia w GUI (tylko główne dzwonki)
            if event["action"] == "playBell" and event["time"] > now and not found_next_occurrence:
                self.nextOccurrence = "Następny dzwonek o " + event["time"].strftime("%H:%M")
                found_next_occurrence = True

        # Jeśli dziś już nic nie ma, pokaż dzwonek na jutro (pseudo logiką)
        if self.noWeekend and now.weekday() >= 5:
            # 5 = Sobota, 6 = Niedziela
            self.nextOccurrence = "Dzwonki w weekend wyłączone"
            
        elif not found_next_occurrence and len(self.data["bellSchedule"]) > 0:
            # Jeśli są zdefiniowane jakieś dzwonki, ale na DZIŚ już się skończyły
            if self.noWeekend and now.weekday() == 4:
                # 4 = Piątek po południu
                self.nextOccurrence = "Następny dzwonek w poniedziałek"
            else:
                # Każdy inny dzień w środku tygodnia po południu
                self.nextOccurrence = "Następny dzwonek jutro"

    def saveScheduleToJson(self):
        self._sort_schedule()

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
        self.needs_rebuild = True

    def addSchedule(self):
        """Dodaje nowy dzwonek do harmonogramu."""
        from constants import MAX_BELLS, DEFAULT_BELL_INTERVAL # Importuj stałe
        if len(self.data['bellSchedule']) >= MAX_BELLS:
            logger.warning(f"Osiągnięto maksymalną liczbę dzwonków ({MAX_BELLS}). Nie można dodać więcej.")
            return False # Sygnalizuj, że dodanie się nie powiodło

        #default_time = datetime.now().strftime("%H:%M")
        self.data["bellSchedule"].append("06:00")
        self.data["prebellIntervals"].append(DEFAULT_BELL_INTERVAL)
        self.data["bellActive"].append(True)

        logger.info(f"Dodano nowy dzwonek")
        self.needs_rebuild = True
        return True

    def deleteSchedule(self, index):
        """Usuwa dzwonek o podanym indeksie z harmonogramu."""
        if 0 <= index < len(self.data["bellSchedule"]):
            deleted_time = self.data["bellSchedule"][index]
            del self.data["bellSchedule"][index]
            del self.data["prebellIntervals"][index]
            del self.data["bellActive"][index]
            self._sort_schedule()
            self.saveScheduleToJson()
            logger.info(f"Usunięto dzwonek: {deleted_time} (indeks: {index})")
            self.needs_rebuild = True
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
        self._sort_schedule()
        formatted_list = []
        if not self.data["bellSchedule"]:
            return ["Brak zdefiniowanych dzwonków"]

        for i, time_str in enumerate(self.data["bellSchedule"]):
            status = "✔  - " if self.data["bellActive"][i] else "✖  - "
            
#            status = "✔         Aktywny -" if self.data["bellActive"][i] else "✖   Nieaktywny -"
            formatted_list.append(f"{status} Dzwonek {i + 1:02}  -  {time_str}")
        return formatted_list
