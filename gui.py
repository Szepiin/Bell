import customtkinter as ctk
from datetime import datetime
import clockHandling 
import time
import threading
import logging
import auth
from myLibs import NotificationPopup, MyButton, MyLabel, MySpinbox, ScheduleButton


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class BellApp(ctk.CTk):
    """
    Główna klasa aplikacji dzwonkowej.
    Zarządza ramkami, nawigacją, zegarem systemowym i logiką wygaszacza ekranu.
    """
    def __init__(self, music, schedule, screensaver_time, auth_handler):
        super().__init__()
        self.music = music
        self.schedule = schedule
        self.screensaver_time = screensaver_time 
        self.auth = auth_handler

        self.title("Dzwonek")
        self.geometry("800x480")
        # self.attributes("-fullscreen", True)
        self.config(cursor="none")

        self.frames = {} 
        self.current_frame_name = None

        self.create_tab_buttons()
        self.create_frames()
        #self.show_frame("main")

        self.show_frame("login")
        
        self.last_activity_time = time.time()
        self.bind_all("<Button>", self._reset_inactivity_timer)
        self.bind_all("<Key>", self._reset_inactivity_timer)
        self.after(1000, self._check_inactivity)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(1000, self._update_main_loop)

    def create_tab_buttons(self):
        """Tworzy ramkę z przyciskami nawigacyjnymi (zakładkami)."""
        self.tab_buttons_frame = ctk.CTkFrame(self)
        self.tab_buttons_frame.pack(side="top", fill="x")

        buttons = [
            ("Harmonogram", "main"),
            ("Ustawienia", "sounds"),
            ("Dzwonki", "schedule"),
            ("Zegar", "clock"),
            ("Hasło", "security"),
        ]

        for text, name in buttons:
            ctk.CTkButton(
                self.tab_buttons_frame,
                text=text,
                height=80,
                hover=False,
                fg_color="#1f538d",
                font=ctk.CTkFont(family="Calibri", size=24, weight="bold"),
                command=lambda n=name: self.show_frame(n),
            ).pack(side="left", fill="both", expand=True, padx=3, pady=5)


    def create_frames(self):
        """Tworzy instancje wszystkich ramek aplikacji."""
        self.frames["login"] = LoginScreen(self, self.auth)
        self.frames["main"] = MainScreen(self)
        self.frames["sounds"] = SoundSettings(self)
        self.frames["schedule"] = ScheduleTab(self, self.schedule)
        self.frames["clock"] = ClockTab(self)
        self.frames["security"] = SecurityTab(self, self.auth)
        self.frames["screensaver"] = ScreensaverFrame(self)
        self.frames["popup"] = PopupFrame(self)

        # Umieszczenie wszystkich ramek w tym samym miejscu, aby można było je przełączać
        for frame in self.frames.values():
            if frame != self.frames["screensaver"] and frame != self.frames["login"]: 
                frame.place(x=0, y=90, relwidth=1, relheight=1) # Ramki pod paskiem przycisków
            else:
                frame.place(x=0, y=0, relwidth=1, relheight=1) # Wygaszacz ekranu zajmuje cały ekran
    
    def unlock_application(self):
        """Wywoływane po poprawnym wpisaniu PINu."""
        logger.info("Zalogowano pomyślnie.")
        self.show_frame("main")
    
    def show_frame(self, name):
        """
        Pokazuje wybraną ramkę i ukrywa pozostałe.
        Odświeża dane na ekranie głównym i zegarze przy wejściu na nie.
        """
        if name not in self.frames:
            logger.error(f"Próba wyświetlenia nieistniejącej ramki: {name}")
            return

        for frame_name, frame_obj in self.frames.items():
            if frame_name == name:
                frame_obj.lift() # Podnieś wybraną ramkę na wierzch
                if frame_name != "login" and frame_name != "screensaver":
                    self.tab_buttons_frame.pack(side="top", fill="x") # Pokaż przyciski nawigacyjne
                else:
                    self.tab_buttons_frame.pack_forget() # Ukryj przyciski dla wygaszacza ekranu
            else:
                frame_obj.lower() # Opuść pozostałe ramki
        self.current_frame_name = name
        logger.info(f"Wyświetlono ramkę: {name}")

        # Odświeżanie danych na ekranach tylko przy wejściu na nie
        if name == "main":
            self.frames["main"].update_display(self.schedule.nextOccurrence, self.schedule.getFormattedScheduleList())
        if name == "clock":
            self.frames["clock"].update_time()

    def _reset_inactivity_timer(self, event=None):
        self.last_activity_time = time.time()
        # Jeśli jesteśmy na screensaverze, wróć do logowania (bezpieczniej) lub do main
        # Tutaj decyzja projektowa: Czy po wygaszaczu trzeba znowu podać hasło?
        # Zazwyczaj w takich systemach nie, chyba że to ścisła kontrola.
        # Przywracam poprzedni widok.
        
        if self.current_frame_name == "screensaver":
            # Jeśli wylogowanie po czasie jest wymagane, zmień na: self.show_frame("login")
            # Jeśli nie, wracamy do głównego (ale zakładając, że user był zalogowany)
            # Najbezpieczniej: wróć do logowania.
            self.show_frame("login") 
            logger.info("Wyjście z wygaszacza -> powrót do logowania.")
    def _update_main_loop(self):
        """
        Główna pętla aktualizująca stan aplikacji co sekundę.
        Odpowiada za logikę dzwonienia i aktualizację wygaszacza ekranu.
        Nie odświeża ciągle listy dzwonków na ekranie głównym.
        """
        self.schedule.checkSchedule() # Model harmonogramu aktualizuje swój stan dzwonków
        
        # Widok screensavera musi się odświeżać co sekundę, bo pokazuje aktualny czas
        if self.current_frame_name == "screensaver":
            self.frames["screensaver"].update_clock(self.schedule.nextOccurrence)
        if self.current_frame_name == "clock":
             self.frames["clock"].update_time()
             
        # Sprawdź flagi `timeTo` z harmonogramu i wykonaj odpowiednie akcje
        # Flagi są resetowane w schedule.checkSchedule(), więc akcja wyzwoli się tylko raz
        if self.schedule.timeTo["turnAmpOn"]:
            self.music._amp_relay(state=True)
            logger.info("Włączono wzmacniacz.")
        
        if self.schedule.timeTo["playPrebell"]:
            self.music.playPrebell()
            logger.info("Odtworzono przeddzwonek.")

        if self.schedule.timeTo["playBell"]:
            self.music.playBell()
            logger.info("Odtworzono dzwonek.")
        
        if self.schedule.timeTo["turnAmpOff"]:
            self.music._amp_relay(state=False)
            logger.info("Wyłączono wzmacniacz.")

        self.frames["sounds"]._update_button_texts()
        
        self.after(1000, self._update_main_loop) # Zaplanuj kolejne wywołanie po 1 sekundzie

    def _on_close(self):
        """Obsługa zamykania okna aplikacji: zapisuje harmonogram i zatrzymuje muzykę."""
        self.schedule.saveScheduleToJson()
        self.music.stopMusic() 
        logger.info("Aplikacja zamykana.")
        self.destroy()
    
    def _reset_inactivity_timer(self, event=None):
        """Resetuje licznik bezczynności i wychodzi z wygaszacza ekranu, jeśli jest aktywny."""
        self.last_activity_time = time.time()
        if self.current_frame_name == "screensaver":
            self.show_frame("login")
            logger.info("Wykryto aktywność, powrót z wygaszacza ekranu.")

    def _check_inactivity(self):
        """Sprawdza bezczynność użytkownika i włącza wygaszacz ekranu po określonym czasie."""
        if time.time() - self.last_activity_time > self.screensaver_time:
            if self.current_frame_name != "screensaver":
                self.show_frame("screensaver")
                logger.info(f"Brak aktywności przez {self.screensaver_time}s, włączanie wygaszacza ekranu.")
        self.after(1000, self._check_inactivity) # Sprawdzaj co sekundę


