from flask import Flask, render_template, request, redirect, url_for, flash
import threading
from datetime import datetime
from utils.Actualise_Data import start_loop_sync_thread
# --- Imports des utilitaires simplifiés ---
from utils.db import init_db
from utils.pointeuse import start_zk_thread
from utils.usb import monitor_usb
from utils.config_manager import get_config_for_template, update_config_file ,definit_mode_fonctionnement # NOUVEAU
from Printer_Function import test_printer
import config
import importlib
# --- Imports des variables de config ---
# L'import direct doit rester pour la logique d'initialisation (mode, IP)

from utils.Actualise_Data import loop_sync
app = Flask(__name__)
# IMPORTANT: Changer cette clé en production.
app.secret_key = "secret-key-123"


# --- Routes Flask ---

@app.route('/')
def index():
    return render_template("index.html")

# @app.route("/update_horaires", methods=["POST"])
# def update_horaires():
#     from datetime import time
#
#     # Charger time_slots actuel
#     import config
#     slots = config.time_slots
#
#     for nom, slot in slots.items():
#         start_key = f"{nom}_start"
#         end_key = f"{nom}_end"
#
#         if start_key in request.form and end_key in request.form:
#             start_str = request.form[start_key]
#             end_str = request.form[end_key]
#
#             # Convertir HH:MM -> time
#             h1, m1 = map(int, start_str.split(":"))
#             h2, m2 = map(int, end_str.split(":"))
#
#             slot["start"] = time(h1, m1)
#             slot["end"] = time(h2, m2)
#
#     # Réécrire dans config.py
#     update_config_file("time_slots", slots)
#
#     return redirect("/config")

# @app.route('/config')
# def afficher_configuration():
#     # Appel de la fonction déplacée dans le manager
#     categories = get_config_for_template()
#     heure_actuelle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#return render_template("config.html", **get_config_for_template())

@app.route('/config')
def afficher_configuration():
        # Heure actuelle
        heure_actuelle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Si tu veux garder tes "categories" depuis config_manager
        categories = get_config_for_template()

        # Passe tout ce dont le template a besoin
        return render_template(
            'config.html',
            config=categories,  # ancien dict si nécessaire
            current_time=heure_actuelle,
            PRINTER_USB_NAME= config.PRINTER_USB_NAME,
            LOG_PATH=config.LOG_PATH,
            USB_CHECK_INTERVAL=config.USB_CHECK_INTERVAL,
            GPIO_TOURNIQUET=config.GPIO_TOURNIQUET,
            GPIO1=config.GPIO1,
            GPIO2=config.GPIO2,
            MODE_TICKET=config.MODE_TICKET,
            MODE_ABONNEMENT=config.MODE_ABONNEMENT,
            MODE_S_AB_TICK=config.MODE_S_AB_TICK,
            MODE_AB_TICK=config.MODE_AB_TICK,
            MODE_TICK_SANS_DOUBLON=config.MODE_TICK_SANS_DOUBLON,
            Nom_Societe=config.Nom_Societe,
            time_slots=config.time_slots
        )

# --- Update general config ---
@app.route("/update_config", methods=["POST"])
def update_config():
    form_data = request.form.to_dict()

    # convertir certains champs si tu veux (ex: nombres)
    # exemple: form_data['GPIO1'] = int(form_data['GPIO1'])  # si nécessaire

    success, message = update_config_file(form_data)  # la fonction doit renvoyer (bool, message)
    # recharge le module config pour refléter les nouvelles valeurs en mémoire
    importlib.reload(config)

    flash(message, "success" if success else "error")
    return redirect(url_for("config"))

# --- Update mode sans doublon ---
@app.route("/update_mode_sans_doublon", methods=["POST"])
def update_mode_sans_doublon():
    # la checkbox renvoie la présence de la clé si cochée
    value = 1 if request.form.get("mode_tick_sans_doublon") == "1" else 0
    success, message = update_config_file({"MODE_TICK_SANS_DOUBLON": value})
    importlib.reload(config)
    flash(message, "success" if success else "error")
    return redirect(url_for("config"))

# --- Update horaires (déjà existait) mais avec reload + message ---
@app.route("/update_horaires", methods=["POST"])
def update_horaires():
    from datetime import time
    import config as cfg

    slots = cfg.time_slots
    for nom, slot in slots.items():
        start_key = f"{nom}_start"
        end_key = f"{nom}_end"

        if start_key in request.form and end_key in request.form:
            start_str = request.form[start_key]
            end_str = request.form[end_key]
            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))
            slot["start"] = time(h1, m1)
            slot["end"] = time(h2, m2)

    # Appelle ta fonction pour sauvegarder la structure time_slots
    success, message = update_config_file({"time_slots": slots})
    importlib.reload(config)
    flash(message, "success" if success else "error")
    return redirect(url_for("config_page"))
# @app.route("/config")
# def config_page():
#     from config import MODE_TICK_SANS_DOUBLON, time_slots
#     return render_template("config.html",
#                            mode_tick_sans_doublon=MODE_TICK_SANS_DOUBLON,
#                            time_slots=time_slots)
# @app.route('/update_config', methods=['POST'])
# def update_configuration():
#     # Récupération et appel de la fonction déplacée
#     form_data = request.form.to_dict()
#     success, message = update_config_file(form_data)
#
#     # Utilisation de flash pour les messages utilisateur
#     flash(message, 'success' if success else 'error')
#
#     # Redirection vers la page de configuration
#     return redirect(url_for('afficher_configuration'))

# @app.route("/update_config", methods=["POST"])
# def update_config():
#     form_data = request.form.to_dict()
#
#     success, message = update_config_file(form_data)
#
#     flash(message, "success" if success else "error")
#     #return redirect(url_for("config"))
#     return redirect(url_for("afficher_configuration"))

@app.route('/pointeuse')
def afficher_pointeuse():
    return render_template("Pointeuse.html", pointeuse_ip=POINTEUSE_IP)


@app.route('/imprimante')
def afficher_imprimante():
    return render_template("Imprimante.html")


@app.route('/rapport')
def rapport():
    return render_template("Rapport.html")

@app.route('/config_ip', methods=['GET', 'POST'])
def config_ip():
    if request.method == 'POST':
        new_ip = request.form.get('ip')

        if not new_ip:
            flash(("danger", "❌ IP invalide !"))
            return redirect(url_for('config_ip'))

        # 🔧 ICI tu peux mettre ton script pour modifier l’IP
        # Exemple :
        # os.system(f"sudo nmcli con mod 'Wired connection 1' ipv4.addresses {new_ip}/24")

        flash(("success", f"✅ Adresse IP changée en {new_ip}"))
        return redirect(url_for('config_ip'))

    # GET → Affiche la page
    return render_template('config_ip.html')
# @app.route("/config")
# def afficher_configuration():
#     return render_template("config.html", **get_config_for_template())

@app.route('/configuration_entreprise',methods=['GET', 'POST'])
def configuration_entreprise():


    return  render_template('configuration_entreprise.html')
# --- Lancement principal ---
if __name__ == '__main__':
    print("🚀 Initialisation de la base de données...")
    init_db()

    start_loop_sync_thread()
    test_printer()
    print('Mode Fonctionnement = ' + definit_mode_fonctionnement())
    # Lancement des threads (inchangé)
    start_zk_thread(definit_mode_fonctionnement(), printer=None, nom_societe="Votre Société")
    # monitor_usb(...)

    print(f"🌐 Serveur Flask démarré sur http://0.0.0.0:5010")
    app.run(host="0.0.0.0", port=5010, debug=False)