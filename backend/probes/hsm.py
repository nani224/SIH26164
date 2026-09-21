"""SoftHSM2 and PKCS#11 hardware security module inventory probe.

Enumerates cryptographic slots, tokens, and keys (RSA, ECC, AES, PQC)
stored within a PKCS#11 token provider.
"""

from __future__ import annotations

import logging
import os

from api.models import HsmInventory, HsmKey, HsmSlot

logger = logging.getLogger(__name__)

# Common default paths for SoftHSM2 shared library
DEFAULT_SOFTHSM_PATHS = (
    os.environ.get("SOFTHSM2_LIB"),
    r"C:\SoftHSM2\lib\softhsm2-x64.dll",
    r"C:\SoftHSM2\lib\softhsm2.dll",
    r"C:\Program Files\SoftHSM2\lib\softhsm2.dll",
    "/usr/lib/softhsm/libsofthsm2.so",
    "/usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so",
    "/usr/local/lib/softhsm/libsofthsm2.so",
)


def _resolve_softhsm_lib() -> str | None:
    for path in DEFAULT_SOFTHSM_PATHS:
        if path and os.path.isfile(path):
            return path
    return None


def get_hsm_inventory(lib_path: str | None = None, pin: str | None = None) -> HsmInventory:
    """Enumerate slots, tokens, and cryptographic keys from a PKCS#11 provider.

    Args:
        lib_path: Optional explicit path to SoftHSM2 or PKCS#11 library.
        pin: Optional User PIN for authenticated key inspection.

    Returns:
        HsmInventory containing discovered slots and keys.
    """
    if not os.environ.get("SOFTHSM2_CONF") and os.path.isfile(r"C:\SoftHSM2\etc\softhsm2.conf"):
        os.environ["SOFTHSM2_CONF"] = r"C:\SoftHSM2\etc\softhsm2.conf"

    resolved_path = lib_path or _resolve_softhsm_lib()
    user_pin = pin or os.environ.get("SOFTHSM2_PIN", "1234")

    slots: list[HsmSlot] = []

    if not resolved_path:
        logger.info("SoftHSM2 PKCS#11 library not detected on host filesystem; returning empty inventory.")
        return HsmInventory(slots=[])

    try:
        import pkcs11
        from pkcs11 import Attribute, KeyType, ObjectClass

        lib = pkcs11.lib(resolved_path)

        for slot in lib.get_slots(token_present=True):
            slot_id = int(getattr(slot, "slot_id", 0))
            keys: list[HsmKey] = []
            token_label = f"Slot-{slot_id}"

            try:
                token = slot.get_token()
                token_label = getattr(token, "label", token_label).strip()

                # Open read-only session on token
                with token.open(user_pin=user_pin) as session:
                    for obj in session.get_objects({Attribute.CLASS: ObjectClass.PUBLIC_KEY}):
                        try:
                            key_type_val = obj[Attribute.KEY_TYPE]
                        except Exception:
                            key_type_val = None

                        type_str = "UNKNOWN"
                        if key_type_val == KeyType.RSA:
                            type_str = "RSA"
                        elif key_type_val == KeyType.EC:
                            type_str = "EC"
                        elif key_type_val == KeyType.DSA:
                            type_str = "DSA"

                        try:
                            label = str(obj[Attribute.LABEL])
                        except Exception:
                            label = "unlabeled"

                        try:
                            size = int(obj[Attribute.MODULUS_BITS] or 0)
                        except Exception:
                            size = 0

                        keys.append(HsmKey(type=type_str, size=size, label=label))
            except Exception as sess_err:
                logger.warning("Could not inspect token for slot %d: %s", slot_id, sess_err)

            slots.append(HsmSlot(slot=slot_id, label=token_label, keys=keys))

    except Exception as exc:
        logger.warning("PKCS#11 inspection encountered an error: %s", exc)

    return HsmInventory(slots=slots)
