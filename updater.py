import os
import zipfile
import platform
import subprocess
import logging
from constants import USB_PATH_LINUX, USB_PATH_WINDOWS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def find_update_zip(base_usb_path):
    """
    Skanuje podane ścieżki (i podkatalogi) w poszukiwaniu pliku zip
    zaczynającego się od 'update' (np. update111.zip).
    """
    if not os.path.exists(base_usb_path):
        logger.warning(f"Ścieżka USB nie istnieje: {base_usb_path}")
        return None
        
    for root, dirs, files in os.walk(base_usb_path):
        for file in files:
            if file.lower().startswith("update") and file.lower().endswith(".zip"):
                return os.path.join(root, file)
    return None

def apply_update(app_dir, popup_callback):
    """
    Główna funkcja aktualizująca aplikację z pendrive'a.
    app_dir: ścieżka do katalogu, w którym działa main.py
    popup_callback: funkcja wyświetlająca powiadomienia (NotificationPopup)
    """
    is_linux = platform.system() == "Linux"
    base_usb_path = USB_PATH_LINUX if is_linux else USB_PATH_WINDOWS
    
    update_file = find_update_zip(base_usb_path)
    
    if not update_file:
        logger.info("Nie znaleziono pliku aktualizacji na dysku USB.")
        popup_callback("Brak pliku do aktualizacji na USB", "orange")
        return False
        
    try:
        popup_callback("Znaleziono aktualizację!\nRozpakowywanie plików...", "white")
        logger.info(f"Rozpoczynam aktualizację z pliku: {update_file}")
        
        # 1. Rozpakowanie i nadpisanie plików na naszej partycji RW
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            zip_ref.extractall(app_dir)
            
        logger.info("Pliki zostały pomyślnie nadpisane.")
        
        # 2. Zmiana nazwy pliku na pendrive, aby uniknąć pętli aktualizacji (restart, update, restart...)
        done_filename = update_file + ".zrobione"
        try:
            os.rename(update_file, done_filename)
            logger.info(f"Zmieniono nazwę pliku na: {done_filename}")
        except Exception as rename_err:
            logger.warning(f"Nie udało się zmienić nazwy pliku na pendrive (może pendrive jest tylko do odczytu?): {rename_err}")
            # Nadal kontynuujemy, to tylko ostrzeżenie. Aplikacja się zrestartuje, 
            # ale jeśli użytkownik nie wyciągnie pendrive'a, przy kolejnym kliknięciu znów wgra aktualizację.
        
        # 3. Restart urządzenia
        if is_linux:
            popup_callback("Aktualizacja zakończona.\nRestartowanie urządzenia...", "green")
            # Dajemy systemowi 2 sekundy, aby GUI zdążyło wyrenderować powiadomienie
            # Z racji, że masz autologowanie root, 'reboot' przejdzie bez pytania o hasło
            subprocess.Popen("sleep 2 && reboot", shell=True) 
        else:
            popup_callback("Aktualizacja zakończona.\nUruchom program ponownie ręcznie.", "green")
        
        return True
        
    except Exception as e:
        logger.error(f"Krytyczny błąd podczas aktualizacji: {e}")
        popup_callback(f"Błąd aktualizacji!\n{e}", "red")
        return False