import time
from firebird.driver import connect
import sqlite3
import sqlite3
from zk import ZK
from utils.pointeuse import Ajouter_Utilisateur_sur_pointeuse
from config import POINTEUSE_IP, POINTEUSE_PORT



HOST = "192.168.100.10"
DB_PATH = r"C:\Cantine_Aero2\Data\DATA_CANTINE_AERO.fdb"
DSN = f"{HOST}:{DB_PATH}"

USERNAME = "SYSDBA"
PASSWORD = "BPSI2000"

# Connexion Firebird globale (OK : Firebird supporte le multi-thread)
try:
    print(f"Connecting to Firebird server at: {DSN}")
    connect_fb = connect(
        database=f"{HOST}/3050:{DB_PATH}",
        user=USERNAME,
        password=PASSWORD,
    )
    print("Connected successfully!")
except Exception as e:
    print("🔥 Database error occurred:")
    print(e)


# ─────────────────────────────────────────────
#  IMPORTANT : SQLite NE DOIT PAS être créé ici
# ─────────────────────────────────────────────
# ❌ A SUPPRIMER :
# sq_conn_actualise = sqlite3.connect("raspberry_data.db")
# sqlite_cur_actualise = sq_conn_actualise.cursor()
# ─────────────────────────────────────────────


# ----------- CONSOMMATEURS -------------
def sync_consomateurs(code_sync_log,code_raspberry_status, record_id, operation):

    connex_sql = sqlite3.connect('raspberry_data.db')
    cursor = connex_sql.cursor()
    try:
        fb_cursor = connect_fb.cursor()  # ✔ CURSEUR Firebird
        zk_device = ZK(POINTEUSE_IP, port=POINTEUSE_PORT)
        zk_conn = zk_device.connect()
        print('Entree sync consomateur 1')
        fb_cursor.execute("""
            SELECT code_consomateur, nom, prenom, nombre_tickets, code_employe
            FROM  CONSOMATEURS
            WHERE code_consomateur = ? """, (record_id,))
        print('Entree sync consomateur 2')

        data = fb_cursor.fetchone()
        print('Entree sync consomateur 3')
        if not data:
            print("⚠ Aucun consomateur trouvé.")
            return

        code_cons, nom, prenom, nbr_tickets, code_emp = data
        fb_cursor.execute("""
                          UPDATE RASPBERRY_STATUT set ETAT = 'DONE' 
                          WHERE code_raspberry_statut = ? """, (code_raspberry_status,))

        if operation == "INSERT":
            print('INSERT')
            cursor.execute("""INSERT OR IGNORE INTO Consomateurs (Nom_Prenom, Nombre_Tickets, code_employe)
                VALUES (?, ?, ?) """, (nom + " " + prenom, nbr_tickets, code_emp))
            #Ajouter Utilisateur sur pointeuse
            print('Ajouter Utilisateur sur pointeuse')
            Ajouter_Utilisateur_sur_pointeuse( code_emp, nom + " " + prenom)


        elif operation == "UPDATE":
            print('UPDATE')
            cursor.execute(""" UPDATE CONSOMATEURS SET Nom_Prenom=?, nombre_tickets=?, code_employe=?
                WHERE code_consomateur = ?""", (nom + " " + prenom, nbr_tickets, code_emp, code_cons))

        connex_sql.commit()

    except Exception as e:
        print("❌ Erreur sync_consomateurs :", e)

    finally:
        connect_fb.commit()
        cursor.close()
        connex_sql.close()

# ----------- PACK_TICKET -------------
def sync_pack_ticket(record_id,code_raspberry_status):
    connex_sql = sqlite3.connect('raspberry_data.db')
    cursor = connex_sql.cursor()
    print('pack_ticket1')
    try :
        curs_fb = connect_fb.cursor()
        curs_fb.execute(""" SELECT pack_tickets.CODE_CONSOMATEUR,consomateurs.CODE_EMPLOYE, QUANTITE_ACHETE 
            FROM PACK_TICKETS  inner join consomateurs on (consomateurs.CODE_CONSOMATEUR = PACK_TICKETS.CODE_CONSOMATEUR) WHERE CODE_PACK_TICKET = ? """, (record_id,))

        print('pack_ticket2')
        data = curs_fb.fetchone()
        print('rows in raspberry status pack ticket= ' + str(len(data)))
        print("Total pack =", len(data))
        # if not data:
        #     print("⚠ Aucun PACK_TICKET trouvé.")
        #     return

        code_cons, code_employe, quant_achete = data

        cursor.execute(""" UPDATE CONSOMATEURS SET nombre_tickets = ? WHERE Code_Employe = ?""", (quant_achete, code_employe))

        curs_fb.execute("""
                          UPDATE RASPBERRY_STATUT
                          set ETAT = 'DONE'
                          WHERE code_raspberry_statut = ? """, (code_raspberry_status,))
        print(f"🎫 Maj SQLite: {code_cons} → {quant_achete} tickets")
        connex_sql.commit()

    except Exception as e:
            print("❌ Erreur sync_consomateurs :", e)

    finally:
        connect_fb.commit()
        cursor.close()
        connex_sql.close()

