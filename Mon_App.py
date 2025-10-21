import signal
import sys
from flask import Flask, render_template, request, redirect, jsonify, flash
from Printer_Function import test_printer, print_daily_summary3,print_daily_report_excel_usb,print_daily_report_pdf_usb, print_weekly_summary, print_month_summary,copy_usb_report
from Fonctions_BDD import init_db,Vider_base,charger_configuration
from USB_Fonctions import detect_and_mount_usb, usb_presente, get_usb_printer
from zk import ZK
from Cantine_Functions import get_time_slot, Import_from_Excel, charger_time_slots, POINTEUSE_IP, POINTEUSE_PORT
from datetime import datetime
import sqlite3
import locale
import time
import threading
import subprocess
import os

CWD = os.path.dirname(os.path.realpath(__file__))
DB_FILE = "raspberry_data.db"
LOG_PATH = os.path.join(CWD, "errors.log") # <-- AJOUTEZ CETTE LIGNE


def log_error(message):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
         f.write(f"{datetime.now().isoformat()} - {message}\n")
app = Flask(__name__)
app.secret_key = "secret-key-123"  # Nécessaire pour afficher les messages flash


# --- Gestion de l'arrêt propre ---
def signal_handler(sig, frame):
    print("\n🛑 Arrêt propre du serveur Flask...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# --- Fonctions Utilitaires ---
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, Code_Utilisateur, Nom_Prenom, Nombre_Repas FROM Utilisateurs")
    users = cur.fetchall()
    conn.close()
    print(users)
    return users


# --- Routes Flask ---
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/pointeuse')
def pointeuse():
    return render_template("Pointeuse.html")


@app.route('/imprimante')
def imprimante():
    return render_template("Imprimante.html")


@app.route('/imprimante/get')
def imprimante_get():
    result = test_printer()
    return f"Résultat : {result}"


@app.route('/rapport')
def rapport():
    return render_template("Rapport.html")





@app.route('/Import_Excel')
def import_excel():
    if Import_from_Excel() :
        print('OK')
        return "Importation terminée avec succès !"

    else :
        print('Pas OK')
        return "Importation Echoue !"


from flask import send_file, redirect, flash
from datetime import datetime

@app.route('/saisie_configuration', methods=['GET', 'POST'])
def saisie_configuration():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if request.method == 'POST':
        nom_societe = request.form.get('nom_societe')
        numero_borne = request.form.get('numero_borne')

        # Vérifier si une ligne existe déjà
        cursor.execute("SELECT COUNT(*) FROM Configuration")
        exists = cursor.fetchone()[0]

        if exists == 0:
            cursor.execute("INSERT INTO Configuration (NUMERO_BORNE, NOM_SOCIETE) VALUES (?, ?)",
                           (numero_borne, nom_societe))
        else:
            cursor.execute("UPDATE Configuration SET NUMERO_BORNE = ?, NOM_SOCIETE = ?",
                           (numero_borne, nom_societe))

        conn.commit()
        conn.close()
        flash("✅ Configuration enregistrée avec succès.")
        return redirect('/configuration')

    # En GET → Récupérer les valeurs existantes pour pré-remplir
    cursor.execute("SELECT NUMERO_BORNE, NOM_SOCIETE FROM Configuration LIMIT 1")
    config = cursor.fetchone()
    conn.close()

    numero_borne = config[0] if config else ""
    nom_societe = config[1] if config else ""

    return render_template('configuration_entreprise.html', numero_borne=numero_borne, nom_societe=nom_societe)


@app.route('/vider_base')
def vider_base():
    try:
        Vider_base()  # Appel de ta fonction Python qui vide la base
        flash("✅ Base de données vidée avec succès.", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de la suppression : {e}", "error")
    return redirect('/configuration')

@app.route('/generer_rapport', methods=["POST"])
def generer_rapport():
    type_rapport_str = request.form.get("type_rapport")
    destination = request.form.get("destination")
    format_export = request.form.get("format")

    print("Type de rapport :", type_rapport_str)
    print("Destination :", destination)
    print("Format :", format_export)

    # Correspondance des types de rapport
    rapport_map = {"Journalier": 1, "Hebdomadaire": 2, "Mensuel": 3}
    type_rapport = rapport_map.get(type_rapport_str)

    if not type_rapport:
        return "❌ Type de rapport invalide."

    # CAS 1️⃣ : Impression ticket
    if destination == "ticket":
        if printer:
            print_daily_summary3(printer)
            return f"✅ Rapport {type_rapport_str} imprimé sur ticket."
        return "❌ Aucune imprimante détectée."

    # CAS 2️⃣ : Téléchargement (PDF ou Excel)
    if destination == "download":
        if format_export == "excel":
            buffer, filename = print_daily_report_excel_usb(type_rapport, mount_point, download=1)
            if buffer:
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            return "❌ Erreur lors de la génération du fichier Excel."

        elif format_export == "pdf":
            buffer, filename = print_daily_report_pdf_usb(type_rapport, mount_point, download=1)
            if buffer:
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            return "⚠ Génération PDF pour téléchargement en cours de développement."

        else:
            return "❌ Format non pris en charge pour le téléchargement."

    # CAS 3️⃣ : Sauvegarde sur USB
    if destination == "usb":
        if format_export == "excel":
            copy_usb_report(printer, type_rapport)
            return f"✅ Rapport Excel {type_rapport_str} enregistré sur USB."

        elif format_export == "pdf":
            # TODO: Génération PDF USB

            return f"⚠ Rapport PDF {type_rapport_str} USB en cours de développement."

        return "❌ Format non pris en charge pour USB."

    return f"❌ Combinaison non prise en charge ({type_rapport_str} / {destination} / {format_export})."

@app.route('/configuration')
def configuration():
    return render_template('configuration.html')

# @app.route('/Rapport_Journalier', methods=["POST"])
# def rapport_journalier():
#     try:
#
#         if printer:
#             print_daily_summary3(printer)
#             return jsonify(success=True)
#         else:
#             raise Exception("Imprimante non détectée.")
#     except Exception as e:
#         print(f"Erreur impression journalière : {e}")
#         log_error(f"Erreur Rapport_Journalier : {e}")
#         return jsonify(success=False, error=str(e))
#
#
# @app.route('/Rapport_Hebdomadaire', methods=["POST"])
# def rapport_hebdomadaire():
#     try:
#
#         if printer:
#             print_weekly_summary(printer)
#             return jsonify(success=True)
#         else:
#             raise Exception("Imprimante non détectée.")
#     except Exception as e:
#         print(f"Erreur impression hebdomadaire : {e}")
#         return jsonify(success=False, error=str(e))
#
#
# @app.route('/Rapport_Mensuel', methods=["POST"])
# def rapport_mensuel():
#     try:
#         if printer:
#             print_month_summary(printer)
#             return jsonify(success=True)
#         else:
#             raise Exception("Imprimante non détectée.")
#     except Exception as e:
#         print(f"Erreur impression mensuelle : {e}")
#         return jsonify(success=False, error=str(e))


@app.route("/Utilisateur")
def utilisateurs():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, Code_Utilisateur, Nom_Prenom, Nombre_Repas
        FROM Utilisateurs
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    users = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM Utilisateurs")
    total_users = cur.fetchone()[0]
    conn.close()

    total_pages = (total_users + per_page - 1) // per_page
    return render_template("Utilisateur.html",
                           utilisateurs=users,
                           page=page,
                           total_pages=total_pages)


@app.route("/ajouter_utilisateur", methods=["POST"])
def ajouter_utilisateur():
    Code_Utilisateur = request.form["Code_Utilisateur"]
    Nom_Prenom = request.form["Nom_Prenom"]

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Utilisateurs (Code_Utilisateur, Nom_Prenom, Nombre_Repas)
            VALUES (?, ?, 1)
        """, (Code_Utilisateur, Nom_Prenom))
        conn.commit()

        # Synchronisation avec la pointeuse
        zk_device = ZK(POINTEUSE_IP, port=POINTEUSE_PORT, timeout=10)
        conn2 = zk_device.connect()
        conn2.set_user(uid=int(Code_Utilisateur), name=Nom_Prenom)
        conn2.disconnect()

        flash("✅ Utilisateur ajouté avec succès.", "success")

    except sqlite3.IntegrityError:
        flash("❌ Ce Code Utilisateur existe déjà.", "danger")
    except Exception as e:
        flash(f"❌ Erreur : {e}", "danger")
    finally:
        conn.close()

    return redirect("/Utilisateur")


from zk import ZK, const

from zk import ZK, const

@app.route("/update_user", methods=["POST"])
def update_user():
    user_id = request.form["id"]
    nom = request.form["Nom_Prenom"]

    # 1️⃣ Mise à jour locale SQLite
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE Utilisateurs SET Nom_Prenom = ? WHERE id = ?", (nom, user_id))
        conn.commit()
        success = cur.rowcount > 0
        cur.execute("SELECT Code_Utilisateur FROM Utilisateurs WHERE id = ?", (user_id,))
        row = cur.fetchone()
        code_employe = row[0] if row else None
    except sqlite3.Error as e:
        return {"success": False, "error": f"Erreur SQLite : {e}"}
    finally:
        conn.close()

    if not success:
        return {"success": False, "error": "Utilisateur non trouvé dans la base locale."}

    # 2️⃣ Mise à jour sur la pointeuse ZKTeco
    try:
        zk = ZK("192.168.100.201", port=4370, timeout=5)
        conn = zk.connect()
        conn.disable_device()
        print("indice 1")
        users = conn.get_users()
        print(users)
        print("user_id =" + user_id)
        user_found = None
        user_found = next((u for u in users if str(u.user_id) == str(code_employe)), None)

        if user_found:
            print(f"Utilisateur trouvé : UID={user_found.uid}, Nom={user_found.name}")
        else:
            print("Utilisateur non trouvé")

        if user_found:
            print("user found")
            conn.set_user(
                uid=int(user_found.uid),
                name=nom,
                privilege=user_found.privilege,
                password=user_found.password,
                group_id=user_found.group_id,
                user_id=user_found.user_id
            )
            result = True
        else:
            result = False

        conn.enable_device()
        conn.disconnect()

    except Exception as e:
        return {"success": False, "error": f"Erreur pointeuse : {e}"}

    # 3️⃣ Réponse JSON
    return {"success": result}


@app.route('/api/utilisateurs')
def api_utilisateurs():
    import sqlite3
    import math

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Exemple de table : id, code_utilisateur, nom_prenom, repas
    cur.execute("SELECT COUNT(*) FROM utilisateurs")
    total = cur.fetchone()[0]
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    cur.execute("""
        SELECT id, Code_Utilisateur, Nom_Prenom, Nombre_repas
        FROM utilisateurs
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    rows = cur.fetchall()
    conn.close()

    return jsonify({
        "utilisateurs": rows,
        "page": page,
        "total_pages": total_pages
    })


@app.route("/delete_user", methods=["POST"])
def delete_user():
    user_id = request.form["id"]
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM Utilisateurs WHERE id = ?", (user_id,))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        print("Erreur delete:", e)
        return jsonify(success=False, error=str(e))
    finally:
        conn.close()


# --- Thread de capture ZKTeco ---
def run_zk_listener(zk_device):
    from Cantine_Functions import process_attendance
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    try:
        zk_conn = zk_device.connect()

        # --- Lecture de l'heure sur la pointeuse
        zk_time = zk_conn.get_time()
        print(f"🕒 Heure de la pointeuse : {zk_time:%Y-%m-%d %H:%M:%S}")

        # --- Conversion de la date au format Linux
        date_str = zk_time.strftime('%Y-%m-%d %H:%M:%S')

        # --- Mise à jour de l’heure du Raspberry Pi
        # ⚠️ Nécessite les droits sudo
        subprocess.run(["sudo", "date", "-s", date_str], check=True)

        print(f"✅ Heure du Raspberry Pi synchronisée avec la pointeuse ({date_str})")

        users = zk_conn.get_users()
        user_dict = {user.user_id: user.name for user in users}
        print(user_dict)
        print("✅ Système prêt. En attente de pointages...")

        while True:
            try:
                for att in zk_conn.live_capture():
                    if att:
                        print(f"📲 Pointage détecté : {att.user_id}")
                        print(user_dict)
                        process_attendance(att, user_dict, printer,nom_societe)
            except Exception as e:
                print(f"⚠️ Erreur live_capture : {e}. Reconnexion dans 5s...")
                time.sleep(5)
                zk_conn.disconnect()
                zk_conn = zk_device.connect()

    except Exception as e:
        print(f"❌ Erreur principale ZKTeco : {e}")
    finally:
        try:
            zk_conn.disconnect()
        except:
            pass

def monitor_usb():
    """
    Surveille la présence de la clé USB et tente de la remonter automatiquement
    lorsqu'elle est retirée puis réinsérée.
    """
    etat_precedent = None
    while True:
        try:
            present = usb_presente()
            if present and not etat_precedent:
                print("🔌 Clé USB détectée → tentative de montage...")
                detect_and_mount_usb()

            elif not present and etat_precedent:
                print("❌ Clé USB retirée.")

            etat_precedent = present
        except Exception as e:
            print(f"⚠️ Erreur dans la surveillance USB : {e}")

        time.sleep(5)  # Vérifie toutes les 5 secondes
# --- Lancement principal ---
if __name__ == '__main__':
    print("🚀 Initialisation de la base de données...")
    init_db()
    config = charger_configuration()
    nom_societe = config.get("nom_societe", "Société inconnue")
    print("✅ Base de données prête. Lancement du serveur Flask...")

    mount_point = detect_and_mount_usb()
    if not mount_point:
        print("⚠️ Impossible de détecter ou de monter la clé USB.")
    else:
        print("la clé USB OK.")
    zk_device = ZK('192.168.100.201', port=4370)
    label, slot_id = get_time_slot(datetime.now())
    print(label, slot_id)

    if usb_presente():
        print("✅ Clé USB détectée")
        charger_time_slots()

    printer = get_usb_printer()
    if printer:
        printer._raw(b'\x1b\x74\x02')
        printer.set(align='center', bold=True, double_height=True)
        printer.text("PROGRAMME COMMENCE\n")
        printer.text(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        printer.cut()
    else:
        print("⚠️ Aucune imprimante détectée.")

    listener_thread = threading.Thread(target=run_zk_listener, args=(zk_device,), daemon=True)
    listener_thread.start()
    #trhreading pour la cle USB
    usb_thread = threading.Thread(target=monitor_usb, daemon=True)
    usb_thread.start()
    print("🧩 Thread de surveillance USB lancé.")

    app.run(host="0.0.0.0", port=5010, debug=False)
