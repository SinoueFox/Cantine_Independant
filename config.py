import os
from datetime import time as dt_time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BORNE = 1
# Base de données SQLite
DB_FILE = os.path.join(BASE_DIR,"raspberry_data.db")

# Pointeuse
POINTEUSE_IP = "192.168.100.201"
POINTEUSE_PORT = 4370

# Imprimante
PRINTER_USB_NAME = "USB_Printer"

# Logs
LOG_PATH = os.path.join(BASE_DIR, "errors.log")

# USB
USB_CHECK_INTERVAL = 5  # en secondes

# GPIO (Raspberry Pi)
GPIO_TOURNIQUET = 12
GPIO1 = 5
GPIO2 = 4

# Mode de fonctionnement
MODE_TICKET = 0
MODE_ABONNEMENT = 0
MODE_S_AB_TICK = 1
MODE_AB_TICK = 0

MODE_TICK_SANS_DOUBLON = 0

Nom_Societe = "Cantine 001"

time_slots = {
    "Petit Déjeuner": {"id_repas": 1, "start": dt_time(0, 0), "end": dt_time(9, 59)},
    "Dejeuner":       {"id_repas": 2, "start": dt_time(10, 0), "end": dt_time(14, 0)},
    "Gouter":         {"id_repas": 3, "start": dt_time(14, 10), "end": dt_time(17, 30)},
    "Diner":          {"id_repas": 4, "start": dt_time(17, 31), "end": dt_time(23, 59)},
}