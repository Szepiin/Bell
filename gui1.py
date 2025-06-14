import customtkinter as ctk
from datetime import datetime
import tkinter as tk
from CTkSpinbox import * # Zakładam, że CTkSpinbox jest poprawnie zaimportowany i działa
import clockHandling # Zakładam, że clockHandling jest poprawnie zaimportowany
import time
import threading
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Konfiguracja CTk (zachowane z oryginalnego pliku)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class NotificationPopup(ctk.CTkToplevel):
    """
    Niestandardowe okno pop-up do wyświetlania krótkich komunikatów.
    Zamyka się automatycznie po określonym czasie lub po kliknięciu.
    """
    def __init__(self, master, message, duration_ms=2500, color="white"):
        super().__init__(master)
        self.master = master
        self.overrideredirect(True)  # Usuwa ramkę okna i przyciski systemowe
        self.attributes("-topmost", True)  # Zawsze na wierzchu innych okien aplikacji

        self.label = ctk.CTkLabel(self, text=message, font=("Calibri", 40, "bold"), text_color=color, anchor="center")
        self.label.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.grab_set() # Zablokuj interakcję z innymi oknami aplikacji, dopóki pop-up jest otwarty
        self.bind("<Button-1>", self.close_popup) # Zamyka po kliknięciu

        # Umieszczenie pop-upu dokładnie nad oknem głównym
        self.update_idletasks()
        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_w = self.master.winfo_width()
        master_h = self.master.winfo_height()
        self.geometry(f"{master_w}x{master_h}+{master_x}+{master_y}")


        self.attributes("-alpha", 0.95)
        self.after(duration_ms, self.close_popup) # Ustaw timer na automatyczne zamknięcie

    def close_popup(self, event=None):
        """Zamyka okno pop-up."""
        if self.winfo_exists(): # Sprawdź, czy okno jeszcze istnieje przed zniszczeniu
            self.grab_release() # Zwolnij blokadę interakcji
            self.destroy()


class MyButton(ctk.CTkButton):
    """Niestandardowy przycisk z predefiniowanymi stylami."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("hover", False)
        kwargs.setdefault("width", 250)
        kwargs.setdefault("height", 90)
        kwargs.setdefault("font", ctk.CTkFont(family="Calibri", size=22, weight="bold"))
        super().__init__(*args, **kwargs)

class ScheduleButton(ctk.CTkButton):
    """Niestandardowy przycisk z predefiniowanymi stylami."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("hover", False)
        kwargs.setdefault("width", 210)
        kwargs.setdefault("height", 80)
        kwargs.setdefault("font", ctk.CTkFont(family="Calibri", size=22, weight="bold"))
        super().__init__(*args, **kwargs)

