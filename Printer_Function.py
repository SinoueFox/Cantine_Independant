import usb.core
import usb.util
import os
import sqlite3
from escpos.printer import Usb
from datetime import datetime,time as dt_time,timedelta
from USB_Fonctions import detect_and_mount_usb,mount_usb_manuellement,detect_and_check_usb,usb_presente
from Fonctions_BDD import Ajouter_Consomation_SQLITE
from openpyxl import Workbook


# Créneaux horaires
time_slots = {
     "Petit Dejeuner": {"id_repas": 1, "start": dt_time(0, 0), "end": dt_time(9, 30)},
     "Dejeuner":       {"id_repas": 2, "start": dt_time(10, 0), "end": dt_time(14, 0)},
     "Gouter":         {"id_repas": 3, "start": dt_time(14, 10), "end": dt_time(17, 30)},
     "Diner":          {"id_repas": 4, "start": dt_time(17, 31), "end": dt_time(23, 59)},
       }
CWD = os.path.dirname(os.path.realpath(__file__))
MOUNT_DIR = "/mnt/usb_cle"
DB_PATH = os.path.join(CWD, "raspberry_data.db")

def get_time_slot(ts):
    """Retourne le créneau horaire et son ID"""
    current_time = ts.time()
    for label, slot in time_slots.items():
        if slot["start"] <= current_time <= slot["end"]:
            return label, slot["id_repas"]
    return None, None

def log_error(message):
    import os
    CWD = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(CWD, "errors.log") , "a", encoding="utf-8") as f:
         f.write(f"{datetime.now().isoformat()} - {message}\n")

def print_daily_summary3(p):
    try:
        print("Indice : début impression du résumé journalier")
        conn = sqlite3.connect("raspberry_data.db")
        cursor = conn.cursor()
        print("indice 2")
        date_jour = datetime.now().date()
        start_of_day = datetime.combine(date_jour, dt_time(0, 0))
        end_of_day = datetime.combine(date_jour, dt_time(23, 59, 59))
        print("indice 3")
        cursor.execute("""
            SELECT TYPE_REPAS_STR, COUNT(*) 
            FROM Consomation
            WHERE Date_Consomation BETWEEN ? AND ?
            GROUP BY TYPE_REPAS_STR
        """, (
            start_of_day.strftime("%Y-%m-%d %H:%M:%S"),
            end_of_day.strftime("%Y-%m-%d %H:%M:%S")
        ))

        results = cursor.fetchall()
        print("indice 4")
        # Initialisation
        total_tickets = 0

        # Impression de l'en-tête
        p.set(align='center', bold=True, double_height=True)
        p.text("CANTINE\n")
        p.set(align='center', bold=False, double_height=False)
        p.text(f"Resume du {date_jour.strftime('%d/%m/%Y')}\n")
        p.text("------------------------------\n")

        # Impression des lignes de repas
        p.set(align='left', bold=False)
        for type_repas_str, count in results:
            # Alignement à gauche + droite
            line = f"{type_repas_str:<30}{count:>5}\n"
            p.text(line)
            total_tickets += count

        p.text("------------------------------\n")
        p.set(bold=True)
        p.text(f"{'TOTAL':<20}{total_tickets:>5}\n")
        print("indice 5")
        #  Ecriture fichier excel
        if usb_presente():
            mount_point = detect_and_check_usb()
            if mount_point:  # Si la clé est montée et valide...
                print_daily_report_excel_usb(1, mount_point)
                p.text("\n")
                p.set(align='center')
                p.text("Rapport copié sur clé USB !\n")
            else:
                print("⚠️ Rapport non sauvegardé : clé USB absente ou non montée.")
        conn.close()
        p.cut()
    except Exception as e:
        log_error(f"Erreur lors de l'impression du résumé journalier : {e}")

