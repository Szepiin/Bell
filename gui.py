import pygame
import os
import time
from datetime import datetime, timedelta
import threading
import json
import platform


import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from CTkSpinbox import *

import customtkinter as ctk


from schedule import scheduleHandling

scheduleData = scheduleHandling()
button_width = 200
button_height = 65



class frMain(ctk.CTkFrame):

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)


        self.next_time_label = ctk.CTkLabel(self, text="Brak następnych wystąpień")
        self.next_time_label.pack(fill="x", pady=10)

        self.main_screen_tab_mid = ctk.CTkFrame(self)
        self.main_screen_tab_mid.pack(fill="both", expand=True)

        self.main_screen_tabL = ctk.CTkFrame(self.main_screen_tab_mid)
        self.main_screen_tabL.pack(side="left", fill="both", expand=True, pady=5)

        self.main_screen_tabR = ctk.CTkFrame(self.main_screen_tab_mid)
        self.main_screen_tabR.pack(side="right", fill="both", expand=True, pady=5)

        self.occurrences_list = []

        self.update_occurrences_list()

    def update_occurrences_list(self):
        for widget in self.main_screen_tabL.winfo_children():
            widget.destroy()
        for widget in self.main_screen_tabR.winfo_children():
            widget.destroy()

        self.occurrences_list = []
        for index, entry in enumerate(scheduleData.data["bellSchedule"]):
            status = "Aktywny" if scheduleData.data["bellActive"][index] else "Nieaktywny"
            self.occurrences_list.append(f"Dzwonek {index + 1}: {entry} - {status}")

        for i in range(0, len(self.occurrences_list), 2):
            left_label = ctk.CTkLabel(self.main_screen_tabL, text=self.occurrences_list[i])
            left_label.pack(pady=5, padx=10)

            if i + 1 < len(self.occurrences_list):
                right_label = ctk.CTkLabel(self.main_screen_tabR, text=self.occurrences_list[i + 1])
                right_label.pack(pady=5, padx=10)


class frSchedule(ctk.CTkFrame):

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.settingsScheduleIndex = 0
        self.show_constant_fields()

    def show_constant_fields(self):
        sub_frameT = ctk.CTkFrame(self)
        sub_frameT.pack(side="top", fill="x")

        self.lblBellNumber = ctk.CTkLabel(sub_frameT, text="")
        self.lblBellNumber.pack(side="top", padx=5)

        sub_frame_mid = ctk.CTkFrame(self)
        sub_frame_mid.pack(fill="x", pady=10)
        
        sub_frameL = ctk.CTkFrame(sub_frame_mid)
        sub_frameL.pack(side="left", fill="both", expand=True)

        sub_frameLB = ctk.CTkFrame(sub_frameL)
        sub_frameLB.pack(side="bottom",fill="both", expand=True, pady=5)

        ctk.CTkLabel(sub_frameLB, text=f"Czas między dzwonkiem a przeddzwonkiem:").pack(side="top", pady=10)

        intervals = [0.5, 1, 1.5, 2] 
        #for interval in intervals:
         #   self.radio_button = ctk.CTkRadioButton(sub_frameLB, text=interval, value = interval, width=75, radiobutton_height=30, radiobutton_width=30)
          #  self.radio_button.pack(side="left", expand=True, padx=15, pady=5)
            

        sub_frameLl = ctk.CTkFrame(sub_frameL)
        sub_frameLl.pack(side="left", fill="both", expand=True)
        sub_frameLr = ctk.CTkFrame(sub_frameL)
        sub_frameLr.pack(side="right", fill="both", expand=True)   

        self.chbActive = ctk.CTkCheckBox(sub_frameLl, text="Aktywny", checkbox_width=50, checkbox_height=50)
        self.chbActive.pack(side="top", expand=True, pady=5)
        
        ctk.CTkLabel(sub_frameLr, text="Godzina:").pack(side="top", padx=5)
        
        self.spbHour = CTkSpinbox(sub_frameLr, min_value = 0, max_value = 23, step_value = 1, width=160, height=50)
        self.spbHour.pack(side="top", padx=5)

        ctk.CTkLabel(sub_frameLr, text="Minuta:").pack(side="top", padx=5)

        self.spbMinute = CTkSpinbox(sub_frameLr, min_value = 0, max_value = 59, step_value = 1, width=160, height=50)
        self.spbMinute.pack(side="top", padx=5)




        sub_frameR = ctk.CTkFrame(sub_frame_mid)
        sub_frameR.pack(side="right", fill="both", expand=True)      

       # ctk.CTkButton(sub_frameR, text="Dodaj dzwonek", command=add_schedule, width=button_width, height=button_height, font=custom_font).pack(pady=5)
       # ctk.CTkButton(sub_frameR, text="Usuń dzwonek", command=lambda: delete_schedule(bell_index), width=button_width, height=button_height, font=custom_font).pack(pady=5)
       # ctk.CTkButton(sub_frameR, text="Zapisz zmiany", command=lambda: save_changes(), width=button_width, height=button_height, font=custom_font).pack(pady=5)



        sub_frame_low = ctk.CTkFrame(self)
        sub_frame_low.pack(side="top", fill="both")
        
        ctk.CTkButton(sub_frame_low, text="Poprzedni", command=self.prevBell, width=button_width, height=button_height).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(sub_frame_low, text="Następny", command=self.nextBell, width=button_width, height=button_height).pack(side="right", padx=5, pady=5)
        
 

        self.updateScheduleSettings()

    def nextBell(self):
        self.settingsScheduleIndex = self.settingsScheduleIndex+1 if self.settingsScheduleIndex < len(scheduleData.data["bellSchedule"])-1 else 0
        self.updateScheduleSettings()
    def prevBell(self):    
        self.settingsScheduleIndex = self.settingsScheduleIndex-1 if self.settingsScheduleIndex >= 1 else len(scheduleData.data["bellSchedule"])-1
        self.updateScheduleSettings()

    def updateScheduleSettings(self):
        index = self.settingsScheduleIndex
        bellNumber = len(scheduleData.data["bellSchedule"])
        active = scheduleData.data["bellActive"][index]
        hour, minute = map(int, scheduleData.data["bellSchedule"][index].split(":"))
        interval = scheduleData.data["prebellIntervals"][self.settingsScheduleIndex]

        self.lblBellNumber.configure(text="Dzwonek %d z %d:" %(index+1, bellNumber))
        #self.radio_button.configure(variable=interval)
        #self.chbActive.configure(variable = scheduleData.data["bellActive"][index])
        #self.spbMinute.configure(start_value = minute)
        #self.spbHour.configure(start_value = hour)

