import os
import sqlite3
import pandas as pd
from datetime import datetime
from Printer_Function import print_ticket,print_weekly_summary,print_daily_summary3,print_month_summary,print_daily_report_excel_usb
from Constantes import time_slots
from USB_Fonctions import detect_and_mount_usb,mount_usb_manuellement,detect_and_check_usb,usb_presente
from Fonctions_BDD import Ajouter_Utilisateur_SQLITE  # ← à ne pas oublier !
from zk import ZK
from datetime import time as dt_time

CWD = os.path.dirname(os.path.realpath(__file__))
EXCEL_FILENAME = "utilisateurs.xlsx"
ERREUR_FILENAME = "erreur.txt"
POINTEUSE_IP = "192.168.100.201"
POINTEUSE_PORT = 4370
DB_PATH = os.path.join(CWD, "raspberry_data.db")


LOG_PATH = os.path.join(CWD, "errors.log") # <-- AJOUTEZ CETTE LIGNE


def log_error(message):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
         f.write(f"{datetime.now().isoformat()} - {message}\n")

def trouver_fichier_config(nom_fichier="config.json", chemins_base=None):
    if chemins_base is None:
        chemins_base = ["/mnt/usb_cle"]

    for chemin in chemins_base:
        # On vérifie que le dossier existe physiquement
        if not os.path.exists(chemin):
            print(f"⛔ Chemin inexistant : {chemin}")
            continue

        try:
            # Tentative de lister rapidement les fichiers (max 1 niveau)
            fichiers = os.listdir(chemin)
        except Exception as e:
            print(f"⚠️ Erreur d'accès à {chemin} : {e}")
            continue

        print(f"📁 Lecture réussie : {chemin}")
        fichier_config = os.path.join(chemin, nom_fichier)
        if os.path.isfile(fichier_config):
            print(f"✅ Fichier trouvé : {fichier_config}")
            return fichier_config

    print("❌ Aucun fichier config.json trouvé.")
    return None



def charger_time_slots():
    chemin_config = trouver_fichier_config()
    if chemin_config:
        print(f"✅ Fichier de config trouvé : {chemin_config}")
        with open(chemin_config, "r") as f:
            raw_data = json.load(f)

        time_slots = {}
        print("trouve nouveaux time slot")
        for repas, infos in raw_data.items():
            time_slots[repas] = {
                "id_repas": infos["id_repas"],
                "start": dt_time(*map(int, infos["start"].split(":"))),
                "end": dt_time(*map(int, infos["end"].split(":")))
            }
        return time_slots
    else:
        print("⚠️ Aucun fichier de config trouvé. Utilisation des valeurs par défaut.")
        return {
            "Petit Dejeuner": {"id_repas": 1, "start": dt_time(6, 0),  "end": dt_time(9, 30)},
            "Dejeuner":       {"id_repas": 2, "start": dt_time(10, 0), "end": dt_time(14, 0)},
            "Gouter":         {"id_repas": 3, "start": dt_time(14, 10),"end": dt_time(17, 30)},
            "Diner":          {"id_repas": 4, "start": dt_time(17, 31),"end": dt_time(23, 59)},
        }