class MyLabel(ctk.CTkLabel):
    """Niestandardowa etykieta z predefiniowanymi stylami."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("font", ctk.CTkFont(family="Calibri", size=22, weight="bold"))
        super().__init__(*args, **kwargs)        


class BellApp(ctk.CTk):
    """
    Główna klasa aplikacji dzwonkowej.
    Zarządza ramkami, nawigacją, zegarem systemowym i logiką wygaszacza ekranu.
    """
    def __init__(self, music, schedule, screensaver_time):
        super().__init__()
        self.music = music
        self.schedule = schedule
        self.screensaver_time = screensaver_time 

        self.title("Dzwonek")
        self.geometry("800x480")
        # Można odkomentować dla trybu pełnoekranowego:
        # self.attributes("-fullscreen", True)
        # self.config(cursor="none")

        self.frames = {} # Słownik przechowujący instancje ramek
        self.current_frame_name = None # Nazwa aktualnie wyświetlanej ramki

        self.create_tab_buttons()
        self.create_frames()
        self.show_frame("main") # Wyświetl ekran główny przy starcie

        # Logika wygaszacza ekranu
        self.last_activity_time = time.time()
        self.bind_all("<Button>", self._reset_inactivity_timer) # Śledzenie kliknięć myszy
        self.bind_all("<Key>", self._reset_inactivity_timer)     # Śledzenie naciśnięć klawiszy
        self.after(1000, self._check_inactivity) # Rozpocznij sprawdzanie bezczynności

        self.protocol("WM_DELETE_WINDOW", self._on_close) # Obsługa zamykania okna
        self.after(1000, self._update_main_loop) # Rozpocznij główną pętlę aktualizacji

    def create_tab_buttons(self):
        """Tworzy ramkę z przyciskami nawigacyjnymi (zakładkami)."""
        self.tab_buttons_frame = ctk.CTkFrame(self)
        self.tab_buttons_frame.pack(side="top", fill="x")

        buttons = [
            ("Ekran główny", "main"),
            ("Ustawienia\ndzwonków", "sounds"),
            ("Harmonogram", "schedule"),
            ("Zegar", "clock"),
        ]

        for text, name in buttons:
            ctk.CTkButton(
                self.tab_buttons_frame,
                text=text,
                height=80,
                hover=False,
                font=ctk.CTkFont(family="Calibri", size=24, weight="bold"),
                command=lambda n=name: self.show_frame(n),
            ).pack(side="left", fill="both", expand=True, padx=3, pady=5)


    def create_frames(self):
        """Tworzy instancje wszystkich ramek aplikacji."""
        self.frames["main"] = MainScreen(self)
        self.frames["sounds"] = SoundSettings(self)
        self.frames["schedule"] = ScheduleTab(self, self.schedule)
        self.frames["clock"] = ClockTab(self)
        self.frames["screensaver"] = ScreensaverFrame(self)

        # Umieszczenie wszystkich ramek w tym samym miejscu, aby można było je przełączać
        for frame in self.frames.values():
            if frame != self.frames["screensaver"]: 
                frame.place(x=0, y=90, relwidth=1, relheight=1) # Ramki pod paskiem przycisków
            else:
                frame.place(x=0, y=0, relwidth=1, relheight=1) # Wygaszacz ekranu zajmuje cały ekran

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
                if frame_name != "screensaver":
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
            self.show_frame("main")
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
        self.schedule_display_frame._scrollbar.configure(width=30)
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

        self.left = ctk.CTkFrame(self)
        self.left.pack(side="left", fill="both", expand=True)

        self.right = ctk.CTkFrame(self)
        self.right.pack(side="right", fill="both", expand=True)

        # Przycisk odtwarzania/zatrzymywania dzwonka
        self.btnPlayBell = MyButton(
            self.left,
            text="", # Tekst zostanie ustawiony przez _update_button_texts
            fg_color="#1f538d",
            command=self._toggle_bell_btn,
        )
        self.btnPlayBell.pack(pady=30)

        # Przycisk odtwarzania/zatrzymywania przeddzwonka
        self.btnPlayPrebell = MyButton(
            self.left,
            text="", # Tekst zostanie ustawiony przez _update_button_texts
            fg_color="#1f538d",
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
        self.btnToggleWeekend = MyButton(self.right, text="", command=self._toggle_weekend_btn, fg_color="")
        self._update_weekend_button_text() # Ustaw początkowy tekst i kolor
        self.btnToggleWeekend.pack(pady=30, fill="y")

        self._update_button_texts() # Upewnij się, że tekst przycisków jest aktualny przy inicjalizacji

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
            self.btnPlayBell.configure(text=f"Odtwórz / zatrzymaj\ndzwonek\n{self.master.music.musicFileNameBell}", state="normal", fg_color="#1f538d")
            self.btnPlayPrebell.configure(text=f"Odtwórz / zatrzymaj\nprzeddzwonek\n{self.master.music.musicFileNamePrebell}", state="normal",fg_color="#1f538d")
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
            self.btnToggleWeekend.configure(text="Tryb weekendowy:\nDzwonki nieaktywne ❌", fg_color="#5e5e5e")
        else:
            self.btnToggleWeekend.configure(text="Tryb weekendowy:\nDzwonki aktywne ✅", fg_color="#969696")

    def _toggle_weekend_btn(self):
        """Obsługuje kliknięcie przycisku trybu weekendowego: przełącza stan."""
        self.master.schedule.noWeekend = not self.master.schedule.noWeekend 
        self._update_weekend_button_text()
        self.master.schedule.saveScheduleToJson() # Zapisz zmianę stanu weekendu
        logger.info(f"Tryb weekendowy: {'Dzwonki nieaktywne' if self.master.schedule.noWeekend else 'Dzwonki aktywne'}")

class ScheduleTab(ctk.CTkFrame):
    class BellFrame(ctk.CTkFrame):
        def __init__(self, master_tab, index, schedule):
            super().__init__(master_tab)
            self.master_tab = master_tab 
            self.index = index
            self.schedule = schedule
            self.schedule_data = self.schedule.data

            self.hour_var = tk.IntVar()
            self.minute_var = tk.IntVar()
            self.interval_var = tk.DoubleVar()
            self.active_var = tk.BooleanVar()

            self._load_bell_data()
            self._build_gui()

        def _load_bell_data(self):
            """Ładuje dane dla bieżącego dzwonka."""
            if 0 <= self.index < len(self.schedule_data["bellSchedule"]):
                time_str = self.schedule_data["bellSchedule"][self.index]
                try:
                    self.hour_var.set(int(time_str.split(":")[0]))
                    self.minute_var.set(int(time_str.split(":")[1]))
                except ValueError:
                    logger.error(f"Błąd parsowania czasu dla dzwonka {self.index}: {time_str}. Ustawiam na 00:00.")
                    self.hour_var.set(0)
                    self.minute_var.set(0)

                self.interval_var.set(self.schedule_data["prebellIntervals"][self.index])
                self.active_var.set(self.schedule_data["bellActive"][self.index])
            else:
                logger.warning(f"Próba załadowania danych dla nieistniejącego indeksu dzwonka: {self.index}")
                # Można tu ustawić wartości domyślne dla nowo dodanych dzwonków

        def _build_gui(self):
            
            # Konfiguracja kolumn i wierszy siatki (rozmiary i rozciąganie)
            self.grid_columnconfigure(0, weight=1, minsize=150)  # lewa kolumna (checkbox)
            self.grid_columnconfigure(1, weight=1, minsize=150)  # prawa kolumna (spinboxy)
            self.grid_columnconfigure(2, weight=1, minsize=150) 
            self.grid_rowconfigure(0, weight=0, minsize=22)   # nagłówek
            self.grid_rowconfigure(1, weight=1, minsize=22)   # checkbox + godzina
            self.grid_rowconfigure(2, weight=1, minsize=22)   # minuta
            self.grid_rowconfigure(3, weight=0, minsize=22)  # radio buttony

            self.label_frame = ctk.CTkFrame(self)
            self.label_frame.grid(row=0, column=0, columnspan=3, rowspan=1,  sticky="ew", pady=(1, 2))
            self.label_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(self.label_frame, text=f"Dzwonek {self.index + 1} z {len(self.schedule_data['bellSchedule'])}",
                         font=ctk.CTkFont(family="Calibri", size=24, weight="bold")).grid(pady=(0, 5))

            # Checkbox aktywny
            ctk.CTkCheckBox(
                self,
                text="Aktywny",
                variable=self.active_var,
                font=ctk.CTkFont(family="Calibri", size=22, weight="bold"),
                checkbox_width=50, 
                checkbox_height=50
            ).grid(row=1, column=0, rowspan=2)

            

            MyLabel(self, text="Godzina:").grid(row=1, column=1, sticky="s", pady=5)
            CTkSpinbox(
                self,
                start_value=self.hour_var.get(),
                min_value=0, max_value=23, step_value=1,
                variable=self.hour_var,
                width=180, height=60,
                font=ctk.CTkFont(family="Calibri", size=22, weight="bold")
            ).grid(row=2, column=1, sticky="n")

            MyLabel(self, text="Minuta:").grid(row=1, column=2, sticky="s", pady=5)
            CTkSpinbox(
                self,
                start_value=self.minute_var.get(),
                min_value=0, max_value=59, step_value=1,
                variable=self.minute_var,
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


            # Przyciski akcji - zostają w ScheduleTab
            # MyButton(buttons_frame, text="Dodaj dzwonek", command=self.master_tab.add_frame).pack(pady=5, fill="x")
            # MyButton(buttons_frame, text="Usuń dzwonek", command=self.master_tab.del_frame).pack(pady=5, fill="x")
            #MyButton(self, text="Zapisz zmiany", command=self._save_changes_and_refresh).grid(row=2, column=0, columnspan=2, pady=10)


        def _save_changes_and_refresh_async(self):
            """Uruchamia zapis zmian w osobnym wątku i pokazuje overlay ładowania."""
            def save_in_thread():

                try:
                    hour = self.hour_var.get()
                    minute = self.minute_var.get()

                    self.schedule_data["bellSchedule"][self.index] = f"{hour:02d}:{minute:02d}"
                    self.schedule_data["prebellIntervals"][self.index] = self.interval_var.get()
                    self.schedule_data["bellActive"][self.index] = self.active_var.get()

                    # Zapisz dane
                    self.schedule.saveScheduleToJson()
                    logger.info(f"Zapisano zmiany dla dzwonka {self.index + 1}.")

                    # Odśwież GUI w wątku głównym
                    self.schedule_display_after_update()

                except Exception as e:
                    logger.error(f"Błąd podczas zapisywania zmian dla dzwonka {self.index + 1}: {e}")
                    self.master_tab.after(0, lambda: self.master_tab.show_message(f"Błąd zapisu: {e}", "red"))
                finally:
                    pass
                    # Ukryj overlay
                    #self.master_tab.after(0, self._hide_loading_overlay)

            # Pokaż overlay ładowania
            #self._show_loading_overlay("Zapisywanie...")
            
            threading.Thread(target=save_in_thread, daemon=True).start()
            
        def schedule_display_after_update(self):
            def update():
                self.master_tab.master.frames["main"].update_display(
                    self.schedule.nextOccurrence,
                    self.schedule.getFormattedScheduleList()
                )
                self.master_tab._rebuild_bell_frames()
                self.master_tab.show_frame(self.index)
                self.master_tab.show_message("Zmiany zapisane!", "green")
            self.master_tab.after(0, update)
            

    def __init__(self, master, schedule):
        super().__init__(master)
        self.master = master # BellApp
        self.schedule = schedule

        self.bell_frames = []
        self.current_index = 0

        # Górny kontener na lewą i prawą część
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(side="top", fill="both", padx=2, pady=2)

        # Lewa część - container
        self.container = ctk.CTkFrame(self.top_frame)
        self.container.pack(side="left", fill="both", expand=True, padx=5)

        # Prawa część - utils (z przyciskami)
        self.utils = ctk.CTkFrame(self.top_frame)
        self.utils.pack(side="right", anchor="n")  # nie filluje x, bierze tyle ile potrzebuje

        ScheduleButton(self.utils, text="Dodaj dzwonek", command=self.add_frame).pack(side="top", pady=5, padx=5)
        ScheduleButton(self.utils, text="Usuń dzwonek", command=self.del_frame).pack(side="top", pady=5, padx=5)
        ScheduleButton(self.utils, text="Zapisz zmiany", command=self.save_current_bell).pack(side="top", pady=5, padx=5)

        # Dolna część - nav_frame
        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(side="top", fill="x", pady=5, padx=2)

        ScheduleButton(self.nav_frame, text="Poprzedni", command=self.show_prev).pack(side="left", padx=5, pady=2)
        ScheduleButton(self.nav_frame, text="Następny", command=self.show_next).pack(side="right", padx=5, pady=2)


        if not self.schedule.data["bellSchedule"]:
            self.schedule.addSchedule()

        self._rebuild_bell_frames() 
        if self.bell_frames:
            self.show_frame(0)

    def _rebuild_bell_frames_OLD(self):
        pass
        """Niszczy i ponownie buduje wszystkie ramki dzwonków, odświeżając dane."""
        for frame in self.bell_frames:
            frame.destroy()
        self.bell_frames.clear()

        schedule_data = self.schedule.data
        for i in range(len(schedule_data["bellSchedule"])):
            frame = self.BellFrame(self, i, self.schedule)
            frame.place(in_=self.container, relx=0, rely=0, relwidth=1, relheight=1)
            self.bell_frames.append(frame)
        logger.info("Ramki dzwonków zostały przebudowane.")

    def _rebuild_bell_frames(self):

        try:
            schedule_data = self.schedule.data
            indices = list(range(len(schedule_data["bellSchedule"])))

            for frame in self.bell_frames:
                frame.destroy()
            self.bell_frames.clear()

            for i in indices:
                frame = self.BellFrame(self, i, self.schedule)
                frame.place(in_=self.container, relx=0, rely=0, relwidth=1, relheight=1)
                self.bell_frames.append(frame)

            logger.info("Ramki dzwonków przebudowane.")
        except Exception as e:
            logger.error(f"Błąd przebudowy ramek: {e}")
            self.after(0, lambda: self.show_message(f"Błąd: {e}", "red"))


    def show_frame(self, index):
        """Pokazuje ramkę o podanym indeksie."""
        if not self.bell_frames:
            logger.warning("Brak ramek dzwonków do wyświetlenia.")
            return

        if 0 <= index < len(self.bell_frames):
            for frame in self.bell_frames:
                frame.lower()
            self.bell_frames[index].lift()
            self.current_index = index
            logger.info(f"Wyświetlono ramkę dzwonka o indeksie: {index}")
        else:
            logger.warning(f"Próba wyświetlenia ramki dzwonka o nieprawidłowym indeksie: {index}")


    def add_frame(self):
        """Dodaje nową ramkę dzwonka i aktualizuje harmonogram."""
        if self.schedule.addSchedule(): 
            self.show_message("Odświeżanie...")
            self._rebuild_bell_frames()
            self.show_frame(0) 
            self.master.frames["main"].update_display(self.schedule.nextOccurrence, self.schedule.getFormattedScheduleList())
            self.show_message("Dzwonek 1 - 6:00 - dodany pomyślnie!", "green")
        else:
            self.show_message("Nie można dodać więcej dzwonków (maks. 24)!", "red")
        logger.info("Próba dodania dzwonka.")


    def del_frame(self):
        """Usuwa bieżącą ramkę dzwonka i aktualizuje harmonogram."""
        if not self.bell_frames:
            self.show_message("Brak dzwonków do usunięcia!", "orange")
            logger.warning("Brak ramek dzwonków do usunięcia.")
            return

        deleted_index = self.current_index
        if self.schedule.deleteSchedule(deleted_index):
            self.show_message("Odświeżanie...")
            self._rebuild_bell_frames() 
            self.master.frames["main"].update_display(self.schedule.nextOccurrence, self.schedule.getFormattedScheduleList())

            self.current_index = max(0, self.current_index - 1)
            if self.bell_frames:
                self.show_frame(self.current_index)
                self.show_message(f"Dzwonek {deleted_index + 1} usunięty!", "orange")
            else:
                self.show_message("Wszystkie dzwonki usunięte. Dodaj nowy.", "red")
                self.schedule.addSchedule() # Automatycznie dodaj pusty dzwonek, jeśli wszystkie usunięto
                self._rebuild_bell_frames()
                self.show_frame(0)
            logger.info(f"Usunięto dzwonek o indeksie: {deleted_index}.")
        else:
            self.show_message(f"Nie udało się usunąć dzwonka {deleted_index + 1}.", "red")

    def save_current_bell(self):
        """Zapisuje zmiany w aktualnie widocznej ramce dzwonka."""
        if 0 <= self.current_index < len(self.bell_frames):
            self.show_message("Zapisywanie...", color="white")
            self.bell_frames[self.current_index]._save_changes_and_refresh_async()
        else:
            self.show_message("Brak aktywnego dzwonka do zapisania!", "red")
            logger.warning("Próba zapisania bez aktywnej ramki dzwonka.")


    def show_next(self):
        """Przechodzi do następnego dzwonka."""
        if self.current_index + 1 < len(self.bell_frames):
            self.show_frame(self.current_index + 1)
        else:
            self.show_message("Ostatni dzwonek.", "gray")
            logger.info("Ostatni dzwonek, nie można przejść dalej.")

    def show_prev(self):
        """Przechodzi do poprzedniego dzwonka."""
        if self.current_index > 0:
            self.show_frame(self.current_index - 1)
        else:
            self.show_message("Pierwszy dzwonek.", "gray")
            logger.info("Pierwszy dzwonek, nie można przejść wstecz.")

    def show_message(self, message, color="white"):
        """Wyświetla komunikat jako pop-up w głównym wątku."""
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

        # Zmienne instancji dla spinboxów, inicjalizowane aktualnym czasem
        self.hour_entry_var = ctk.IntVar(value=datetime.now().hour)
        self.minute_entry_var = ctk.IntVar(value=datetime.now().minute)

        self.hour_entry = CTkSpinbox(entry_frame, min_value=0, max_value=23, width=180, height=60, 
                                     variable=self.hour_entry_var, start_value=datetime.now().hour, font=("size",24))
        self.hour_entry.pack(side="left", padx=50)

        self.minute_entry = CTkSpinbox(entry_frame, min_value=0, max_value=59, width=180, height=60, 
                                       variable=self.minute_entry_var, start_value=datetime.now().minute, font=("size",24))
        self.minute_entry.pack(side="left", padx=10)

        self.btn_save_clock = MyButton(entry_frame, text="Zapisz czas",                      
                      command=self._save_clock_time) 
        self.btn_save_clock.pack(pady=20, side="bottom")
        
        # Etykieta do wyświetlania komunikatów o zapisie czasu
        self.message_label = MyLabel(self.center_frame, text="", text_color="green")
        self.message_label.pack(pady=5)


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
            self.message_label.configure(text="Czas zapisany pomyślnie!", text_color="green")
            logger.info(f"Czas systemowy ustawiono na {hour:02d}:{minute:02d}.")
        else:
            self.message_label.configure(text="Błąd zapisu czasu. Wymagane uprawnienia administratora.", text_color="red")
            logger.error(f"Nie udało się ustawić czasu systemowego na {hour:02d}:{minute:02d}.")
        self.after(3000, lambda: self.message_label.configure(text="")) # Usuń komunikat po 3 sekundach


class ScreensaverFrame(ctk.CTkFrame):
    """
    Ramka wygaszacza ekranu, wyświetlająca duży zegar i następny dzwonek.
    """
    def __init__(self, master):
        super().__init__(master, fg_color="#292727") # Ciemne tło
        
        # Etykieta dużego zegara
        self.clock_label = ctk.CTkLabel(
            self, 
            text="", 
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