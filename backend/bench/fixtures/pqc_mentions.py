# This module will eventually wrap liboqs ML-KEM-768 / ML-DSA-65 once
# Phase 8 lands. For now it's a placeholder with no real crypto calls.


class KeyStore:
    def generate_private_key(self) -> bytes:
        return self._load_from_vault()

    def _load_from_vault(self) -> bytes:
        return b""
