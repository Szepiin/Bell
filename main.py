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

def quit_plymouth():
    os.system("sudo plymouth quit")


def get_base_path():
    """Zwraca ścieżkę bazową dla plików w zależności od systemu operacyjnego."""
    if platform.machine() == "AMD64":
        return USB_PATH_WINDOWS
    else:
        return USB_PATH_LINUX
    

if __name__ == "__main__":
    base_path = get_base_path()

    schedule = scheduleHandling()
    music = musicHandling(base_path, AMP_OUTPUT_PIN_GPIO)
    
    appGui = BellApp(music=music, schedule=schedule, screensaver_time=SCREEN_SAVER_TIME_SECONDS)

    appGui.mainloop()
    appGui.after(2000, quit_plymouth)
    