class MainScreen(ctk.CTkFrame):
    """
    Ekran główny aplikacji, wyświetlający następny dzwonek i listę wszystkich dzwonków.
    """
    def __init__(self, master):
        super().__init__(master)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(fill="x", pady=1)

        self.next_time_label = MyLabel(self.top_frame, text="Następny dzwonek: --:--")
        self.next_time_label.pack(fill="x", pady=3)

        self.schedule_display_frame = ctk.CTkScrollableFrame(self, height=330)
        self.schedule_display_frame._scrollbar.configure(width=30, hover=False)
        self.schedule_display_frame.pack(fill="both", pady=5, padx=2)
        

        self.bell_labels = [] # Lista do przechowywania referencji do etykiet dzwonków

    def update_display(self, next_occurrence, formatted_schedule_list):
        """
        Aktualizuje wyświetlanie następnego dzwonka i listy dzwonków.
        Wywoływane tylko przy wejściu na ten ekran, aby uniknąć migotania.
        """
        self.next_time_label.configure(text= next_occurrence)
        self._update_bell_labels(formatted_schedule_list)
        logger.debug("MainScreen: Odświeżono wyświetlanie.")
    def _update_bell_labels(self, formatted_schedule_list):
        """
        Aktualizuje etykiety dzwonków z równym formatowaniem kolumnowym,
        rozmieszczając je w dwóch głównych kolumnach.
        """
        num_entries = len(formatted_schedule_list)
        num_rows = (num_entries + 1) // 2  # liczba wierszy potrzebna do 2-kolumnowego układu

        # Upewnij się, że `bell_labels` ma wystarczającą liczbę etykiet (w układzie [ [label1, label2], ... ])
        while len(self.bell_labels) < num_rows:
            row_labels = []
            for col in range(2):  # 2 kolumny
                frame = ctk.CTkFrame(self.schedule_display_frame, corner_radius=0)
                frame.grid(row=len(self.bell_labels), column=col, padx=5, pady=2, sticky="nsew")

                label = MyLabel(frame, text="", anchor="center", corner_radius=5)
                label.pack(fill="both", expand=True, padx=5, pady=3)

                row_labels.append(label)
            self.bell_labels.append(row_labels)

        # Aktualizuj/ustaw dane w etykietach
        for idx, entry in enumerate(formatted_schedule_list):
            row = idx // 2
            col = idx % 2
            label = self.bell_labels[row][col]
            if label.cget("text") != entry:
                label.configure(text=entry)
            label.master.grid()  # pokaż frame jeśli był ukryty
            label.master.grid_rowconfigure(0, weight=1)

        # Ukryj nadmiarowe etykiety (jeśli np. wcześniej było więcej)
        for idx in range(num_entries, len(self.bell_labels) * 2):
            row = idx // 2
            col = idx % 2
            label = self.bell_labels[row][col]
            label.configure(text="")
            label.master.grid_remove()  # ukryj frame

        # Ustaw wagę wierszy i kolumn, by równo się rozciągały
        for row in range(num_rows):
            self.schedule_display_frame.grid_rowconfigure(row, weight=1)
        self.schedule_display_frame.grid_columnconfigure(0, weight=1)
        self.schedule_display_frame.grid_columnconfigure(1, weight=1)

        logger.debug(f"Zaktualizowano etykiety dzwonków: {num_entries} pozycji, {num_rows} wierszy.")

