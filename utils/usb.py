import time
from config import USB_CHECK_INTERVAL

def monitor_usb(detect_and_mount_usb, usb_presente):
    etat_precedent = None
    while True:
        try:
            present = usb_presente()
            if present and not etat_precedent:
                print("🔌 Clé USB détectée → montage...")
                detect_and_mount_usb()
            elif not present and etat_precedent:
                print("❌ Clé USB retirée.")
            etat_precedent = present
        except Exception as e:
            print(f"⚠️ Erreur USB : {e}")
        time.sleep(USB_CHECK_INTERVAL)