def get_usb_printer():
    """
    Recherche et initialise automatiquement une imprimante ESC/POS USB.
    """
    devices = usb.core.find(find_all=True)
    for dev in devices:
        try:
            # Détacher le pilote kernel si actif
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)

            # Test de communication ESC/POS
            printer = Usb(dev.idVendor, dev.idProduct, 0)
            printer._raw(b'\x10\x04\x14')  # interrogation de statut ESC/POS
            print(f"✅ Imprimante détectée : {dev.idVendor:04x}:{dev.idProduct:04x}")
            return printer

        except Exception:
            continue  # Essayer le périphérique suivant

    return None

def print_month_summary(p):
    try:
        conn = sqlite3.connect("raspberry_data.db")  # Connexion SQLite
        cursor = conn.cursor()

        # Date/heure début du mois et maintenant
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()  # Garde l'heure courante

        # Debug
        print(f"Début du mois : {start_of_month.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Maintenant    : {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Requête SQL avec heure exacte
        cursor.execute("""
                       SELECT date (Date_Consomation) AS day, TYPE_REPAS_STR, TYPE_REPAS, COUNT (*)
                       FROM Consomation
                       WHERE Date_Consomation BETWEEN ? AND ?
                       GROUP BY day, TYPE_REPAS
                       ORDER BY day, TYPE_REPAS
                       """, (start_of_month.strftime('%Y-%m-%d %H:%M:%S'),
                             now.strftime("%Y-%m-%d %H:%M:%S")))

        results = cursor.fetchall()

        # Impression en-tête
        p.set(align='center', bold=True, double_height=True)
        p.text("RECAPITULATIF MENSUEL\n")
        p.set(align='left', bold=False, double_height=False)
        p.text(f"Periode: {start_of_month.strftime('%d/%m/%Y')} au {now.strftime('%d/%m/%Y %H:%M')}\n")
        p.text("=" * 32 + "\n")

        current_day = None
        total_month = 0

        for day, TYPE_REPAS_STR, type_repas, count in results:
            if day != current_day:
                if current_day is not None:
                    p.text("-" * 32 + "\n")
                current_day = day
                p.text(f"{datetime.strptime(day, '%Y-%m-%d').strftime('%A %d/%m')}:\n")

            p.text(f"  {TYPE_REPAS_STR:<20}{count:>10}\n")
            total_month += count

        p.text("=" * 32 + "\n")
        p.text(f"Total mois: {total_month}\n")

        #  Ecriture fichier excel
        if usb_presente():
            mount_point = detect_and_check_usb()
            if mount_point:  # Si la clé est montée et valide...
                print_daily_report_excel_usb(3, mount_point)
                p.text("\n")
                p.set(align='center')
                p.text("Rapport copié sur clé USB !\n")
            else:
                print("⚠️ Rapport non sauvegardé : clé USB absente ou non montée.")
        conn.close()
        p.cut()
    except Exception as e:
        log_error(f"Erreur lors de l'impression du résumé journalier : {e}")
        p.cut()
        conn.close()

    except Exception as e:
        log_error(f"Erreur lors de l'impression du résumé mensuel : {e}")

        def print_weekly_summary(p):
            try:
                conn = sqlite3.connect("raspberry_data.db")  # Utilisez DB_FILE pour SQLite
                cursor = conn.cursor()

                today = datetime.now().date()
                sunday = today - timedelta(days=today.weekday() + 1)
                start_of_week = datetime.combine(sunday, time(0, 0))
                end_of_week = datetime.combine(today, time(23, 59, 59))
                cursor.execute("""
                               SELECT date (Date_Consomation) as day, TYPE_REPAS_STR, TYPE_REPAS, COUNT (*)
                               FROM Consomation
                               WHERE Date_Consomation BETWEEN ? AND ?
                               GROUP BY day, TYPE_REPAS
                               ORDER BY day, TYPE_REPAS
                               """, (start_of_week.strftime("%Y-%m-%d %H:%M:%S"),
                                     end_of_week.strftime("%Y-%m-%d %H:%M:%S")))
                results = cursor.fetchall()

                p.set(align='center', bold=True, double_height=True)
                p.text("RECAPITULATIF HEBDOMADAIRE\n")
                p.set(align='left', bold=False, double_height=False)

                p.text(f"Periode: {start_of_week.strftime('%d/%m/%Y')} au {end_of_week.strftime('%d/%m/%Y')}\n")
                p.text("=" * 32 + "\n")

                current_day = None
                total_week = 0

                for day, TYPE_REPAS_STR, type_repas, count in results:
                    if day != current_day:
                        if current_day is not None:
                            p.text("-" * 32 + "\n")
                        current_day = day
                        p.text(f"{datetime.strptime(day, '%Y-%m-%d').strftime('%A %d/%m')}:\n")

                    p.text(f"  {TYPE_REPAS_STR:<20}{count:>10}\n")
                    total_week += count

                p.text("=" * 32 + "\n")
                p.text(f"Total semaine: {total_week}\n")
                #  Ecriture fichier excel
                if usb_presente():
                    mount_point = detect_and_check_usb()
                    if mount_point:  # Si la clé est montée et valide...
                        print_daily_report_excel_usb(2, mount_point)
                        p.text("\n")
                        p.set(align='center')
                        p.text("Rapport copié sur clé USB !\n")
                    else:
                        print("⚠️ Rapport non sauvegardé : clé USB absente ou non montée.")
                conn.close()
                p.cut()
            except Exception as e:
                log_error(f"Erreur lors de l'impression du résumé journalier : {e}")



            except Exception as e:
                log_error(f"Erreur lors de l'impression du résumé hebdomadaire : {e}")

def print_ticket(user_dict, att, slot_label, printer, type_repas, time_conso, exempt):
    """Imprime un ticket de consommation"""
    print('impression de ticket')
    try:
        user_id = att.user_id
        user_name = user_dict.get(user_id, "Inconnu")
        timestamp_str = att.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        jour_annee = datetime.now().timetuple().tm_yday
        annee = datetime.now().year

        try:
            printer.set(align='center', bold=True, double_height=True)
            printer.text("Consomation\n")
            printer.set(align='left', bold=False, double_height=False)
            printer.text(f"Date      : {timestamp_str}\n")
            printer.text(f"ID        : {user_id}\n")
            printer.text(f"Nom       : {user_name}\n")
            printer.text(f"Creneau   : {slot_label}\n")
            printer.text("--------------------------\n")
            printer.text(f"{datetime.now().strftime('%H:%M:%S')}\n")
            printer.cut()
        except Exception as printer_error:
            log_error(f"Erreur d'impression ID {user_id} : {printer_error}")
            return

        label, slot_id = get_time_slot(datetime.now())
        if exempt:
            print("je suis dans exempt")
            Ajouter_Consomation_SQLITE(user_id, 1, slot_id, jour_annee, annee, time_conso, f"{label} {user_name}")
        else:
            print("je suis dans non exempt")
            Ajouter_Consomation_SQLITE(user_id, 1, slot_id, jour_annee, annee, time_conso, label)

    except Exception as e:
        log_error(f"Erreur print_ticket ID {att.user_id} : {e}")

def print_weekly_summary(p):
    try:
        conn = sqlite3.connect("raspberry_data.db")  # Utilisez DB_FILE pour SQLite
        cursor = conn.cursor()

        today = datetime.now().date()
        sunday = today - timedelta(days=today.weekday() + 1)
        start_of_week = datetime.combine(sunday, dt_time(0, 0))
        end_of_week = datetime.combine(today, dt_time(23, 59, 59))
        cursor.execute("""
                       SELECT date (Date_Consomation) as day, TYPE_REPAS_STR, TYPE_REPAS, COUNT (*)
                       FROM Consomation
                       WHERE Date_Consomation BETWEEN ? AND ?
                       GROUP BY day, TYPE_REPAS
                       ORDER BY day, TYPE_REPAS
                       """, (start_of_week.strftime("%Y-%m-%d %H:%M:%S"),
                             end_of_week.strftime("%Y-%m-%d %H:%M:%S")))
        results = cursor.fetchall()

        p.set(align='center', bold=True, double_height=True)
        p.text("RECAPITULATIF HEBDOMADAIRE\n")
        p.set(align='left', bold=False, double_height=False)

        p.text(f"Periode: {start_of_week.strftime('%d/%m/%Y')} au {end_of_week.strftime('%d/%m/%Y')}\n")
        p.text("=" * 32 + "\n")

        current_day = None
        total_week = 0

        for day, TYPE_REPAS_STR, type_repas, count in results:
            if day != current_day:
                if current_day is not None:
                    p.text("-" * 32 + "\n")
                current_day = day
                p.text(f"{datetime.strptime(day, '%Y-%m-%d').strftime('%A %d/%m')}:\n")

            p.text(f"  {TYPE_REPAS_STR:<20}{count:>10}\n")
            total_week += count

        p.text("=" * 32 + "\n")
        p.text(f"Total semaine: {total_week}\n")
        #  Ecriture fichier excel
        if usb_presente():
            mount_point = detect_and_check_usb()
            if mount_point:  # Si la clé est montée et valide...
                print_daily_report_excel_usb(2, mount_point)
                p.text("\n")
                p.set(align='center')
                p.text("Rapport copié sur clé USB !\n")
            else:
                print("⚠️ Rapport non sauvegardé : clé USB absente ou non montée.")
        conn.close()
        p.cut()
    except Exception as e:
        log_error(f"Erreur lors de l'impression du résumé journalier : {e}")



    except Exception as e:
        log_error(f"Erreur lors de l'impression du résumé hebdomadaire : {e}")


def test_printer():
    """
    Teste automatiquement la première imprimante USB trouvée.
    """
    printer = get_usb_printer()
    if printer:
        try:
            printer.text("Bonjour depuis imprimante USB !\n")
            printer.cut()
            print("🖨️ Test d’impression automatique réussi !")

        except Exception as e:
            print(f"⛔ Erreur lors de l'impression : {e}")

        finally:
            # ✅ Libère le périphérique USB proprement
            usb.util.dispose_resources(printer.device)
    else:
        print("⛔ Aucune imprimante détectée.")


from openpyxl import Workbook
from datetime import datetime, timedelta, time as dt_time
import sqlite3, os

# def print_daily_report_excel_usb(type_rapport, mount_point):
#     """
#     Génère un rapport de consommation complet et un résumé (hebdomadaire ou mensuel) sur la clé USB.
#     """
#     print(f"Type rapport: {type_rapport} | Destination: {mount_point}")
#
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#
#     # Détermination de la période et du titre
#     if type_rapport == 1:  # Rapport journalier
#         date_jour = datetime.now().date()
#         date_debut = datetime.combine(date_jour, dt_time.min)
#         date_fin = datetime.combine(date_jour, dt_time.max)
#         report_title = f"Consommations_Journalieres_{date_jour.strftime('%Y-%m-%d')}"
#         resume_title = None
#
#     elif type_rapport == 2:  # Rapport hebdomadaire
#         today = datetime.now().date()
#         start_of_week = today - timedelta(days=today.weekday() + 1)
#         date_debut = datetime.combine(start_of_week, dt_time.min)
#         date_fin = datetime.combine(today, dt_time.max)
#         report_title = f"Consommations_Hebdomadaires_{start_of_week.strftime('%Y-%m-%d')}_au_{today.strftime('%Y-%m-%d')}"
#         resume_title = "resume_hebdomadaire.xlsx"
#
#     elif type_rapport == 3:  # Rapport mensuel
#         today = datetime.now().date()
#         start_of_month = today.replace(day=1)
#         date_debut = datetime.combine(start_of_month, dt_time.min)
#         date_fin = datetime.combine(today, dt_time.max)
#         report_title = f"Consommations_Mensuelles_{start_of_month.strftime('%Y-%m-%d')}_au_{today.strftime('%Y-%m-%d')}"
#         resume_title = "resume_mensuel.xlsx"
#     else:
#         print("⚠️ Type de rapport non valide.")
#         return
#
#     # 🔹 Récupération des données de consommation
#     cursor.execute("""
#         SELECT Consomation.TYPE_REPAS_STR,
#                Consomation.id_utilisateur,
#                Consomation.Date_Consomation,
#                Utilisateurs.Nom_Prenom
#         FROM Consomation
#         INNER JOIN Utilisateurs ON Utilisateurs.Code_Utilisateur = Consomation.id_utilisateur
#         WHERE Date_Consomation BETWEEN ? AND ?
#     """, (date_debut.strftime("%Y-%m-%d %H:%M:%S"),
#           date_fin.strftime("%Y-%m-%d %H:%M:%S")))
#
#     results = cursor.fetchall()
#     conn.close()
#
#     if not results:
#         print("Aucune donnée de consommation pour la période sélectionnée.")
#         return
#
#     # 🔸 1️⃣ Rapport complet
#     wb = Workbook()
#     ws = wb.active
#     ws.title = "Consommations"
#     ws.append(["Type Repas", "ID Utilisateur", "Date Consommation", "Nom Prénom"])
#     for row in results:
#         ws.append(row)
#
#     try:
#         nom_fichier = f"{report_title}.xlsx"
#         chemin_fichier = os.path.join(mount_point, nom_fichier)
#         wb.save(chemin_fichier)
#         print(f"✅ Rapport détaillé enregistré : {chemin_fichier}")
#     except Exception as e:
#         print(f"❌ Erreur lors de l'enregistrement du rapport complet : {e}")
#         return
#
#     # 🔸 2️⃣ Rapport résumé (si hebdomadaire ou mensuel)
#     if resume_title:
#         from collections import Counter
#
#         # Compter les consommations par utilisateur
#         consommations_par_nom = Counter([row[3] for row in results])  # row[3] = Nom Prénom
#
#         wb_resume = Workbook()
#         ws_resume = wb_resume.active
#         ws_resume.title = "Résumé Consommations"
#         ws_resume.append(["Nom Prénom", "Total Consommations"])
#
#         for nom, total in consommations_par_nom.items():
#             ws_resume.append([nom, total])
#
#         try:
#             chemin_resume = os.path.join(mount_point, resume_title)
#             wb_resume.save(chemin_resume)
#             print(f"✅ Fichier résumé enregistré : {chemin_resume}")
#         except Exception as e:
#             print(f"❌ Erreur lors de l'enregistrement du résumé : {e}")
def print_daily_report_excel_usb(type_rapport, mount_point):
    """
    Génère un rapport Excel résumé (journalier, hebdomadaire, mensuel)
    à partir de la base SQLite locale.
    """
    import os
    import sqlite3
    from datetime import datetime, timedelta, time as dt_time
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side

    print("Début génération du rapport Excel résumé...")
    # --- Connexion à la base de données ---
    conn = sqlite3.connect(DB_PATH)
    print(DB_PATH)
    cursor = conn.cursor()
    print('indice 2')

    now = datetime.now()
    print('indice 3')
    # --- Définition des bornes temporelles selon le type de rapport ---
    if type_rapport == 1:
        date_debut = datetime.combine(now.date(), dt_time.min)
        date_fin = datetime.combine(now.date(), dt_time.max)
        titre = f"Resume des consommations du {date_debut.strftime('%d/%m/%Y')}"
        fichier_sortie = os.path.join(mount_point, f"resume_journalier_{now.strftime('%Y%m%d')}.xlsx")

    elif type_rapport == 2:
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        date_debut = datetime.combine(start_of_week.date(), dt_time.min)
        date_fin = datetime.combine(end_of_week.date(), dt_time.max)
        titre = f"Resume des consommations du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        fichier_sortie = os.path.join(mount_point, f"resume_hebdomadaire_{now.strftime('%Y%m%d')}.xlsx")

    elif type_rapport == 3:
        start_of_month = now.replace(day=1)
        date_debut = datetime.combine(start_of_month.date(), dt_time.min)
        date_fin = datetime.combine(now.date(), dt_time.max)
        titre = f"Resume des consommations du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        fichier_sortie = os.path.join(mount_point, f"resume_mensuel_{now.strftime('%Y%m%d')}.xlsx")

    else:
        print("❌ Type de rapport non valide (doit être 'journalier', 'hebdomadaire' ou 'mensuel').")
        return

    print(f"📅 Date début : {date_debut}")
    print(f"📅 Date fin   : {date_fin}")

    # --- Récupération des données depuis la base ---
    try:
        cursor.execute("""
            SELECT Utilisateurs.Code_Utilisateur,
                   Utilisateurs.Nom_Prenom,
                   COUNT(*) AS total
            FROM Consomation
            INNER JOIN Utilisateurs ON Utilisateurs.Code_Utilisateur = Consomation.id_utilisateur
            WHERE Date_Consomation BETWEEN ? AND ?
            GROUP BY Utilisateurs.Code_Utilisateur, Utilisateurs.Nom_Prenom
            ORDER BY Utilisateurs.Nom_Prenom ASC
        """, (
            date_debut.strftime("%Y-%m-%d %H:%M:%S"),
            date_fin.strftime("%Y-%m-%d %H:%M:%S")
        ))
        donnees = cursor.fetchall()
        print(f"✅ {len(donnees)} lignes récupérées.")
    except Exception as e:
        print(f"❌ Erreur SQL : {e}")
        donnees = []

    conn.close()

    # --- Création du classeur Excel ---
    wb = Workbook()
    ws = wb.active
    ws.title = "Resume"

    # --- Styles ---
    font_titre = Font(size=14, bold=True)
    font_entete = Font(bold=True)
    border_gray = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC")
    )
    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")

    # --- Titre ---
    ws.merge_cells("A1:C1")
    ws["A1"] = titre
    ws["A1"].font = font_titre
    ws["A1"].alignment = align_left  # aligné à gauche

    # --- Lignes vides après le titre ---
    ws.append([])
    ws.append([])
    ws.append([])

    # --- En-têtes ---
    headers = ["Code Employe", "Nom et Prenom", "Quantite"]
    ws.append(headers)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=ws.max_row, column=col)
        cell.font = font_entete
        cell.alignment = align_center
        cell.border = border_gray

    # --- Lignes de données ---
    for code, nom_prenom, total in donnees:
        ws.append([code, nom_prenom, total])

    # --- Style des cellules de données ---
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=1, max_col=3):
        for idx, cell in enumerate(row, start=1):
            cell.border = border_gray
            if idx == 1:  # Code Employe
                cell.alignment = align_center
            elif idx == 2:  # Nom et Prenom
                cell.alignment = align_left
            elif idx == 3:  # Quantite
                cell.alignment = align_center

    # --- Largeur des colonnes ---
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 15

    # --- Ligne du total ---
    last_data_row = ws.max_row
    total_row = last_data_row + 2
    ws[f"B{total_row}"] = "Total consommations :"
    ws[f"B{total_row}"].font = font_entete
    ws[f"C{total_row}"] = f"=SUM(C5:C{last_data_row})"
    ws[f"C{total_row}"].font = font_entete
    ws[f"C{total_row}"].alignment = align_center

    # --- Sauvegarde du fichier ---
    try:
        wb.save(fichier_sortie)
        print(f"✅ Rapport Excel résumé sauvegardé sur {fichier_sortie}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde du fichier : {e}")



