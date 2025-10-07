# constante.py
from datetime import time as dt_time

# Créneaux horaires
time_slots = {
    "Petit Déjeuner": {"id_repas": 1, "start": dt_time(0, 0), "end": dt_time(9, 30)},
    "Dejeuner":       {"id_repas": 2, "start": dt_time(10, 0), "end": dt_time(14, 0)},
    "Gouter":         {"id_repas": 3, "start": dt_time(14, 10), "end": dt_time(17, 30)},
    "Diner":          {"id_repas": 4, "start": dt_time(17, 31), "end": dt_time(23, 59)},
}
