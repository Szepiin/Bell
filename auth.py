# auth.py
import hashlib
import json
import os
import logging

from constants import AUTH_PATH_LINUX

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AuthHandler:
    def __init__(self):
        self.DEFAULT_PIN_HASH = "bf7b7fa5bc0225c07be0e76ff88b0c690a17cad85535d7613d7813de2c88dcee"
        self.auth_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), AUTH_PATH_LINUX)
        self.user_pin_hash = None
        self._load_user_pin()

    def _hash_pin(self, pin):
        """Tworzy hash SHA-256 dla podanego PIN-u."""
        return hashlib.sha256(str(pin).encode('utf-8')).hexdigest()

    def _load_user_pin(self):
        """Ładuje hash PIN-u użytkownika z pliku JSON."""
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, 'r') as f:
                    data = json.load(f)
                    self.user_pin_hash = data.get("user_pin_hash")
            except Exception as e:
                logger.error(f"Błąd ładowania pliku autoryzacji: {e}")

    def check_pin(self, input_pin):
        """
        Sprawdza, czy podany PIN pasuje do domyślnego LUB użytkownika.
        Zwraca True, jeśli pasuje.
        """
        input_hash = self._hash_pin(input_pin)
        
        # Sprawdź hasło domyślne
        if input_hash == self.DEFAULT_PIN_HASH:
            return True
        
        # Sprawdź hasło użytkownika (jeśli ustawione)
        if self.user_pin_hash and input_hash == self.user_pin_hash:
            return True
            
        return False

    def set_user_pin(self, new_pin):
        """Ustawia nowe hasło użytkownika i zapisuje do pliku."""
        new_hash = self._hash_pin(new_pin)
        self.user_pin_hash = new_hash
        
        data = {"user_pin_hash": new_hash}
        try:
            # Upewnij się, że katalog Files istnieje
            os.makedirs(os.path.dirname(self.auth_file), exist_ok=True)
            with open(self.auth_file, 'w') as f:
                json.dump(data, f)
            logger.info("Zmieniono PIN użytkownika.")
            return True
        except Exception as e:
            logger.error(f"Błąd zapisu PIN-u: {e}")
            return False