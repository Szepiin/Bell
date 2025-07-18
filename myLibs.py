import customtkinter as ctk

class MySpinbox(ctk.CTkFrame):
    def __init__(self, master, width=130, height=30, step_size=1, command=None, 
                 variable=None, min_value=None, max_value=None, font=None, **kwargs):
        
        super().__init__(master, width=width, height=height, border_width=2, border_color="#2b2b2b", **kwargs)

        self.step_size = step_size
        self.command = command
        self.min_value = min_value
        self.max_value = max_value
        self.font = font

        if variable is None:
            self.variable = ctk.IntVar(value=0)
        else:
            self.variable = variable
            
        # Zapisz ID śledzenia
        self._trace_id = self.variable.trace_add("write", self._variable_callback) 

        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.subtract_button = ctk.CTkButton(self, text="-", width=height, height=height, font=ctk.CTkFont(size=22, weight='bold'),
                                             command=self._subtract_button_callback)
        self.subtract_button.grid(row=0, column=0, sticky="nswe", padx=4, pady=4)

        self.entry = ctk.CTkEntry(self, width=width - (2 * height), height=height, font=ctk.CTkFont(size=22, weight='bold'),
                                  border_width=0, bg_color="#2b2b2b", fg_color="#2b2b2b", justify="center")
        self.entry.grid(row=0, column=1, sticky="nswe", pady=4)
        self.entry.configure(state="readonly")
        if self.font:
            self.entry.configure(font=self.font)

        self.add_button = ctk.CTkButton(self, text="+", width=height, height=height, font=ctk.CTkFont(size=22, weight='bold'),
                                        command=self._add_button_callback)
        self.add_button.grid(row=0, column=2, sticky="nswe", padx=4, pady=4)

        self.subtract_button.configure(fg_color=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"]), hover=False)
        self.add_button.configure(fg_color=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"]), hover=False)
        self.entry.configure(fg_color=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"]),
                             text_color=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkEntry"]["text_color"]))
        self._update_entry_from_variable()

    # Dodaj metodę do zarządzania śledzeniem
    def _manage_trace(self, action):
        if action == "remove" and self._trace_id:
            self.variable.trace_remove("write", self._trace_id)
            self._trace_id = None
        elif action == "add" and not self._trace_id:
            self._trace_id = self.variable.trace_add("write", self._variable_callback)


    def _update_entry_from_variable(self):
        self.entry.configure(state="normal")
        self.entry.delete(0, ctk.END)
        self.entry.insert(0, str(self.variable.get()))
        self.entry.configure(state="readonly")

    def _variable_callback(self, var_name, index, mode):
        self._update_entry_from_variable()
        if self.command is not None:
            self.command(self.variable.get())

    def _set_value_and_notify(self, new_value):
        if self.min_value is not None and new_value < self.min_value:
            new_value = self.max_value if self.max_value is not None else self.min_value
        if self.max_value is not None and new_value > self.max_value:
            new_value = self.min_value if self.min_value is not None else self.min_value 
        
        self.variable.set(new_value) 

    def _add_button_callback(self):
        current_value = self.variable.get()
        self._set_value_and_notify(current_value + self.step_size)

    def _subtract_button_callback(self):
        current_value = self.variable.get()
        self._set_value_and_notify(current_value - self.step_size)

    def get(self):
        return self.variable.get()

    def set(self, value):
        self._set_value_and_notify(int(value)) 


class NotificationPopup(ctk.CTkToplevel):
    """
    Niestandardowe okno pop-up do wyświetlania krótkich komunikatów.
    Zamyka się automatycznie po określonym czasie lub po kliknięciu.
    """
    _closed = False
    def __init__(self, master, message, duration_ms=2500, color="white"):
        super().__init__(master)
        self.master = master
        self.overrideredirect(True)  # Usuwa ramkę okna i przyciski systemowe
        self.attributes("-topmost", True)  # Zawsze na wierzchu innych okien aplikacji

        self.config(cursor="none")
        self.update_idletasks()
        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_w = self.master.winfo_screenwidth()
        master_h = self.master.winfo_screenheight()
        self.geometry(f"{master_w}x{master_h}+{master_x}+{master_y}")
        
        self.label = ctk.CTkLabel(self, text=message, font=("Calibri", 40, "bold"), text_color=color, anchor="center")
        self.label.pack(fill="both", expand=True, padx=20, pady=20)
        
        #self.grab_set() # Zablokuj interakcję z innymi oknami aplikacji, dopóki pop-up jest otwarty
        self.bind("<Button-1>", self.close_popup) # Zamyka po kliknięciu
        self.label.bind("<Button-1>", self.close_popup)
        



        self.attributes("-alpha", 0.95)
        self._closed = False
        self.after(duration_ms, self.close_popup) # Ustaw timer na automatyczne zamknięcie

    def close_popup(self, event=None):
        """Zamyka okno pop-up."""
        if not self._closed and self.winfo_exists(): # Sprawdź, czy okno jeszcze istnieje przed zniszczeniu
            self._closed = True
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
