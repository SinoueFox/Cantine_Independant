import signal
import sys
from flask import Flask, render_template, request, redirect, jsonify, flash
from Printer_Function import test_printer, print_daily_summary3, print_weekly_summary, print_month_summary
from Fonctions_BDD import init_db
from USB_Fonctions import detect_and_mount_usb, usb_presente, get_usb_printer
from zk import ZK
from Cantine_Functions import get_time_slot, Import_from_Excel, charger_time_slots, POINTEUSE_IP, POINTEUSE_PORT
from datetime import datetime
import sqlite3
import locale
import time
import threading
from Constantes import time_slots

DB_FILE = "raspberry_data.db"

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


@app.route('/Configuration')
def configuration():
    return render_template("Configuration.html")


@app.route('/Import_Excel')
def import_excel():
    Import_from_Excel()
    return "Importation terminée avec succès !"


@app.route('/Rapport_Journalier', methods=["POST"])
def rapport_journalier():
    try:
        if printer:
            print_daily_summary3(printer)
            return jsonify(success=True)
        else:
            raise Exception("Imprimante non détectée.")
    except Exception as e:
        print(f"Erreur impression journalière : {e}")
        return jsonify(success=False, error=str(e))


@app.route('/Rapport_Hebdomadaire', methods=["POST"])
def rapport_hebdomadaire():
    try:
        if printer:
            print_weekly_summary(printer)
            return jsonify(success=True)
        else:
            raise Exception("Imprimante non détectée.")
    except Exception as e:
        print(f"Erreur impression hebdomadaire : {e}")
        return jsonify(success=False, error=str(e))


@app.route('/Rapport_Mensuel', methods=["POST"])
def rapport_mensuel():
    try:
        if printer:
            print_month_summary(printer)
            return jsonify(success=True)
        else:
            raise Exception("Imprimante non détectée.")
    except Exception as e:
        print(f"Erreur impression mensuelle : {e}")
        return jsonify(success=False, error=str(e))


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


@app.route("/update_user", methods=["POST"])
def update_user():
    user_id = request.form["id"]
    nom = request.form["Nom_Prenom"]
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE Utilisateurs SET Nom_Prenom = ? WHERE id = ?", (nom, user_id))
        conn.commit()
        success = cur.rowcount > 0
    except sqlite3.Error as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
    return {"success": success}


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

    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        zk_conn = zk_device.connect()
        zk_conn.set_time(datetime.now())
        print(f"🕒 Heure synchronisée : {datetime.now():%Y-%m-%d %H:%M:%S}")

        users = zk_conn.get_users()
        user_dict = {user.user_id: user.name for user in users}
        print("✅ Système prêt. En attente de pointages...")

        while True:
            try:
                for att in zk_conn.live_capture():
                    if att:
                        print(f"📲 Pointage détecté : {att.user_id}")
                        print(user_dict)
                        process_attendance(att, user_dict, printer)
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


# --- Lancement principal ---
if __name__ == '__main__':
    print("🚀 Initialisation de la base de données...")
    init_db()
    print("✅ Base de données prête. Lancement du serveur Flask...")

    mount_point = detect_and_mount_usb()
    if not mount_point:
        print("⚠️ Impossible de détecter ou de monter la clé USB.")

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

    app.run(host="0.0.0.0", port=5013, debug=False)