class SoundSettings(ctk.CTkFrame):
    """
    Ekran ustawień dźwięków, pozwalający na testowanie dzwonków, przeddzwonków, alarmów
    oraz włączanie/wyłączanie trybu weekendowego.
    """
    def __init__(self, master):
        super().__init__(master)


        self.top = ctk.CTkFrame(self)
        self.top.pack(fill="x")
        
        self.left = ctk.CTkFrame(self.top)
        self.left.pack(side="left", fill="both", expand=True)

        self.right = ctk.CTkFrame(self.top)
        self.right.pack(side="right", fill="both", expand=True)


        # Przycisk odtwarzania/zatrzymywania dzwonka
        self.btnPlayBell = MyButton(
            self.left,
            text="", # Tekst zostanie ustawiony przez _update_button_texts
            command=self._toggle_bell_btn,
        )
        self.btnPlayBell.pack(pady=30)

        # Przycisk odtwarzania/zatrzymywania przeddzwonka
        self.btnPlayPrebell = MyButton(
            self.left,
            text="", # Tekst zostanie ustawiony przez _update_button_texts
            command=self._toggle_prebell_btn,
        )
        self.btnPlayPrebell.pack(pady=30)

        # Przycisk uruchamiania/zatrzymywania alarmu
        self.btnStartAlarm = MyButton(
            self.right,
            text="", # Tekst zostanie ustawiony przez _update_button_texts
            fg_color="#e00000",           
            command=self._toggle_alarm_btn,
        )
        self.btnStartAlarm.pack(pady=30)
       
        # Przycisk trybu weekendowego
        self.btnToggleWeekend = MyButton(self.right, text="", command=self._toggle_weekend_btn)
        self._update_weekend_button_text() # Ustaw początkowy tekst i kolor
        self.btnToggleWeekend.pack(pady=30, fill="y")

        self._update_button_texts() # Upewnij się, że tekst przycisków jest aktualny przy inicjalizacji
        
        self.lbInfo = MyLabel(self, text="Autor: Grzegorz Serwin | Wersja programu: 1.0.0", font=ctk.CTkFont(family="Calibri", size=12, weight="bold"))
        self.lbInfo.pack(pady=10)
        
    def _update_button_texts(self):
        """
        Aktualizuje teksty i kolory przycisków odtwarzania dźwięków
        w zależności od aktualnego stanu odtwarzania (czy coś gra, czy alarm).
        """
        if self.master.music._is_alarm_playing:
            self.btnStartAlarm.configure(text=f"Zatrzymaj alarm\n{self.master.music.musicFileNameAlarm}", fg_color="#990000")
            self.btnPlayBell.configure(state="disabled")
            self.btnPlayPrebell.configure(state="disabled")

        else: # Nic nie gra
            self.btnPlayBell.configure(text=f"Odtwórz / zatrzymaj\ndzwonek:\n{self.master.music.musicFileNameBell}", state="normal")
            self.btnPlayPrebell.configure(text=f"Odtwórz / zatrzymaj\nprzeddzwonek:\n{self.master.music.musicFileNamePrebell}", state="normal")
            self.btnStartAlarm.configure(text=f"Uruchom alarm:\n{self.master.music.musicFileNameAlarm}", state="normal",fg_color="#e00000")


    def _toggle_bell_btn(self):
        """Obsługuje kliknięcie przycisku dzwonka: zatrzymuje lub odtwarza."""
        if self.master.music.is_playing() and not self.master.music._is_alarm_playing:
            # Jeśli gra dzwonek/przeddzwonek, zatrzymaj go
            self.master.music.stopMusic()
            logger.info("Zatrzymano dzwonek/przeddzwonek.")
        else:
            # Jeśli nic nie gra lub gra alarm (który zostanie przerwany), uruchom dzwonek
            self.master.music.playBell()
            logger.info("Uruchomiono dzwonek.")
        self._update_button_texts() # Zaktualizuj teksty wszystkich przycisków


    def _toggle_prebell_btn(self):
        """Obsługuje kliknięcie przycisku przeddzwonka: zatrzymuje lub odtwarza."""
        if self.master.music.is_playing() and not self.master.music._is_alarm_playing:
            # Jeśli gra dzwonek/przeddzwonek, zatrzymaj go
            self.master.music.stopMusic()
            logger.info("Zatrzymano dzwonek/przeddzwonek.")
        else:
            # Jeśli nic nie gra lub gra alarm (który zostanie przerwany), uruchom przeddzwonek
            self.master.music.playPrebell()
            logger.info("Uruchomiono przeddzwonek.")
        self._update_button_texts()
        

    def _toggle_alarm_btn(self):
        """Obsługuje kliknięcie przycisku alarmu: uruchamia lub zatrzymuje alarm."""
        if self.master.music._is_alarm_playing: # Sprawdź, czy to alarm gra
            self.master.music.stopMusic()
            logger.info("Alarm zatrzymany.")
        else: # Alarm nie gra, więc go uruchom
            self.master.music.playAlarm()
            logger.info("Alarm uruchomiony.")
        self._update_button_texts() # Zawsze aktualizuj teksty po zmianie stanu alarmu


    def _update_weekend_button_text(self):
        """Aktualizuje tekst i kolor przycisku trybu weekendowego."""
        if self.master.schedule.noWeekend: # Jeśli noWeekend jest True, to dzwonki są wyłączone w weekend
            self.btnToggleWeekend.configure(text="Dzwonki w weekend:\n✖ - nieaktywne", fg_color="#5e5e5e")
        else:
            self.btnToggleWeekend.configure(text="Dzwonki w weekend:\n✔ - aktywne", fg_color="#969696")

    def _toggle_weekend_btn(self):
        """Obsługuje kliknięcie przycisku trybu weekendowego: przełącza stan."""
        self.master.schedule.noWeekend = not self.master.schedule.noWeekend 
        self._update_weekend_button_text()
        self.master.schedule.saveScheduleToJson() # Zapisz zmianę stanu weekendu
        logger.info(f"Tryb weekendowy: {'Dzwonki nieaktywne' if self.master.schedule.noWeekend else 'Dzwonki aktywne'}")
