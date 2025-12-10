import threading, time
from zk import ZK
from USB_Fonctions import get_usb_printer
from config import POINTEUSE_IP, POINTEUSE_PORT, GPIO1, GPIO2
from Cantine_Functions import process_attendance_v2
def run_zk_listener(mode_fonctionnement, printer, nom_societe):
    zk_device = ZK(POINTEUSE_IP, port=POINTEUSE_PORT)
    try:
        printer = get_usb_printer()
        zk_conn = zk_device.connect()
        print("✅ Connexion ZKTeco établie")
        users = zk_conn.get_users()
        user_dict = {user.user_id: user.name for user in users}

        while True:
            try:
                for att in zk_conn.live_capture():
                    if att:
                        print(f"📲 Pointage détecté : {att.user_id}")
                        # Ici on appelle une fonction de traitement (process_attendance)
                        process_attendance_v2(att, user_dict, printer, nom_societe, mode_fonctionnement)
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

def start_zk_thread(mode_fonctionnement, printer, nom_societe):
    thread = threading.Thread(target=run_zk_listener, args=(mode_fonctionnement, printer, nom_societe), daemon=True)
    thread.start()
    print("🟢 Thread ZKTeco lancé")

def Ajouter_Utilisateur_sur_pointeuse(user_id,name):
    from config import POINTEUSE_IP, POINTEUSE_PORT
    # Ajouter l'utilisateur
    zk_device = ZK(POINTEUSE_IP, port=POINTEUSE_PORT)
    ZK_conn = zk_device.connect()
    ZK_conn.set_user(name=name, user_id=str(user_id))  # Le vrai identifiant utilisateur)