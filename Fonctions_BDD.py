import sqlite3

from zk import ZK

DB_FILE = "raspberry_data.db"

def charger_configuration():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT NUMERO_BORNE, NOM_SOCIETE,GPIO_TOURNIQUET,POINTEUSE,IP_POINTEUSE,GPIO1,GPIO2 FROM Configuration LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "numero_borne": result[0],
            "nom_societe": result[1],
            "gpio_tourniquet": result[2],
            "pointeuse": result[3],
            "Ip_Pointeuse":result[4],
            "Gpio1":result[5],
            "Gpio2":result[6]
        }
    else:
        return {
            "numero_borne": None,
            "nom_societe": None
        }



def get_users_page(per_page, offset):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, Code_Utilisateur, Nom_Prenom, Nombre_Tickets
        FROM Utilisateurs
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    users = cur.fetchall()
    conn.close()
    return users

def get_total_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Utilisateurs")
    total_users = cur.fetchone()[0]
    conn.close()
    return total_users

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
        config = charger_configuration()
        Ip_Pointeuse = config.get("Ip_Pointeuse", "Pointeuse")

        vider_pointeuse(ip=Ip_Pointeuse, port=4370)
    except Exception as e:
        print(f"❌ Erreur lors de la suppression : {e}")



from zk import ZK


def vider_pointeuse(ip, port=4370):
    config = charger_configuration()
    Ip_Pointeuse = config.get("Ip_Pointeuse", "Pointeuse")

    zk = ZK(Ip_Pointeuse, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
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


def Ajouter_Utilisateur_SQLITE(Code_Utilisateur: int, Nom_Prenom: str):

    try:
        conn_sqlite = sqlite3.connect(DB_FILE)
        cur = conn_sqlite.cursor()

        # Vérifier si l'utilisateur existe déjà
        cur.execute("SELECT Nom_Prenom FROM Utilisateurs WHERE Code_Utilisateur = ?", (Code_Utilisateur,))
        row = cur.fetchone()

        if row is None:
            # Utilisateur n’existe pas → on l’ajoute
            cur.execute("""
                INSERT INTO Utilisateurs (Code_Utilisateur, Nom_Prenom, Nombre_Tickets)
                VALUES (?, ?, ?)
            """, (Code_Utilisateur, Nom_Prenom, 1))

            conn_sqlite.commit()
            print(f"✔️ Ajouté : {Code_Utilisateur} - {Nom_Prenom}")

        else:
            # Utilisateur existe → on met à jour seulement si le nom a changé
            old_name = row[0]
            if old_name != Nom_Prenom:
                cur.execute("""
                    UPDATE Utilisateurs
                    SET Nom_Prenom = ?
                    WHERE Code_Utilisateur = ?
                """, (Nom_Prenom, Code_Utilisateur))

                conn_sqlite.commit()
                print(f"🔄 Nom mis à jour : {Code_Utilisateur} — {old_name} → {Nom_Prenom}")
            else:
                print(f"➡️ Déjà à jour : {Code_Utilisateur} - {Nom_Prenom}")

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
        Nombre_Tickets INTEGER NOT NULL,Abonnement_Actif INTEGER NOT NULL,
        Multi_Repas INTEGER,
        Num_Carte TEXT )""")

    # cur.execute("""
    #
    # CREATE TABLE IF NOT EXISTS Configuration (NUMERO_BORNE INTEGER NOT NULL,NOM_SOCIETE TEXT NOT NULL,
    # GPIO_TOURNIQUET INTEGER,POINTEUSE INTEGER,LECTEUR_WIEGAND INTEGER) """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Consomation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_utilisateur INTEGER NOT NULL,
        TYPE_REPAS INTEGER NOT NULL,
        Nbr_repas INTEGER NOT NULL,
        Jour_annee INTEGER NOT NULL,Annee_Consomation INTEGER NOT NULL,NUMERO_BORNE INTEGER,
        Date_Consomation TEXT NOT NULL,TYPE_REPAS_STR TEXT ) """)

    cur.execute("""CREATE TABLE IF NOT EXISTS Configuration (
    NUMERO_BORNE INTEGER NOT NULL,
    NOM_SOCIETE TEXT NOT NULL,
    POINTEUSE INTEGER,         -- 1 = activé, 0 = désactivé
    IP_POINTEUSE TEXT,         -- Adresse IP pointeuse si activée
    LECTEUR_WIEGAND INTEGER,   -- 1 = activé, 0 = désactivé
    GPIO1 INTEGER,             -- GPIO Lecteur 1
    GPIO2 INTEGER,             -- GPIO Lecteur 2
    TOURNIQUET INTEGER,        -- 1 = activé, 0 = désactivé
    GPIO_TOURNIQUET INTEGER    )""")
    print("indice1")
    conn.commit()
    conn.close()
    print("✅ Table 'donnees' créée ou déjà existante.")
    return True
  except Exception as e:
      print(f"❌ Erreur dans init_db(): {e}")
  return False