def process_attendance(att, user_dict, printer):
    """Traite une entrée de pointage"""
    print('Process Attendance ')
    try:
        print('Process Attendance in')
        Usb_Key = usb_presente()
        print (Usb_Key)
        print ("process attendance inin")
        print (att)
        user_id = att.user_id

        print("nom et prenom")
        print(user_dict)
        user_name = user_dict.get(user_id, "").lower()  # On récupère le nom à partir de l’ID
        print (user_name)
        timestamp = att.timestamp
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        jour_annee = timestamp.timetuple().tm_yday
        annee = timestamp.year

        # Traitement rapports
        print("rapport")
        if user_name == "rapport":
            print("📄 Rapport journalier demandé")
            if Usb_Key == True :
             if not detect_and_check_usb():
                print("🔄 Tentative de montage manuel...")
                if mount_usb_manuellement() and detect_and_check_usb():
                    print("✅ Clé USB montée après tentative.")
                else:
                    print("⚠️ Rapport non sauvegardé : clé USB absente.")
            print_daily_summary3(printer)
            return
        if user_name == "rapport3":
            print("📄 Rapport mensuel demandé")
            if Usb_Key == True:
                if not detect_and_check_usb():
                    print("🔄 Tentative de montage manuel...")
                    if mount_usb_manuellement() and detect_and_check_usb():
                        print("✅ Clé USB montée après tentative.")
                    else:
                        print("⚠️ Rapport non sauvegardé : clé USB absente.")
            print_month_summary(printer)
            return
        print("rapport2")
        if user_name == "rapport2":
            print("📄 Rapport hebdomadaire demandé")
            if Usb_Key == True:
                if not detect_and_check_usb():
                    print("🔄 Tentative de montage manuel...")
                    if mount_usb_manuellement() and detect_and_check_usb():
                        print("✅ Clé USB montée après tentative.")
                    else:
                        print("⚠️ Rapport non sauvegardé : clé USB absente.")
            print_weekly_summary(printer)
            return

        # Traitement normal
        print("traitement normal")
        print(timestamp)
        label, slot_id = get_time_slot(timestamp)
        print(slot_id)
        if not slot_id:
            print(f"⏱️ Ignoré (hors créneau) : {timestamp_str}")
            return
        print("traitement normal2")
        exempt = user_name.startswith(("visiteur", "superviseur", "invité"))
        print("avant exempt")
        if exempt:
            slot_label = f"{label} ({user_name})"
            print_ticket(user_dict, att, slot_label, printer, slot_id, timestamp, True)
        else:
            # Vérifier doublon dans la même journée/créneau
            print('verification doublon')
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM Consomation
                    WHERE id_utilisateur = ? AND TYPE_REPAS = ? AND Jour_annee = ? AND Annee_Consomation = ?
                """, (user_id, slot_id, jour_annee, annee))
                (count,) = cursor.fetchone()

        if count > 0:
            print(f"[{timestamp_str}] ID {user_id} a déjà consommé ce créneau → pas de ticket.")
            return

        print_ticket(user_dict, att, label, printer, slot_id, timestamp, False)

    except Exception as e:
            log_error(f"Erreur process_attendance : {e}")


def get_time_slot(ts):
    """Retourne le créneau horaire et son ID"""
    current_time = ts.time()
    for label, slot in time_slots.items():
        if slot["start"] <= current_time <= slot["end"]:
            return label, slot["id_repas"]
    return None, None


def find_excel_file(start_path):
    """Recherche le fichier Excel sur la clé USB montée"""
    for root, dirs, files in os.walk(start_path):
        if EXCEL_FILENAME in files:
            return os.path.join(root, EXCEL_FILENAME)
    return None


def Import_from_Excel():
    """Importe les utilisateurs depuis un fichier Excel et les envoie vers la pointeuse"""
    mount_point = detect_and_mount_usb()
    if not mount_point:
        print("❌ Impossible de détecter ou de monter la clé USB.")
        return

    excel_path = find_excel_file(mount_point)
    if not excel_path:
        print(f"❌ Fichier '{EXCEL_FILENAME}' introuvable sur la clé USB.")
        return

    try:
        df = pd.read_excel(excel_path)
        print(f"✅ Fichier Excel '{excel_path}' lu avec succès.")
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier Excel : {e}")
        return

    print("📥 Importation des utilisateurs depuis Excel...")

    zk = ZK(POINTEUSE_IP, port=POINTEUSE_PORT, timeout=10)
    conn = None
    erreurs = []

    try:
        conn = zk.connect()
        print("✅ Connexion à la pointeuse établie.")
        conn.disable_device()

        existing_users = conn.get_users()
        existing_ids = {str(user.user_id) for user in existing_users}
        print(f"ℹ️ {len(existing_users)} utilisateurs existants récupérés.")
        print(f"IDs existants : {existing_ids}")

        # Parcours du fichier Excel
        for index, row in df.iterrows():
            try:
                user_id = str(row['ID'])
                name = str(row['Nom'])
                print(f"➡️ Traitement utilisateur : ID={user_id}, Nom={name}")

                if user_id in existing_ids:
                    erreurs.append(f"ID {user_id} - {name} : déjà présent\n")
                    print("   ⚠️ Utilisateur déjà présent, ignoré.")
                    continue

                # Ajout dans la pointeuse et dans SQLite
                conn.set_user(uid=int(user_id), name=name)
                print('ajout_excel')
                print(user_id)
                Ajouter_Utilisateur_SQLITE(user_id, name)
                print(f"   ✅ Utilisateur {name} ajouté avec succès.")

            except Exception as e:
                erreurs.append(f"ID {row.get('ID', '?')} - {row.get('Nom', '?')} : erreur {e}\n")
                print(f"   ❌ Erreur lors de l'ajout de l'utilisateur {row.get('Nom', '?')} : {e}")

        # Fin du traitement
        conn.enable_device()
        print("🟢 Pointeuse réactivée.")

        # Écriture du fichier d’erreurs
        if erreurs:
            erreur_file_path = os.path.join(mount_point, ERREUR_FILENAME)
            with open(erreur_file_path, "w", encoding="utf-8") as f:
                f.write("Erreurs lors de l'import des utilisateurs :\n")
                f.writelines(erreurs)
            print(f"⚠️ Erreurs enregistrées dans {erreur_file_path}")
        else:
            print("✅ Aucune erreur rencontrée lors de l'import des utilisateurs.")

    except Exception as e:
        print(f"❌ Erreur de connexion ou d'injection : {e}")

    finally:
        if conn:
            conn.disconnect()
            print("✅ Importation terminée avec succès.")
            return True



