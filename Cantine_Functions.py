import os
import sqlite3
import pandas as pd
from datetime import datetime
from flask import render_template, request, flash, redirect
from Printer_Function import print_ticket,print_weekly_summary,print_daily_summary3,print_month_summary,print_daily_report_excel_usb
from config import time_slots
from USB_Fonctions import detect_and_mount_usb,mount_usb_manuellement,detect_and_check_usb,usb_presente
from Fonctions_BDD import Ajouter_CONSOMATEUR_SQLITE  # ← à ne pas oublier !
from zk import ZK
from datetime import time as dt_time
import subprocess
import re
import sqlite3

CWD = os.path.dirname(os.path.realpath(__file__))
EXCEL_FILENAME = "utilisateurs.xlsx"
ERREUR_FILENAME = "erreur.txt"

POINTEUSE_PORT = 4370

DB_FILE = "raspberry_data.db"

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
    import json
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


# def config_ip():
#     if request.method == "POST":
#         ip = request.form["ip"]
#
#         # Validation simple IP
#         if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
#             flash("Adresse IP invalide !", "danger")
#             return redirect("/")
#
#         gateway = extract_gateway(ip)
#
#         try:
#             # Appliquer la nouvelle IP
#             subprocess.run(
#                 ["sudo", "nmcli", "connection", "modify", CONNECTION_NAME, "ipv4.addresses", f"{ip}/{MASK}"],
#                 check=True
#             )
#             # Définir passerelle
#             subprocess.run(
#                 ["sudo", "nmcli", "connection", "modify", CONNECTION_NAME, "ipv4.gateway", gateway],
#                 check=True
#             )
#             # Définir DNS
#             subprocess.run(
#                 ["sudo", "nmcli", "connection", "modify", CONNECTION_NAME, "ipv4.dns", DNS],
#                 check=True
#             )
#             # Forcer méthode statique
#             subprocess.run(
#                 ["sudo", "nmcli", "connection", "modify", CONNECTION_NAME, "ipv4.method", "manual"],
#                 check=True
#             )
#             # Redémarrer la connexion
#             subprocess.run(
#                 ["sudo", "nmcli", "connection", "up", CONNECTION_NAME],
#                 check=True
#             )
#
#             flash(f"Nouvelle IP appliquée : {ip} (passerelle : {gateway})", "success")
#
#         except subprocess.CalledProcessError as e:
#             flash(f"Erreur lors de l'application : {e}", "danger")
#
#         return redirect("/")
#
#     return render_template("config_ip.html")



# Note : Les imports de fonctions externes (usb_presente, detect_and_check_usb,
# mount_usb_manuellement, log_error, get_time_slot, print_ticket, print_daily_summary3, ...)
# sont supposés exister ailleurs dans votre code.

# --- Configuration de la base de données (À SUPPOSER IMPORTÉE) ---
# Nous allons uniformiser le chemin d'accès à la BDD en utilisant la variable DB_FILE
# DB_FILE doit être importé, par exemple : from config import DB_FILE

def check_and_mount_usb():
    """Vérifie la présence et monte la clé USB si nécessaire."""
    if usb_presente():
        if not detect_and_check_usb():
            print("🔄 Tentative de montage manuel...")
            if mount_usb_manuellement() and detect_and_check_usb():
                print("✅ Clé USB montée après tentative.")
                return True
            else:
                print("⚠️ Opération non sauvegardée : clé USB absente ou échec de montage.")
                return False
        return True
    return False