class ScheduleTab(ctk.CTkFrame):
    class BellFrame(ctk.CTkFrame):
        def __init__(self, master_tab, schedule): # Usunięto on_data_change_callback
            super().__init__(master_tab)
            self.master_tab = master_tab
            self.schedule = schedule
            self.schedule_data = self.schedule.data # Referencja do danych harmonogramu

            self.hour_var = ctk.IntVar()
            self.minute_var = ctk.IntVar()
            self.interval_var = ctk.DoubleVar()
            self.active_var = ctk.BooleanVar()

            self._trace_ids = {}
            # Callback _on_variable_change będzie tylko aktualizował self.schedule.data
            self._trace_ids['hour'] = self.hour_var.trace_add("write", self._on_variable_change)
            self._trace_ids['minute'] = self.minute_var.trace_add("write", self._on_variable_change)
            self._trace_ids['interval'] = self.interval_var.trace_add("write", self._on_variable_change)
            self._trace_ids['active'] = self.active_var.trace_add("write", self._on_variable_change)

            self._build_gui()
            self.current_display_index = -1 

        def _on_variable_change(self, var_name, index, mode):
            """
            Callback dla zmian zmiennych w BellFrame.
            Aktualizuje tylko wewnętrzną strukturę danych self.schedule.data.
            NIE wywołuje zapisu do pliku ani callbacka do ScheduleTab.
            """
            self._save_current_values_to_schedule_data(suppress_trace_callbacks=True)
            # Opcjonalnie: Możesz tu dodać flagę is_dirty = True w ScheduleTab,
            # aby sygnalizować, że są niezapisane zmiany.

        def _save_current_values_to_schedule_data(self, suppress_trace_callbacks=False):
            """
            Zapisuje aktualne wartości zmiennych z BellFrame do struktury danych harmonogramu (self.schedule.data).
            `suppress_trace_callbacks` używane, aby uniknąć rekurencyjnego wywoływania trace.
            """
            if not (0 <= self.current_display_index < len(self.schedule_data["bellSchedule"])):
                logger.warning(f"Attempted to save data for invalid index: {self.current_display_index}")
                return

            try:
                hour = self.hour_var.get()
                minute = self.minute_var.get()

                if suppress_trace_callbacks:
                    self._remove_all_traces()

                self.schedule_data["bellSchedule"][self.current_display_index] = f"{hour:02d}:{minute:02d}"
                self.schedule_data["prebellIntervals"][self.current_display_index] = self.interval_var.get()
                self.schedule_data["bellActive"][self.current_display_index] = self.active_var.get()

                if suppress_trace_callbacks:
                    self._add_all_traces()

                logger.debug(f"Saved current BellFrame values to schedule data for index {self.current_display_index}.")

            except Exception as e:
                logger.error(f"Error saving current BellFrame values to schedule data for index {self.current_display_index}: {e}")

        def _remove_all_traces(self):
            """Usuwa wszystkie śledzenia ze zmiennych CustomTkinter."""
            for var_name, trace_id in list(self._trace_ids.items()): # Użyj list() aby móc modyfikować słownik podczas iteracji
                if trace_id:
                    getattr(self, f"{var_name}_var").trace_remove("write", trace_id)
                    del self._trace_ids[var_name] # Usuń wpis po usunięciu śledzenia

        def _add_all_traces(self):
            """Dodaje z powrotem wszystkie śledzenia do zmiennych CustomTkinter."""
            # Dodaj tylko jeśli słownik jest pusty (czyli wszystkie trace zostały usunięte)
            # lub jeśli konkretny trace nie istnieje
            if 'hour' not in self._trace_ids:
                self._trace_ids['hour'] = self.hour_var.trace_add("write", self._on_variable_change)
            if 'minute' not in self._trace_ids:
                self._trace_ids['minute'] = self.minute_var.trace_add("write", self._on_variable_change)
            if 'interval' not in self._trace_ids:
                self._trace_ids['interval'] = self.interval_var.trace_add("write", self._on_variable_change)
            if 'active' not in self._trace_ids:
                self._trace_ids['active'] = self.active_var.trace_add("write", self._on_variable_change)


        def _load_bell_data(self, index):
            """Ładuje dane dla podanego indeksu i aktualizuje zmienne BellFrame."""
            if not (0 <= index < len(self.schedule_data["bellSchedule"])):
                logger.warning(f"Cannot load data for index {index}: out of bounds for bellSchedule of size {len(self.schedule_data['bellSchedule'])}")
                self._remove_all_traces() # Upewnij się, że nie ma aktywnych trace'ów przed resetowaniem
                self.hour_var.set(0)
                self.minute_var.set(0)
                self.interval_var.set(0.5)
                self.active_var.set(False)
                self.bell_label.configure(text="Brak dzwonka") 
                self.current_display_index = -1 # Ustaw na nieprawidłowy indeks, jeśli brak dzwonka
                self._add_all_traces() # Przywróć trace'y
                return False

            self.current_display_index = index
            time_str = self.schedule_data["bellSchedule"][index]
            
            self._remove_all_traces() # Usuń wszystkie śledzenia przed ustawieniem wartości

            try:
                self.hour_var.set(int(time_str.split(":")[0]))
                self.minute_var.set(int(time_str.split(":")[1]))
            except ValueError:
                logger.error(f"Błąd parsowania czasu dla dzwonka {index}: {time_str}. Ustawiam na 00:00.")
                self.hour_var.set(0)
                self.minute_var.set(0)

            self.interval_var.set(self.schedule_data["prebellIntervals"][index])
            self.active_var.set(self.schedule_data["bellActive"][index])

            self._add_all_traces() # Dodaj z powrotem wszystkie śledzenia

            self.bell_label.configure(text=f"Dzwonek {self.current_display_index + 1} z {len(self.schedule_data['bellSchedule'])}")
            logger.info(f"Loaded bell data for index: {index}")
            return True


        def _build_gui(self):
            self.grid_columnconfigure(0, weight=1, minsize=150)
            self.grid_columnconfigure(1, weight=1, minsize=150)
            self.grid_columnconfigure(2, weight=1, minsize=150) 
            self.grid_rowconfigure(0, weight=0, minsize=22)
            self.grid_rowconfigure(1, weight=1, minsize=22)
            self.grid_rowconfigure(2, weight=1, minsize=22)
            self.grid_rowconfigure(3, weight=0, minsize=22)

            self.label_frame = ctk.CTkFrame(self)
            self.label_frame.grid(row=0, column=0, columnspan=3, rowspan=1, sticky="ew", pady=(5, 1))
            self.label_frame.grid_columnconfigure(0, weight=1)
            self.bell_label = ctk.CTkLabel(self.label_frame, text="Dzwonek X z Y",
                                             font=ctk.CTkFont(family="Calibri", size=24, weight="bold"))
            self.bell_label.grid(pady=(5, 5))

            ctk.CTkCheckBox(
                self,
                text="Aktywny",
                variable=self.active_var,
                font=ctk.CTkFont(family="Calibri", size=22, weight="bold"),
                checkbox_width=50, 
                checkbox_height=50
            ).grid(row=1, column=0, rowspan=2)

            MyLabel(self, text="Godzina:").grid(row=1, column=1, sticky="s", pady=5)
            MySpinbox(
                self,
                variable=self.hour_var,
                min_value=0, max_value=23, step_size=1,
                width=180, height=60,
                font=ctk.CTkFont(family="Calibri", size=22, weight="bold")
            ).grid(row=2, column=1, sticky="n")

            MyLabel(self, text="Minuta:").grid(row=1, column=2, sticky="s", pady=5)
            MySpinbox(
                self,
                variable=self.minute_var,
                min_value=0, max_value=59, step_size=1,
                width=180, height=60,
                font=ctk.CTkFont(family="Calibri", size=22, weight="bold")
            ).grid(row=2, column=2, sticky="n")

            radio_buttons_frame = ctk.CTkFrame(self)
            radio_buttons_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
            radio_buttons_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

            MyLabel(radio_buttons_frame, text="Czas między dzwonkiem a przeddzwonkiem:").grid(row=0, column=0, columnspan=4, pady=5)

            for i, interval in enumerate([0.5, 1, 1.5, 2]):
                ctk.CTkRadioButton(
                    radio_buttons_frame,
                    text=str(interval),
                    variable=self.interval_var,
                    value=interval,
                    font=ctk.CTkFont(family="Calibri", size=18, weight="bold"),
                    width=60, height=25,
                    radiobutton_height=40,
                    radiobutton_width=40
                ).grid(row=1, column=i, padx=5, pady=5)


    def __init__(self, master, schedule):
        super().__init__(master)
        self.master = master # BellApp
        self.schedule = schedule

        self.current_bell_frame = None 
        self.current_index = 0 

        # Zamiast top_frame i container, użyjmy grid dla całej ScheduleTab
        self.grid_rowconfigure(0, weight=1) # Wiersz dla głównego kontenera dzwonka
        self.grid_rowconfigure(1, weight=0) # Wiersz dla paska nawigacji
        self.grid_columnconfigure(0, weight=1) # Jedna kolumna rozciągająca się na całą szerokość

        # Główny kontener dla BellFrame i Utils
        self.main_content_frame = ctk.CTkFrame(self)
        self.main_content_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.main_content_frame.grid_columnconfigure(0, weight=1) # Kolumna dla BellFrame
        self.main_content_frame.grid_columnconfigure(1, weight=0) # Kolumna dla Utils (nie rozciągaj)
        self.main_content_frame.grid_columnconfigure(2, weight=0) # Kolumna dla Utils (nie rozciągaj)

        self.container = ctk.CTkFrame(self.main_content_frame)
        self.container.grid(row=0, column=0, sticky="nsew", padx=5) # Rozciągnij w poziomie i pionie

        self.utils = ctk.CTkFrame(self.main_content_frame)
        self.utils.grid(row=0, column=1, sticky="ns", padx=5) # Tylko pionowo, nie rozciągaj w poziomie

        ScheduleButton(self.utils, text="Dodaj dzwonek", command=self._add_bell).pack(side="top", pady=5, padx=5)
        ScheduleButton(self.utils, text="Usuń dzwonek", command=self._delete_bell).pack(side="top", pady=5, padx=5)
        ScheduleButton(self.utils, text="Zapisz zmiany", command=self._save_current_bell_to_file).pack(side="top", pady=5, padx=5)

        # Ramka nawigacji na dole, używając grid
        self.nav_frame = ctk.CTkFrame(self.main_content_frame)
        self.nav_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5, padx=5) # Rozciągnij w poziomie
        
        # Konfiguracja kolumn w nav_frame
        self.nav_frame.grid_columnconfigure(0, weight=1) # Lewy przycisk, rozciągnij
        self.nav_frame.grid_columnconfigure(1, weight=1) # Prawy przycisk, rozciągnij

        ScheduleButton(self.nav_frame, text="Poprzedni", command=self._show_prev_bell).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ScheduleButton(self.nav_frame, text="Następny", command=self._show_next_bell).grid(row=0, column=1, padx=5, pady=5, sticky="e")

        if not self.schedule.data["bellSchedule"]:
            self.schedule.addSchedule()

        # Tworzenie pojedynczej instancji BellFrame (bez on_data_change_callback)
        self.current_bell_frame = self.BellFrame(self.container, self.schedule)
        self.current_bell_frame.place(in_=self.container, relx=0, rely=0, relwidth=1, relheight=1)

        if self.schedule.data["bellSchedule"]:
            self._display_bell_at_index(0)
        else:
            self.show_message("Brak dzwonków do wyświetlenia, dodaj nowy.", "red")

    def _display_bell_at_index(self, index):
        """
        Zmienia wyświetlany dzwonek w pojedynczej BellFrame.
        Ładuje dane dla nowego indeksu do istniejącej BellFrame.
        """
        if not self.schedule.data["bellSchedule"]:
            logger.warning("No bells in schedule to display.")
            return

        if 0 <= index < len(self.schedule.data["bellSchedule"]):
            self.current_index = index
            self.current_bell_frame._load_bell_data(self.current_index)
            logger.info(f"Displayed bell at index: {index}")
        else:
            logger.warning(f"Attempted to display bell at invalid index: {index}")
            self.current_index = 0
            if self.schedule.data["bellSchedule"]:
                self.current_bell_frame._load_bell_data(self.current_index)
            else:
                self.show_message("Brak dzwonków do wyświetlenia. Dodaj pierwszy.", "orange")


    def _add_bell(self):
        """Dodaje nowy dzwonek do harmonogramu i wyświetla go."""
        if self.schedule.addSchedule(): 
            new_index = len(self.schedule.data["bellSchedule"]) - 1
            self._display_bell_at_index(new_index) 
            #self._save_current_bell_to_file_async() # Zapisz zmiany do pliku po dodaniu
            self.master.frames["main"].update_display(self.schedule.nextOccurrence, self.schedule.getFormattedScheduleList())
            self.show_message(f"Dzwonek {new_index + 1} dodany pomyślnie!", "green")
            logger.info("Added new bell.")
        else:
            self.show_message("Nie można dodać \n więcej dzwonków!", "red")
            logger.warning("Attempted to add bell, but reached maximum.")


    def _delete_bell(self):
        """Usuwa bieżący dzwonek i aktualizuje wyświetlanie."""
        if not self.schedule.data["bellSchedule"]:
            self.show_message("Brak dzwonków do usunięcia!", "orange")
            logger.warning("No bells to delete.")
            return

        deleted_index = self.current_index
        if self.schedule.deleteSchedule(deleted_index):
            if len(self.schedule.data["bellSchedule"]) == 0:
                self.schedule.addSchedule()
                self._display_bell_at_index(0)
                self.show_message("Wszystkie dzwonki usunięte. Dodano nowy domyślny.", "red")
            else:
                self.current_index = min(deleted_index, len(self.schedule.data["bellSchedule"]) - 1)
                self._display_bell_at_index(self.current_index)
                self.show_message(f"Dzwonek {deleted_index + 1} usunięty!", "orange")

            #self._save_current_bell_to_file_async() # Zapisz zmiany do pliku po usunięciu
            self.master.frames["main"].update_display(self.schedule.nextOccurrence, self.schedule.getFormattedScheduleList())
            logger.info(f"Deleted bell at index: {deleted_index}.")
        else:
            self.show_message(f"Nie udało się usunąć dzwonka {deleted_index + 1}. Musi być co najmniej 1 dzwonek.", "red")
            logger.error(f"Failed to delete bell at index {deleted_index}.")

    def _save_current_bell_to_file(self):
        """
        Zapisuje zmiany w aktualnie widocznej ramce dzwonka (które już są w self.schedule.data)
        do pliku JSON. Wywoływane przez przycisk "Zapisz zmiany".
        """
        self._save_current_bell_to_file_async()

    def _save_current_bell_to_file_async(self):
        """Uruchamia zapis zmian w osobnym wątku."""
        def save_in_thread():
            try:
                self.schedule.saveScheduleToJson() # To jest faktyczny zapis do pliku
                logger.info("Schedule saved to JSON.")
                self.after(0, lambda: self.show_message("Zmiany zapisane!", "green"))
            except Exception as e:
                logger.error(f"Error saving schedule to file: {e}")
                self.after(0, lambda: self.show_message(f"Błąd zapisu: {e}", "red"))
        threading.Thread(target=save_in_thread, daemon=True).start()

    def _show_next_bell(self):
        """Przechodzi do następnego dzwonka. Zachowuje zmiany przed przejściem."""
        if not self.schedule.data["bellSchedule"]:
            self.show_message("Brak dzwonków do nawigacji.", "orange")
            return
        
        # Opcjonalnie: Zapisz bieżące zmiany przed przejściem do następnego dzwonka
        # self._save_current_bell_to_file_async(show_message=False) 

        next_index = (self.current_index + 1) % len(self.schedule.data["bellSchedule"])
        self._display_bell_at_index(next_index)

    def _show_prev_bell(self):
        """Przechodzi do poprzedniego dzwonka. Zachowuje zmiany przed przejściem."""
        if not self.schedule.data["bellSchedule"]:
            self.show_message("Brak dzwonków do nawigacji.", "orange")
            return
        
        # Opcjonalnie: Zapisz bieżące zmiany przed przejściem do poprzedniego dzwonka
        # self._save_current_bell_to_file_async(show_message=False)

        prev_index = (self.current_index - 1 + len(self.schedule.data["bellSchedule"])) % len(self.schedule.data["bellSchedule"])
        self._display_bell_at_index(prev_index)

    def show_message(self, message, color="white"):
        """Wyświetla komunikat."""
        NotificationPopup(self.master, message, color=color)



