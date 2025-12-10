import sqlite3

from zk import ZK
DB_FILE = "raspberry_data.db"
from zk import ZK
import config as cfg  # On importe le fichier config.py



def charger_configuration_from_py():
        # Les valeurs sont directement lues depuis le module config.py (importé comme cfg)

        # Récupérer les valeurs (Nous devons ajouter 'numero_borne' et 'nom_societe'
        # soit dans config.py, soit les simuler pour que la fonction soit complète)

        # --- Simuler les valeurs manquantes pour la cohérence ---
        # Ces variables devraient idéalement être ajoutées à votre config.py
        numero_borne = 1
        nom_societe = "Ma Société"
        # --------------------------------------------------------

        gpio_tourniquet = cfg.GPIO_TOURNIQUET
        Gpio1 = cfg.GPIO1
        Gpio2 = cfg.GPIO2

        # L'ancienne config.ini avait une valeur 'pointeuse' (0 ou 1 ?),
        # nous la simulerons ou la fixerons à 1 si la pointeuse est configurée.
        pointeuse = 1
        Ip_Pointeuse = cfg.POINTEUSE_IP  # Utiliser POINTEUSE_IP de config.py

        Mode_Ticket = cfg.MODE_TICKET
        Mode_Abonnement = cfg.MODE_ABONNEMENT
        Mode_AB_Tick = cfg.MODE_AB_TICK
        Mode_S_AB_TICK = cfg.MODE_S_AB_TICK
        DB_FILE = cfg.DB_FILE
        # Affichage pour vérification
        print("Borne:", numero_borne)
        print("Société:", nom_societe)
        print("GPIO Tourniquet:", gpio_tourniquet)
        print("Gpio1:", Gpio1, "Gpio2:", Gpio2)
        print("Pointeuse:", pointeuse, "IP:", Ip_Pointeuse)
        print("Modes de fonctionnement:",
              f"Ticket={Mode_Ticket}, Abonnement={Mode_Abonnement}, S_AB_Tick={Mode_S_AB_TICK}, AB_Tick={Mode_AB_Tick}")

        # Le bloc if/else n'est plus nécessaire car l'importation de config.py
        # réussira si le fichier existe et est syntaxiquement correct.
        return {
            "numero_borne": numero_borne,
            "nom_societe": nom_societe,
            "gpio_tourniquet": gpio_tourniquet,
            "pointeuse": pointeuse,
            "Ip_Pointeuse": Ip_Pointeuse,
            "Gpio1": Gpio1,
            "Gpio2": Gpio2,
            "Mode_Ticket": Mode_Ticket,
            "Mode_Abonnement": Mode_Abonnement,
            "Mode_S_AB_Tick": Mode_S_AB_TICK,
            "Mode_AB_Tick": Mode_AB_Tick,
            "DB_FILE": DB_FILE
        }


    # Si vous voulez garder le nom de fonction original, renommez simplement la nouvelle.



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

def Ajouter_Consumation_SQLITE(id_utilisateur, Nbr_repas, TYPE_REPAS, Jour_annex,
                                   Anne_consummation: int, Date_Consumation):
        global conn_sqlite
        try:
            print("debut consomation sqlite")
            config = charger_configuration_from_py()
            numero_borne = config["numero_borne"]
            DB_FILE = config["DB_FILE"]
            print('DB_FILE =' + DB_FILE)
            conn_sqlite = sqlite3.connect(DB_FILE)
            cur = conn_sqlite.cursor()
            cur.execute("""
                INSERT INTO Consomation (id_utilisateur, Nbr_repas, TYPE_REPAS,
                                         Jour_annee, Annee_consomation, Date_Consomation, NUMERO_BORNE)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (id_utilisateur, Nbr_repas, TYPE_REPAS,
                  Jour_annex, Anne_consummation, Date_Consumation, numero_borne))

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


def Ajouter_CONSOMATEUR_SQLITE(Code_Employe: int, Nom_Prenom: str):

        try:
            conn_sqlite = sqlite3.connect(DB_FILE)
            cur = conn_sqlite.cursor()

            # Vérifier si l'utilisateur existe déjà
            cur.execute("SELECT Nom_Prenom FROM Consomateurs WHERE Code_Employe = ?", (Code_Employe,))
            row = cur.fetchone()

            if row is None:
                # Utilisateur n’existe pas → on l’ajoute
                cur.execute("""
                    INSERT INTO Consomateurs (Code_Employe, Nom_Prenom, Nombre_Tickets)
                    VALUES (?, ?, ?)
                """, (Code_Employe, Nom_Prenom, 1))

                conn_sqlite.commit()
                print(f"✔️ Ajouté : {Code_Employe} - {Nom_Prenom}")

            else:
                # Utilisateur existe → on met à jour seulement si le nom a changé
                old_name = row[0]
                if old_name != Nom_Prenom:
                    cur.execute("""
                        UPDATE Consomateurs
                        SET Nom_Prenom = ?
                        WHERE Code_Utilisateur = ?
                    """, (Nom_Prenom, Code_Employe))

                    conn_sqlite.commit()
                    print(f"🔄 Nom mis à jour : {Code_Employe} — {old_name} → {Nom_Prenom}")
                else:
                    print(f"➡️ Déjà à jour : {Code_Employe} - {Nom_Prenom}")

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Consomateurs (id_Consomateur INTEGER PRIMARY KEY AUTOINCREMENT,
                        Code_Employe INTEGER UNIQUE, Nom_Prenom TEXT NOT NULL, Nombre_Tickets INTEGER NOT NULL DEFAULT 0,
                        Abonnement_Actif INTEGER NOT NULL DEFAULT 0, Multi_Repas INTEGER DEFAULT 0, Num_Carte TEXT)""")



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