# def loop_sync():
#     from config import BORNE
#     BORNE1 = BORNE
#     print("📡 Boucle principale démarrée")
#
#     while True:
#         try:
#             fb_curseur = connect_fb.cursor()
#
#             # Récupère tous les enregistrements PENDING
#             fb_curseur.execute("""
#                                SELECT sync_log.CODE_SYNC_LOG,
#                                       sync_log.TABLE_NAME,
#                                       sync_log.RECORD_ID,
#                                       RASPBERRY_STATUT.CODE_RASPBERRY_STATUT,
#                                       raspberry_statut.OPERATION
#                                FROM SYNC_LOG
#                                         JOIN raspberry_statut
#                                              ON sync_log.ID_SYNC_LOG = raspberry_statut.CODE_SYNC_LOG
#                                WHERE raspberry_statut.ETAT = 'PENDING'
#                                  AND raspberry_statut.CODE_BORNE = ?
#                                """, (BORNE1,))
#
#             rows = fb_curseur.fetchall()  # récupère toutes les lignes
#
#             if len(rows) > 0:
#                 # Connexion à SQLite sur le Raspberry
#                 print('rows in raspberry status = ' + str(len(rows)))
#                 print("Total consomateurs =", len(rows))
#
#                 for row in rows:
#                     code_sync_log = row[0]
#                     table_name = row[1]
#                     record_id = row[2]
#                     code_raspberry_status = row[3]
#                     operation = row[4]
#
#                     # Exemple de traitement : mise à jour de la base SQLite
#                     # À adapter selon tes besoins
#                     if table_name == 'CONSOMATEURS' :
#                         print('Consomateur')
#                         sync_consomateurs( code_sync_log,code_raspberry_status,record_id, operation)
#                     if table_name == 'PACK_TICKET':
#                         print('Pack Ticket')
#                         sync_pack_ticket(record_id,code_raspberry_status)
#
#
#
#         except Exception as e:
#             print("⚠ ERREUR Firebird :", e)
#
#         time.sleep(3)
def loop_sync():
    from config import BORNE
    BORNE1 = BORNE
    print("📡 Boucle principale démarrée")

    while True:
        try:
            # 🔄 Ouvre une nouvelle connexion Firebird à chaque itération
            connect2_fb = connect(database=f"{HOST}/3050:{DB_PATH}",user=USERNAME,password=PASSWORD,)
            fb_curseur = connect2_fb.cursor()

            fb_curseur.execute("""
                SELECT sync_log.CODE_SYNC_LOG,
                       sync_log.TABLE_NAME,
                       sync_log.RECORD_ID,
                       RASPBERRY_STATUT.CODE_RASPBERRY_STATUT,
                       raspberry_statut.OPERATION
                FROM SYNC_LOG
                JOIN raspberry_statut
                    ON sync_log.ID_SYNC_LOG = raspberry_statut.CODE_SYNC_LOG
                WHERE raspberry_statut.ETAT = 'PENDING'
                  AND raspberry_statut.CODE_BORNE = ?
            """, (BORNE1,))

            rows = fb_curseur.fetchall()

            if rows:
                print('rows in raspberry status =', len(rows))
                print("Total consomateurs =", len(rows))

                for row in rows:
                    code_sync_log = row[0]
                    table_name = row[1]
                    record_id = row[2]
                    code_raspberry_status = row[3]
                    operation = row[4]

                    if table_name == 'CONSOMATEURS':
                        print('Consomateur')
                        sync_consomateurs(code_sync_log, code_raspberry_status, record_id, operation)

                    elif table_name == 'PACK_TICKET':
                        print('Pack Ticket')
                        sync_pack_ticket(record_id, code_raspberry_status)

            # 🔒 Très important : commit + fermer la connexion
            connect2_fb.close()

        except Exception as e:
            print("⚠ ERREUR Firebird :", e)

        time.sleep(3)


def start_loop_sync_thread():
    import threading
    t = threading.Thread(target=loop_sync, daemon=True)
    t.start()
    print("🔄 Thread loop_sync lancé")