class ClockTab(ctk.CTkFrame):
    """
    Zakładka zegara, wyświetlająca aktualny czas i pozwalająca na ustawienie
    czasu systemowego.
    """
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.top = ctk.CTkFrame(self)
        self.top.pack(side="top", fill="x")

        self.bottom = ctk.CTkFrame(self)
        self.bottom.pack(side="top", fill="both", expand=True)

        self.time_label = ctk.CTkLabel(self.top, text="", font=("Helvetica", 130))
        self.time_label.pack(pady=20)

        self.center_frame = ctk.CTkFrame(self.bottom)
        self.center_frame.pack(anchor="center", pady=20, fill="both")

        MyLabel(self.center_frame, text="Ustaw godzinę:").pack(pady=10)

        entry_frame = ctk.CTkFrame(self.center_frame)
        entry_frame.pack(fill="x")

        self.hour_entry_var = ctk.IntVar(value=datetime.now().hour)
        self.minute_entry_var = ctk.IntVar(value=datetime.now().minute)

        self.hour_entry = MySpinbox(entry_frame, min_value=0, max_value=23, width=180, height=60, 
                                     variable=self.hour_entry_var)
        self.hour_entry.pack(side="left", padx=40)

        self.minute_entry = MySpinbox(entry_frame, min_value=0, max_value=59, width=180, height=60, 
                                       variable=self.minute_entry_var)
        self.minute_entry.pack(side="left", padx=10)

        self.btn_save_clock = MyButton(entry_frame, text="Zapisz czas",                      
                      command=self._save_clock_time) 
        self.btn_save_clock.pack(pady=20, side="bottom")
        


    def update_time(self):
        """Aktualizuje wyświetlany czas na etykiecie zegara."""
        self.time_label.configure(text=datetime.now().strftime("%H:%M:%S"))

    def _save_clock_time(self):
        """
        Zapisuje ustawiony czas systemowy.
        Wymaga uprawnień administratora/roota na systemach Linux.
        """
        hour = self.hour_entry_var.get()
        minute = self.minute_entry_var.get()
        
        if clockHandling.set_system_time(hour=hour, minute=minute):
            #self.message_label.configure(text="Czas zapisany pomyślnie!", text_color="green")
            logger.info(f"Czas systemowy ustawiono na {hour:02d}:{minute:02d}.")
        else:
            #self.message_label.configure(text="Błąd zapisu czasu. Wymagane uprawnienia administratora.", text_color="red")
            logger.error(f"Nie udało się ustawić czasu systemowego na {hour:02d}:{minute:02d}.")
        #self.after(3000, lambda: self.message_label.configure(text=""))


