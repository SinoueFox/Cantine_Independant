import RPi.GPIO as GPIO
from time import time, sleep
import threading

GPIO.setwarnings(False)
GPIO.cleanup()
def read_wiegand(d0_pin, d1_pin, timeout=0.5, inactivity_threshold=0.05, pull_up_down=None):
    """
    Lit une trame Wiegand sur les broches d0_pin (D0) et d1_pin (D1).
    - timeout : durée maximale (en secondes) pour attendre le début d'une trame (None = infini)
    - inactivity_threshold : délai (s) sans nouveaux bits pour considérer la trame terminée
    - pull_up_down : None (pas de pull), GPIO.PUD_UP ou GPIO.PUD_DOWN si souhaité

    Retour :
      - None si aucun bit reçu (timeout)
      - (facility, card, bits_str) si trame 26 bits
      - (value_decimal, bits_str) si autre longueur
    """
    # Préparation GPIO (on ne fait pas cleanup global ici pour laisser d'autres pins si besoin)
    GPIO.setmode(GPIO.BCM)
    if pull_up_down is None:
        GPIO.setup(d0_pin, GPIO.IN)
        GPIO.setup(d1_pin, GPIO.IN)
    else:
        GPIO.setup(d0_pin, GPIO.IN, pull_up_down=pull_up_down)
        GPIO.setup(d1_pin, GPIO.IN, pull_up_down=pull_up_down)

    bits = []
    last_time = [time()]  # liste pour être mutable dans closure
    got_any_bit = threading.Event()

    def cb_d0(channel):
        bits.append('0')
        last_time[0] = time()
        got_any_bit.set()

    def cb_d1(channel):
        bits.append('1')
        last_time[0] = time()
        got_any_bit.set()

    # Enregistrement callbacks
    GPIO.add_event_detect(d0_pin, GPIO.FALLING, callback=cb_d0, bouncetime=1)
    GPIO.add_event_detect(d1_pin, GPIO.FALLING, callback=cb_d1, bouncetime=1)

    start_wait = time()
    try:
        # attente du début de trame (premier bit) jusqu'au timeout
        if timeout is not None:
            remaining = timeout - (time() - start_wait)
            if remaining <= 0:
                # timeout direct
                return None
        # Bloque ici jusqu'au premier bit ou timeout
        if not got_any_bit.wait(timeout):
            # aucun bit reçu
            return None

        # Dès que premier bit reçu, on attend la fin de la trame décrétée par inactivity_threshold
        while True:
            sleep(0.005)
            if time() - last_time[0] > inactivity_threshold:
                break

        bits_str = "".join(bits)
        length = len(bits_str)
        if length == 0:
            return None

        # décodage 26 bits (format classique)
        if length == 26:
            # bits_str[0] = parité, [1:9] facility, [9:25] card, [25] = parité
            try:
                facility = int(bits_str[1:9], 2)
                card = int(bits_str[9:25], 2)
                return (facility, card, bits_str)
            except ValueError:
                return (int(bits_str, 2), bits_str)
        else:
            # retourne la valeur décimale brute + la chaîne de bits
            try:
                val = int(bits_str, 2)
                return (val, bits_str)
            except ValueError:
                return (bits_str,)  # chaîne brute si conversion impossible

    finally:
        # retirer les event_detect pour éviter doublons si la fonction est rappelée
        try:
            GPIO.remove_event_detect(d0_pin)
        except Exception:
            pass
        try:
            GPIO.remove_event_detect(d1_pin)
        except Exception:
            pass
        # ne pas faire GPIO.cleanup() ici si tu gères d'autres broches ailleurs

def wiegand_listener(gpio1, gpio2):
    while True:
        result = read_wiegand(gpio1, gpio2, timeout=1.0, inactivity_threshold=0.05)
        if result is None:
            continue  # pas de carte, on attend encore
        elif len(result) == 3:
            facility, card, bits = result
            print(f"26 bits → Facility: {facility}, Card: {card} (bits={bits})")
            # ici tu appelles process_attendance(...) comme avec la ZK
        else:
            val, bits = result
            print(f"Trame non-26 → valeur: {val} (bits={bits})")
            # ici pareil, traiter la carte
