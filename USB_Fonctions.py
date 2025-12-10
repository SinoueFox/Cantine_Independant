import sqlite3
from datetime import time, timedelta, datetime
import usb.core
import usb.util
from datetime import datetime, time
import json
import os
import getpass
import subprocess
from datetime import time as dt_time

from escpos.printer import Usb
from openpyxl import Workbook

MOUNT_DIR = "/mnt/usb_cle"

def get_usb_printer():
    # Recherche tous les périphériques USB
    print('GET  USB  PRINTER')
    devices = usb.core.find(find_all=True)
    for dev in devices:
        try:
            # Sauter les root hubs (ID 1d6b:xxxx)
            if dev.idVendor == 0x1d6b:
                continue

            # Sauter si pas de configuration
            if dev.bNumConfigurations < 1:
                continue

            # Vérifier si le périphérique est une imprimante
            cfg = dev.get_active_configuration()
            intf = cfg[(0, 0)]
            if intf.bInterfaceClass != 7:  # 7 = classe imprimante
                continue

            # Libérer l'interface si utilisée par le noyau
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)

            # Configurer le périphérique
            dev.set_configuration()

            # Retourner l'objet imprimante
            print(f"✅ Imprimante détectée : {hex(dev.idVendor)}:{hex(dev.idProduct)}")
            return Usb(dev.idVendor, dev.idProduct, 0)

        except usb.core.USBError as e:
            print(f"Erreur USB : {e}")
        except Exception as e:
            print(f"Erreur avec {hex(dev.idVendor)}:{hex(dev.idProduct)} → {e}")

    print("❌ Aucune imprimante détectée")
    return None
def usb_presente():
    import glob
    # Cherche toutes les partitions de type /dev/sdXN (N = chiffre)
    devices = glob.glob('/dev/sd[a-z][0-9]')
    return len(devices) > 0

def detect_and_check_usb():
    """
    Vérifie si la clé USB est déjà montée au point spécifié.
    Retourne le chemin si la clé est montée et non vide, sinon None.
    NOTE : Cette fonction suppose que le montage est géré par le système
    (via fstab ou udev) et que le script est exécuté avec sudo.
    """
    try:
        # Vérifie si le répertoire est un point de montage et n'est pas vide
        if os.path.ismount(MOUNT_DIR) and os.path.isdir(MOUNT_DIR) and os.listdir(MOUNT_DIR):
            print(f"✅ Clé USB détectée et montée sur {MOUNT_DIR}")
            return MOUNT_DIR
        else:
            print(f"❌ Clé USB non détectée, non montée ou répertoire {MOUNT_DIR} vide.")
            return None
    except Exception as e:
        print(f"Erreur lors de la vérification de la clé USB : {e}")
        return None

def mount_usb_manuellement():
    """
    Tente de démonter et remonter manuellement le premier périphérique USB détecté
    pour s'affranchir d'autofs.
    """
    print("Tentative de montage manuel de la clé USB...")

    # 1. Tenter de désactiver ou démonter les points de montage autofs
    try:
        if is_mounted("/mnt/usb_cle"):
            print("⚠️ Démontage du point de montage autofs pour le remplacer par un montage direct.")
            subprocess.run(["sudo", "umount", "-l", "/mnt/usb_cle"], check=True)  # -l pour un démontage "paresseux"
    except subprocess.CalledProcessError as e:
        print(f"Échec du démontage autofs (peut-être déjà inactif) : {e.stderr.decode()}")
    except Exception as e:
        log_error(f"Erreur inattendue lors du démontage : {e}")

    # 2. Chercher le périphérique USB et le monter manuellement
    devices = glob.glob("/dev/sd[a-z]1")
    if not devices:
        print("⛔ Aucun périphérique USB trouvé (ex: /dev/sda1).")
        return False

    device_to_mount = devices[0]
    print(f"🔍 Périphérique détecté pour montage : {device_to_mount}")

    try:
        os.makedirs("/mnt/usb_cle", exist_ok=True)
        subprocess.run(["sudo", "mount", device_to_mount, "/mnt/usb_cle"], check=True)
        print(f"✅ Clé USB montée avec succès sur /mnt/usb_cle depuis {device_to_mount}")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"❌ Erreur lors du montage manuel de {device_to_mount} : {e.stderr.decode()}")
        print(f"❌ Erreur lors du montage manuel : {e.stderr.decode()}")
        return False
    except Exception as e:
        log_error(f"❌ Erreur inattendue lors du montage manuel : {e}")
        print(f"❌ Erreur inattendue lors du montage manuel : {e}")
        return False

