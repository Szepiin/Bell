import platform
import os
from schedule import scheduleHandling
from music import musicHandling
from gui import BellApp
from constants import AMP_OUTPUT_PIN_GPIO, USB_PATH_LINUX, USB_PATH_WINDOWS, SCREEN_SAVER_TIME_SECONDS
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ustawienie zmiennej DISPLAY (może wymagać dostosowania do środowiska)
os.environ['DISPLAY'] = ':0'

def get_base_path():
    """Zwraca ścieżkę bazową dla plików w zależności od systemu operacyjnego."""
    if platform.machine() == "AMD64":
        return USB_PATH_WINDOWS
    else:
        # Można dodać bardziej zaawansowane wykrywanie ścieżki USB na Linuksie
        return USB_PATH_LINUX

if __name__ == "__main__":
    base_path = get_base_path()
    sound_files_path = os.path.join(base_path, "Files") # Zakładamy podkatalog Files dla dźwięków

    schedule = scheduleHandling()
    music = musicHandling(sound_files_path, AMP_OUTPUT_PIN_GPIO)
    
    appGui = BellApp(music=music, schedule=schedule, screensaver_time=SCREEN_SAVER_TIME_SECONDS)
    appGui.mainloop()