class ScreensaverFrame(ctk.CTkFrame):
    """
    Ramka wygaszacza ekranu, wyświetlająca duży zegar i następny dzwonek.
    """
    def __init__(self, master):
        super().__init__(master, fg_color="#292727") # Ciemne tło
        
        # Etykieta dużego zegara
        self.clock_label = ctk.CTkLabel(
            self, 
            text=datetime.now().strftime("%H:%M:%S"), 
            font=ctk.CTkFont("Helvetica", 150), 
            text_color="white"
        )
        self.clock_label.place(relx=0.5, rely=0.5, anchor="center") # Wyśrodkowanie zegara
        
        # Konfiguracja siatki dla etykiety następnego dzwonka (umieszczona na górze)
        self.grid_rowconfigure(0, weight=1) # Górny rząd na etykietę dzwonka
        self.grid_rowconfigure(1, weight=1) # Dolny rząd (dla zegara, ale zegar używa place)
        self.grid_columnconfigure(0, weight=1)

        # Etykieta następnego dzwonka
        self.next_bell_label = MyLabel(self, text="") 
        self.next_bell_label.grid(row=0, column=0, pady=15, sticky="n") # Umieść na górze, wyśrodkowane

        # Pierwsza aktualizacja przy inicjalizacji
        # update_clock będzie wywoływane co sekundę przez BellApp._update_main_loop
        self.update_clock(master.schedule.nextOccurrence) 

    def update_clock(self, next_occurrence):
        """
        Aktualizuje wyświetlanie zegara i następnego dzwonka na wygaszaczu ekranu.
        Wywoływane co sekundę przez główną pętlę aplikacji.
        """
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=now)
        self.next_bell_label.configure(text= next_occurrence)
        
