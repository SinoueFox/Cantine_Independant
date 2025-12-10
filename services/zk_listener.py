# services/zk_listener.py
import time
import subprocess
import locale
from zk import ZK
from utils.logger import logger


def run_zk_listener(zk_device, printer, nom_societe, Mode_Fonctionnement, stop_event=None):
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    zk_conn = None
    while True:
        try:
            zk_conn = zk_device.connect()
            zk_time = zk_conn.get_time()
            date_str = zk_time.strftime('%Y-%m-%d %H:%M:%S')
            subprocess.run(["sudo", "date", "-s", date_str], check=True)
            logger.info("Heure Raspberry synchronisée avec la pointeuse: %s", date_str)

            users = zk_conn.get_users()
            user_dict = {user.user_id: user.name for user in users}
            logger.info("ZK ready, %d users", len(user_dict))

            for att in zk_conn.live_capture():
                if att:
                    logger.debug("Pointage: %s", att.user_id)
                    try:
                        process_attendance(att, user_dict, printer, nom_societe, Mode_Fonctionnement)
                    except Exception as e:
                        logger.exception("Erreur process_attendance: %s", e)

        except Exception as e:
            logger.exception("Erreur ZK listener, reconnect dans 5s: %s", e)
            try:
                if zk_conn:
                    zk_conn.disconnect()
            except Exception:
                pass
            time.sleep(5)
