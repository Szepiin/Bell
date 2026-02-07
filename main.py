import platform
import os
from schedule import scheduleHandling
from music import musicHandling
from gui import BellApp
from logging.handlers import RotatingFileHandler
from auth import AuthHandler
from constants import AMP_OUTPUT_PIN_GPIO, USB_PATH_LINUX, USB_PATH_WINDOWS, SCREEN_SAVER_TIME_SECONDS
import logging


log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, "bell.log")

file_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO, 
    handlers=[file_handler, console_handler]
)

# Konfiguracja logowania
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    auth = AuthHandler()
    appGui = BellApp(music=music, schedule=schedule, screensaver_time=SCREEN_SAVER_TIME_SECONDS, auth_handler=auth)

    appGui.mainloop()
    appGui.after(2000, quit_plymouth)
    