class PopupFrame(ctk.CTkFrame):
    """
    Ramka wygaszacza ekranu, wyświetlająca duży zegar i następny dzwonek.
    """
    def __init__(self, master):
        super().__init__(master, fg_color="#292727") # Ciemne tło
        
        # Etykieta dużego zegara
        self.clock_label = ctk.CTkLabel(
            self, 
            text=datetime.now().strftime("%H:%M:%S"), 
            font=ctk.CTkFont("Helvetica", 150), 
            text_color="white"
        )


class LoginScreen(ctk.CTkFrame):
    """
    Ekran logowania wyświetlany przy starcie aplikacji.
    Układ: Lewa strona - Pole PIN, Prawa strona - Klawiatura.
    """
    def __init__(self, master, auth_handler):
        super().__init__(master)
        self.master = master
        self.auth = auth_handler
        
        self.pack_propagate(False)
        
        # Główny kontener wyśrodkowany na ekranie
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # --- LEWA STRONA (Input) ---
        self.input_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=40, pady=20, sticky="n")

        self.label = ctk.CTkLabel(self.input_frame, text="Podaj kod PIN", font=("Calibri", 30, "bold"))
        self.label.pack(pady=(0, 20))

        self.pin_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self.input_frame, textvariable=self.pin_var, show="*", 
                                  font=("Calibri", 50), width=250, height=60, justify="center")
        self.entry.pack(pady=10)

        # --- PRAWA STRONA (Klawiatura) ---
        self.keypad_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.keypad_frame.grid(row=0, column=1, padx=40, pady=20)

        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('⌫', 3, 0), ('0', 3, 1), ('OK', 3, 2),
        ]

        for key, row, col in keys:
            if key == 'OK':
                color = "green"
                cmd = self._check_login
            elif key == '⌫':
                color = "#a83232" # czerwony
                cmd = self._clear_entry
            else:
                color = None # domyślny
                cmd = lambda k=key: self._add_digit(k)

            # Powiększyłem przyciski dla wygody dotykowej
            btn = ctk.CTkButton(self.keypad_frame, text=key, width=80, height=80, 
                                font=("Calibri", 32, "bold"), command=cmd)
            if color:
                btn.configure(fg_color=color)
            btn.grid(row=row, column=col, padx=4, pady=4)

    def _add_digit(self, digit):
        if len(self.pin_var.get()) < 6: # Limit długości pinu
            self.pin_var.set(self.pin_var.get() + digit)

    def _clear_entry(self):
        self.pin_var.set("")

    def _check_login(self):
        pin = self.pin_var.get()
        if self.auth.check_pin(pin):
            self.entry.configure(border_color="green")
            self.master.unlock_application()
            self._clear_entry()
        else:
            self.entry.configure(border_color="red")
            # Używamy NotificationPopup bezpośrednio, bo frames["popup"] może nie być zainicjowane
            NotificationPopup(self.master, "Błędny PIN!", color="red") 
            self.pin_var.set("")