def check_consumption_doublon(conn, user_id, slot_id, jour_annee, annee):
    """Vérifie si l'utilisateur a déjà consommé ce créneau ce jour-là."""
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT COUNT(*)
                   FROM Consomation
                   WHERE id_utilisateur = ?
                     AND TYPE_REPAS = ?
                     AND Jour_annee = ?
                     AND Annee_Consomation = ?
                   """, (user_id, slot_id, jour_annee, annee))
    (count,) = cursor.fetchone()
    return count > 0


def process_attendance_v2(att, user_dict, printer, nom_societe, Mode_Fonctionnement):
    """Traite une entrée de pointage (Version optimisée et robuste)"""
    from config import MODE_TICK_SANS_DOUBLON
    print('Process Attendance V2')
    user_id = att.user_id

    try:
        user_name = user_dict.get(user_id, "").lower()
        timestamp = att.timestamp
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        jour_annee = timestamp.timetuple().tm_yday
        print('jour_annee =', str(jour_annee))
        annee = timestamp.year

        # --- 1. Traitement des commandes de Rapport (Basé sur le nom d'utilisateur) ---
        # Note: Ceci est maintenu mais la recommandation est d'utiliser un mécanisme plus sûr.
        if user_name.startswith("rapport"):
            usb_ok = check_and_mount_usb()  # Utilisation de la fonction factorisée

            if user_name == "rapport":
                print("📄 Rapport journalier demandé")
                print_daily_summary3(printer, usb_ok)
            elif user_name == "rapport2":
                print("📄 Rapport hebdomadaire demandé")
                print_weekly_summary(printer, usb_ok)
            elif user_name == "rapport3":
                print("📄 Rapport mensuel demandé")
                print_month_summary(printer, usb_ok)
            return

        # --- 2. Vérification du Créneau Horaire ---
        label, slot_id = get_time_slot(timestamp)

        if not slot_id:
            print(f"⏱️ Ignoré (hors créneau) : {timestamp_str}")
            return

        # --- 3. Récupération des Données Utilisateur (Utilisation de l'accès sécurisé BDD) ---
        with sqlite3.connect(DB_FILE) as conn:
            # Optionnel : Activer les lignes comme des dictionnaires pour un accès plus propre (ex: user_data['exemption'])
            # conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            print('Boucle identification consomateur' + DB_FILE)

            # Utilisation d'une requête SELECT spécifique pour la lisibilité
            cur.execute("""
                        SELECT Abonnement_Actif, Multi_Repas, Nombre_Tickets, Code_Employe
                        FROM Consomateurs
                        WHERE Code_Employe = ?
                        """, (user_id,))
            user_data = cur.fetchone()

            if not user_data:
                print(f"❌ Utilisateur ID {user_id} non trouvé dans la base Consomateurs.")
                return

            Abonnement_Actif, Multi_Repas, Nbr_Tickets, Code_Employe = user_data
            print('Code_employe = ' + str(Code_Employe))
        # --- 4. Traitement selon le Mode de Fonctionnement ---

        # Mode Exemption (Mode_S_AB_Tick uniquement pour les exemptés)
        print('Multi repas = ' + str(Multi_Repas))
        print('Mode_Fonctionnement = ' + Mode_Fonctionnement)
        if Mode_Fonctionnement == 'Mode_S_AB_Tick' and Multi_Repas == 1:
            slot_label = f"{label} (Exempté)"
            print_ticket(user_dict, att, slot_id, label, printer,jour_annee,annee, timestamp,  nom_societe)


            return

        # Modes basés sur la Consommation (Abonnement ou Mode_S_AB_Tick sans exemption)
        if Mode_Fonctionnement in ['Mode_Abonnement', 'Mode_S_AB_Tick']:

            is_allowed = False

            if Mode_Fonctionnement == 'Mode_Abonnement' and Abonnement_Actif == 1:
                is_allowed = True

            # S'applique aux non-exemptés de Mode_S_AB_Tick
            if Mode_Fonctionnement == 'Mode_S_AB_Tick' and Multi_Repas != 1:
                is_allowed = True

            if is_allowed:
                with sqlite3.connect(DB_FILE) as conn:  # Réutilisation de la connexion sécurisée
                    print('user = ' + str(user_id) + ' slot_id = ' + str(slot_id) + ' jour_annee = ' + str(jour_annee) + ' annee = ' + str(annee))
                    if check_consumption_doublon(conn, user_id, slot_id, jour_annee, annee):
                        print(f"[{timestamp_str}] ID {user_id} a déjà consommé ce créneau → pas de ticket.")
                    else:
                        print_ticket(user_dict, att, slot_id,label,printer, jour_annee,annee,  timestamp, nom_societe)

            return  # Fin du traitement pour ces modes

        # Mode Tickets
        if Mode_Fonctionnement == 'Mode_Ticket':
            print('Nombre Tickets = ' + str(Nbr_Tickets))


            if Nbr_Tickets > 0:
                # Mise à jour de la BDD
                try:
                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE Consomateurs SET Nombre_Tickets = ? WHERE Code_Employe = ?",
                            (Nbr_Tickets - 1, Code_Employe))
                        conn.commit()
                        if MODE_TICK_SANS_DOUBLON != 0 :
                            if check_consumption_doublon(conn, user_id, slot_id, jour_annee, annee):
                                print(f"[{timestamp_str}] ID {user_id} a déjà consommé ce créneau → pas de ticket.")
                            else:
                                print_ticket(user_dict, att, slot_id, label, printer, jour_annee, annee, timestamp,nom_societe)


                except sqlite3.Error as e:
                    log_error(f"Erreur DB lors de la décrémentation des tickets pour ID {user_id}: {e}")
            else:
                print(f"[{timestamp_str}] ID {user_id} n'a plus de tickets.")
            return

    except AttributeError as e:
        # Ex: si att ou user_dict n'a pas l'attribut attendu
        log_error(f"Erreur d'attribut lors du traitement de {user_id}: {e}")
    except sqlite3.Error as e:
        # Erreurs spécifiques à la base de données (ex: table Consomateurs non trouvée)
        log_error(f"Erreur de base de données pour ID {user_id}: {e}")
    except Exception as e:
        # Toute autre erreur inattendue
        log_error(f"Erreur inattendue process_attendance pour ID {user_id}: {e}")
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