def detect_and_mount_usb():
    """
    Détecte et monte la clé USB sur /mnt/usb_cle.
    Supporte les cas avec ou sans table de partitions.
    """
    mount_dir = "/mnt/usb_cle"
    print("etape 1")
    try:
        print("etape 2")
        output = subprocess.check_output(
            "lsblk -o NAME,TYPE,TRAN,FSTYPE,MOUNTPOINT -nr",
            shell=True
        ).decode()
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de lsblk : {e}")
        return None

    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("disk", "part") and parts[2] == "usb":
            name = parts[0]
            fstype = parts[3] if len(parts) > 3 else ""
            mount_point = parts[4] if len(parts) > 4 else ""

            # On ignore les disques déjà montés
            if mount_point:
                print(f"Clé USB déjà montée sur {mount_point}")
                return mount_point

            # Si c’est un "disk" USB, on regarde s’il a une partition
            if parts[1] == "disk" and os.path.exists(f"/dev/{name}1"):
                device_path = f"/dev/{name}1"
            else:
                device_path = f"/dev/{name}"

            os.makedirs(mount_dir, exist_ok=True)

            try:
                subprocess.check_call(f"mount {device_path} {mount_dir}", shell=True)
                print(f"Clé USB montée sur {mount_dir}")
                return mount_dir
            except subprocess.CalledProcessError as e:
                print(f"Erreur lors du montage de {device_path} : {e}")
                return None

    print("Aucune clé USB détectée.")
    return None

def detect_and_check_usb():
    """
    Vérifie si la clé USB est déjà montée au point spécifié.
    Retourne le chemin si la clé est montée et non vide, sinon None.
    NOTE : Cette fonction suppose que le montage est géré par le système
    (via fstab ou udev) et que le script est exécuté avec sudo.
    """
    try:
        # Vérifie si le répertoire est un point de montage et n'est pas vide
        if os.path.ismount(MOUNT_DIR) and os.path.isdir(MOUNT_DIR) and os.listdir(MOUNT_DIR):
            print(f"✅ Clé USB détectée et montée sur {MOUNT_DIR}")
            return MOUNT_DIR
        else:
            print(f"❌ Clé USB non détectée, non montée ou répertoire {MOUNT_DIR} vide.")
            return None
    except Exception as e:
        print(f"Erreur lors de la vérification de la clé USB : {e}")
        return None

def mount_usb_manuellement():
    """
    Tente de démonter et remonter manuellement le premier périphérique USB détecté
    pour s'affranchir d'autofs.
    """
    print("Tentative de montage manuel de la clé USB...")

    # 1. Tenter de désactiver ou démonter les points de montage autofs
    try:
        if is_mounted("/mnt/usb_cle"):
            print("⚠️ Démontage du point de montage autofs pour le remplacer par un montage direct.")
            subprocess.run(["sudo", "umount", "-l", "/mnt/usb_cle"], check=True)  # -l pour un démontage "paresseux"
    except subprocess.CalledProcessError as e:
        print(f"Échec du démontage autofs (peut-être déjà inactif) : {e.stderr.decode()}")
    except Exception as e:
        log_error(f"Erreur inattendue lors du démontage : {e}")

    # 2. Chercher le périphérique USB et le monter manuellement
    devices = glob.glob("/dev/sd[a-z]1")
    if not devices:
        print("⛔ Aucun périphérique USB trouvé (ex: /dev/sda1).")
        return False

    device_to_mount = devices[0]
    print(f"🔍 Périphérique détecté pour montage : {device_to_mount}")

    try:
        os.makedirs("/mnt/usb_cle", exist_ok=True)
        subprocess.run(["sudo", "mount", device_to_mount, "/mnt/usb_cle"], check=True)
        print(f"✅ Clé USB montée avec succès sur /mnt/usb_cle depuis {device_to_mount}")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"❌ Erreur lors du montage manuel de {device_to_mount} : {e.stderr.decode()}")
        print(f"❌ Erreur lors du montage manuel : {e.stderr.decode()}")
        return False
    except Exception as e:
        log_error(f"❌ Erreur inattendue lors du montage manuel : {e}")
        print(f"❌ Erreur inattendue lors du montage manuel : {e}")
        return False


def is_mounted(path="/mnt/usb_cle"):
    try:
        return subprocess.run(["mountpoint", "-q", path], check=False).returncode == 0
    except Exception:
        return False