class SecurityTab(ctk.CTkFrame):
    """
    Zakładka do zmiany hasła.
    Układ: Lewa strona - Pola edycji, Prawa strona - Klawiatura.
    Obsługuje przełączanie aktywnego pola dotykiem.
    """
    def __init__(self, master, auth_handler):
        super().__init__(master)
        self.auth = auth_handler
        
        # Główny kontener wyśrodkowany
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.place(relx=0.5, rely=0.4, anchor="center")

        # --- LEWA STRONA (Pola wprowadzania) ---
        self.input_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=40, pady=20, sticky="n")

        MyLabel(self.input_frame, text="Ustaw nowy PIN:").pack(pady=(30, 0))

        # Zmienne przechowujące wartości
        self.new_pin_var = ctk.StringVar()
        self.confirm_pin_var = ctk.StringVar()
        
        # Zmienna wskazująca, które pole jest aktualnie edytowane (domyślnie pierwsze)
        self.active_var = self.new_pin_var 

        # Pole 1: Nowy PIN
        self.entry_new = ctk.CTkEntry(self.input_frame, textvariable=self.new_pin_var, placeholder_text="Nowy PIN", 
                                      show="*", font=("Calibri", 24), width=300, height=50, justify="center")
        self.entry_new.pack(pady=15)
        # Bind events: Kliknięcie w pole ustawia je jako aktywne
        self.entry_new.bind("<Button-1>", lambda event: self._set_active_field(self.new_pin_var, self.entry_new))
        self.entry_new.bind("<FocusIn>", lambda event: self._set_active_field(self.new_pin_var, self.entry_new))
        MyLabel(self.input_frame, text="Powtórz nowy PIN:").pack(pady=(20, 0))
        # Pole 2: Potwierdź PIN
        self.entry_confirm = ctk.CTkEntry(self.input_frame, textvariable=self.confirm_pin_var, placeholder_text="Potwierdź PIN", 
                                          show="*", font=("Calibri", 24), width=300, height=50, justify="center")
        self.entry_confirm.pack(pady=15)
        self.entry_confirm.bind("<Button-1>", lambda event: self._set_active_field(self.confirm_pin_var, self.entry_confirm))
        self.entry_confirm.bind("<FocusIn>", lambda event: self._set_active_field(self.confirm_pin_var, self.entry_confirm))

        # Przycisk Zapisu
        MyButton(self.input_frame, text="Zapisz zmiany", command=self._save_new_pin, width=300, height=80).pack(pady=30)


        # --- PRAWA STRONA (Klawiatura) ---
        self.keypad_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.keypad_frame.grid(row=0, column=1, padx=40)

        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('⌫', 3, 0), ('0', 3, 1), # Zmiana: DEL (backspace) i CLR (czyść wszystko)
        ]

        for key, row, col in keys:
            cmd = None
            color = None
            if key == '⌫':
                color = "#d97b23" # pomarańczowy dla backspace
                cmd = self._backspace
            else:
                cmd = lambda k=key: self._add_digit(k)

            btn = ctk.CTkButton(self.keypad_frame, text=key, width=80, height=80, 
                                font=("Calibri", 32, "bold"), command=cmd)
            if color:
                btn.configure(fg_color=color)
            btn.grid(row=row, column=col, padx=4, pady=4)

        # Ustawienie wizualne aktywnego pola na starcie
        self._set_active_field(self.new_pin_var, self.entry_new)

    def _set_active_field(self, variable, widget):
        """Ustawia aktywne pole do edycji i podświetla je."""
        self.active_var = variable
        
        # Reset kolorów ramek
        self.entry_new.configure(border_color=["#979da2", "#565b5e"]) # Domyślne kolory ctk
        self.entry_confirm.configure(border_color=["#979da2", "#565b5e"])
        
        # Podświetl aktywne pole
        widget.configure(border_color="#1f538d") # Kolor akcentu (niebieski)

    def _add_digit(self, digit):
        """Dodaje cyfrę do aktualnie aktywnego pola."""
        if len(self.active_var.get()) < 8:
            self.active_var.set(self.active_var.get() + digit)

    def _backspace(self):
        """Usuwa ostatni znak z aktywnego pola."""
        current_text = self.active_var.get()
        if len(current_text) > 0:
            self.active_var.set(current_text[:-1])

    def _save_new_pin(self):
        p1 = self.new_pin_var.get()
        p2 = self.confirm_pin_var.get()

        if not p1 or not p2:
             NotificationPopup(self.master, "Pola nie mogą być puste", color="orange")
             return

        if len(p1) < 4:
             NotificationPopup(self.master, "Podany PIN jest za krótki - minimum 4 cyfry)", color="orange")
             return

        if p1 == p2:
            if self.auth.set_user_pin(p1):
                NotificationPopup(self.master, "Hasło zmienione!", color="green")
                self.new_pin_var.set("")
                self.confirm_pin_var.set("")
                # Reset focusu na pierwsze pole
                self._set_active_field(self.new_pin_var, self.entry_new)
            else:
                NotificationPopup(self.master, "Błąd zapisu.", color="red")
        else:
            NotificationPopup(self.master, "Hasła nie są identyczne", color="red")