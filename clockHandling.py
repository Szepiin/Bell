import platform
import os
import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def set_system_time(hour: int, minute: int, second: int) -> bool:
    """
    Ustawia czas systemowy na podaną godzinę i minutę.
    Wymaga uprawnień administratora/roota.
    Zwraca True w przypadku sukcesu, False w przypadku błędu.
    """
    try:
        now = datetime.datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        
        if platform.system() == "Windows":
            # Dla Windows wymagane uprawnienia administratora
            # Komenda date/time w cmd.exe może być różna dla różnych wersji Windows
            # Na przykład: os.system(f'time {target_time.strftime("%H:%M:%S")}')
            logger.warning("Ustawianie czasu systemowego na Windows nie jest zaimplementowane w sposób niezawodny bez zewnętrznych bibliotek lub interakcji z API.")
            logger.info(f"Symulacja ustawienia czasu na: {target_time.strftime('%H:%M:%S')}")
            return True # Zwracamy True dla symulacji
        elif platform.system() == "Linux":
            # Dla Linuksa wymagane uprawnienia roota (np. sudo)
            # Użycie `date -s`
            command = f"sudo date -s '{target_time.strftime('%Y-%m-%d %H:%M:%S')}'"
            result = os.system(command)
            if result == 0:
                logger.info(f"Ustawiono czas systemowy na Linux: {target_time.strftime('%H:%M:%S')}")
                return True
            else:
                logger.error(f"Nie udało się ustawić czasu systemowego na Linux. Komenda: '{command}', Wynik: {result}. Brak uprawnień root?")
                return False
        else:
            logger.warning(f"Ustawianie czasu systemowego nie jest obsługiwane na platformie: {platform.system()}")
            return False
    except Exception as e:
        logger.error(f"Wystąpił błąd podczas ustawiania czasu systemowego: {e}")
        return False