class frSettings(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        label = ctk.CTkLabel(self, text="To jest dynamicznie settings schedule")
        label.pack(padx=20, pady=20)

class frClock(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        label = ctk.CTkLabel(self, text="To jest dynamicznie clock schedule")
        label.pack(padx=20, pady=20)

class App:
    def __init__(self, root):
        self.root = root
        self.root.geometry("800x480")

        self.topBar()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        

    def topBar(self):
        self.header_frame = ctk.CTkFrame(self.root, height=65)
        self.header_frame.pack(side="top", fill="x", pady=5)

        btnMain = ctk.CTkButton(self.header_frame, text="Ekran główny", height=65, command=self.load_main)
        btnMain.pack(side="left", padx=5, expand=True, fill="both")
        
        btnSchedule = ctk.CTkButton(self.header_frame, text="Harmonogram", height=65, command=self.load_schedule)
        btnSchedule.pack(side="left", padx=5, expand=True, fill="both")
        
        btnSettings = ctk.CTkButton(self.header_frame, text="Ustawienia", height=65, command=self.load_settings)
        btnSettings.pack(side="left", padx=5, expand=True, fill="both", )
        
        btnClock = ctk.CTkButton(self.header_frame, text="Zegar", height=65, command=self.load_clock)
        btnClock.pack(side="left", padx=5, expand=True, fill="both")

        self.frame_area = ctk.CTkFrame(self.root)
        self.frame_area.pack(side="top", fill="both", expand=True,  pady=5)

        self.load_main()
    
    def clear_frame_area(self):
        for widget in self.frame_area.winfo_children():
            widget.destroy()

    def load_main(self):
        self.clear_frame_area()
        frame = frMain(self.frame_area)
        frame.pack(fill="both", expand=True)
    def load_schedule(self):
        self.clear_frame_area()
        frame = frSchedule(self.frame_area)
        frame.pack(fill="both", expand=True)
    def load_settings(self):
        self.clear_frame_area()
        frame = frSettings(self.frame_area)
        frame.pack(fill="both", expand=True)
    def load_clock(self):
        self.clear_frame_area()
        frame = frClock(self.frame_area)
        frame.pack(fill="both", expand=True)


# Uruchamiamy aplikację
root = ctk.CTk()
app = App(root)
root.mainloop()
