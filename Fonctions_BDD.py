import sqlite3

from zk import ZK

DB_FILE = "raspberry_data.db"

def charger_configuration():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT NUMERO_BORNE, NOM_SOCIETE FROM Configuration LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "numero_borne": result[0],
            "nom_societe": result[1]
        }
    else:
        return {
            "numero_borne": None,
            "nom_societe": None
        }

# def Ajouter_Consomation_SQLITE(id_utilisateur, Nbr_repas, TYPE_REPAS, Jour_annee,Annee_consomation: int,
#                                Date_Consomation,TYPE_REPAS_STR: str):
#     try:
#         config = charger_configuration()
#         numero_borne = config["numero_borne"]
#
#         print("passage3")
#         print(TYPE_REPAS)
#         conn_sqlite = sqlite3.connect(DB_FILE)
#         cur = conn_sqlite.cursor()
#         cur.execute("""
#                     INSERT INTO Consomation (id_utilisateur, Nbr_repas, TYPE_REPAS,
#                                              Jour_annee,Annee_consomation,Date_Consomation,TYPE_REPAS_STR,NUMERO_BORNE)
#                     VALUES (?, ?, ?, ?, ?,?,?,?)
#                     """, (id_utilisateur, 1, TYPE_REPAS,
#                           Jour_annee,Annee_consomation,Date_Consomation,TYPE_REPAS_STR,numero_borne))  # Corrigé: TYPE_REPAS et Date_Consomation étaient des valeurs fixes
#         # envoie la consomation sur la firebird
#
#         conn_sqlite.commit()
#
#         if cur.rowcount > 0:
#             # Note: nb_repas n'est pas défini ici, cette ligne pourrait causer une erreur.
#             # Si nb_repas est le nombre de repas de l'utilisateur, il doit être récupéré avant.
#             # print(f"Nbr Repas update OK : {nb_repas - 1}")
#             print("Consommation ajoutée avec succès à SQLite.")
#         else:
#             print("⚠️ Aucun enregistrement modifié (Num_Carte non trouvé ?)")
#
#     except sqlite3.Error as e:
#         print(f"❌ Erreur SQLite : {e}")
#
#     finally:
#         conn_sqlite.close()
def Ajouter_Consomation_SQLITE(id_utilisateur, Nbr_repas, TYPE_REPAS, Jour_annee,
                               Annee_consomation: int, Date_Consomation, TYPE_REPAS_STR: str):
    try:
        print("debut consomation sqlite")
        config = charger_configuration()
        numero_borne = config["numero_borne"]

        conn_sqlite = sqlite3.connect(DB_FILE)
        cur = conn_sqlite.cursor()
        cur.execute("""
            INSERT INTO Consomation (id_utilisateur, Nbr_repas, TYPE_REPAS,
                                     Jour_annee, Annee_consomation, Date_Consomation, TYPE_REPAS_STR, NUMERO_BORNE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_utilisateur, Nbr_repas, TYPE_REPAS,
              Jour_annee, Annee_consomation, Date_Consomation, TYPE_REPAS_STR, numero_borne))

        conn_sqlite.commit()

        print("✅ Consommation ajoutée avec succès à SQLite.")

    except sqlite3.Error as e:
        print(f"❌ Erreur SQLite : {e}")

    finally:
        conn_sqlite.close()


def Vider_base():
    import sqlite3
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        # Suppression du contenu des tables
        cur.execute("DELETE FROM Consomation")
        cur.execute("DELETE FROM Utilisateurs")

        # Réinitialisation des compteurs AUTOINCREMENT (optionnel mais recommandé)
        cur.execute("DELETE FROM sqlite_sequence WHERE name='Consomation'")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='Utilisateurs'")

        conn.commit()
        conn.close()
        print("✅ Base de données vidée avec succès.")
        vider_pointeuse(ip="192.168.100.201", port=4370)
    except Exception as e:
        print(f"❌ Erreur lors de la suppression : {e}")


# def vider_pointeuse(ip="192.168.100.201", port=4370):
#     zk = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
#     try:
#         print("🔗 Connexion à la pointeuse...")
#         conn = zk.connect()
#         conn.disable_device()
#
#         print("🗑️ Suppression de toutes les données (utilisateurs, empreintes, logs)...")
#         conn.clear_data()  # Efface TOUT
#
#         conn.enable_device()
#         conn.disconnect()
#         print("✅ Pointeuse vidée avec succès.")
#     except Exception as e:
#         print(f"❌ Erreur : {e}")
from zk import ZK


def vider_pointeuse(ip="192.168.100.201", port=4370):
    zk = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
    try:
        print("🔗 Connexion à la pointeuse...")
        conn = zk.connect()
        conn.disable_device()

        # 1️⃣ Suppression des logs
        try:
            print("🗑️ Suppression des logs...")
            conn.clear_attendance()
        except Exception as e:
            print(f"⚠️ Impossible de supprimer les logs : {e}")

        # 2️⃣ Suppression des utilisateurs et de leurs empreintes
        try:
            print("🗑️ Suppression des utilisateurs et empreintes...")
            users = conn.get_users()
            for user in users:
                uid = user.uid
                # Suppression des empreintes
                try:
                    # On essaie pour les 10 doigts (de 0 à 9)
                    for finger in range(0, 10):
                        conn.delete_user_template(uid, finger)
                except:
                    pass

                # Suppression de l'utilisateur
                try:
                    conn.delete_user(uid)
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Impossible de récupérer ou supprimer les utilisateurs : {e}")

        conn.enable_device()
        conn.disconnect()
        print("✅ Pointeuse vidée avec succès (méthodes séparées).")
    except Exception as e:
        print(f"❌ Erreur : {e}")


def Ajouter_Utilisateur_SQLITE(Code_Utilisateur : int,Nom_Prenom : str):
    try:
        print("passage3")
        conn_sqlite = sqlite3.connect(DB_FILE)
        cur = conn_sqlite.cursor()
        cur.execute("""
                    INSERT INTO Utilisateurs (Code_Utilisateur, Nom_Prenom,Nombre_Repas)
                    VALUES (?, ?, ?)
                    """, (Code_Utilisateur, Nom_Prenom,1))
        conn_sqlite.commit()

        if cur.rowcount > 0:
            # Note: nb_repas n'est pas défini ici, cette ligne pourrait causer une erreur.
            # Si nb_repas est le nombre de repas de l'utilisateur, il doit être récupéré avant.
            # print(f"Nbr Repas update OK : {nb_repas - 1}")
            print("Utilisateur ajoutée avec succès à SQLite.")
        else:
            print("⚠️ Aucun enregistrement modifié (Num_Carte non trouvé ?)")

    except sqlite3.Error as e:
        print(f"❌ Erreur SQLite : {e}")

    finally:
        conn_sqlite.close()

def init_db():
  print ("BAse de donnee cree")
  try:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,Code_Utilisateur INTEGER UNIQUE,
        Nom_Prenom TEXT NOT NULL,
        Nombre_Repas INTEGER NOT NULL,
        Num_Carte TEXT )""")
    cur.execute("""
    
    CREATE TABLE IF NOT EXISTS Configuration (NUMERO_BORNE INTEGER NOT NULL,NOM_SOCIETE TEXT NOT NULL)""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Consomation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_utilisateur INTEGER NOT NULL,
        TYPE_REPAS INTEGER NOT NULL,
        Nbr_repas INTEGER NOT NULL,
        Jour_annee INTEGER NOT NULL,Annee_Consomation INTEGER NOT NULL,NUMERO_BORNE INTEGER,
        Date_Consomation TEXT NOT NULL,TYPE_REPAS_STR TEXT ) """)
    print("indice1")
    conn.commit()
    conn.close()
    print("✅ Table 'donnees' créée ou déjà existante.")
    return True
  except Exception as e:
      print(f"❌ Erreur dans init_db(): {e}")
  return False
