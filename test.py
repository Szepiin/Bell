import customtkinter as ctk

# Tworzymy główne okno
app = ctk.CTk()
app.geometry("600x400")  # Ustaw rozmiar okna

# Główna ramka, na której rozmieszczamy inne ramki
main_frame = ctk.CTkFrame(app)
main_frame.pack(fill="both", expand=True)

# Lewa górna ramka - zajmuje pozostałą przestrzeń w poziomie (X)
left_frame = ctk.CTkFrame(main_frame)
left_frame.pack(side="left", fill="both", expand=True)

# Prawa górna ramka - zajmuje tylko tyle miejsca, ile potrzebują jej elementy
right_frame = ctk.CTkFrame(main_frame)
right_frame.pack(side="right", fill="y")  # Wypełnia przestrzeń tylko w pionie (Y)

# Dolna ramka - rozciąga się na całą szerokość ekranu
bottom_frame = ctk.CTkFrame(main_frame)
bottom_frame.pack(side="bottom", fill="x")

# Uruchomienie aplikacji
app.mainloop()
