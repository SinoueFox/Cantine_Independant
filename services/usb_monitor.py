# services/usb_monitor.py
import time
from USB_Fonctions import detect_and_mount_usb, usb_presente
from utils.logger import log_error

def monitor_usb_loop(stop_event=None, check_interval=5):
    prev_state = None
    while True:
        try:
            present = usb_presente()
            if present and not prev_state:
                log_error.info("Clé USB détectée → tentative de montage...")
                detect_and_mount_usb()
            elif not present and prev_state:
                log_error.warning("Clé USB retirée.")
            prev_state = present
        except Exception as e:
            log_error.exception("Erreur dans monitor_usb_loop: %s", e)
        time.sleep(check_interval)
