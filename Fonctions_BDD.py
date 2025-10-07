import sqlite3
DB_FILE = "raspberry_data.db"

def Ajouter_Consomation_SQLITE(id_utilisateur, Nbr_repas, TYPE_REPAS, Jour_annee,Annee_consomation: int,
                               Date_Consomation,TYPE_REPAS_STR: str):
    try:
        print("passage3")
        print(TYPE_REPAS)
        conn_sqlite = sqlite3.connect(DB_FILE)
        cur = conn_sqlite.cursor()
        cur.execute("""
                    INSERT INTO Consomation (id_utilisateur, Nbr_repas, TYPE_REPAS,
                                             Jour_annee,Annee_consomation,Date_Consomation,TYPE_REPAS_STR)
                    VALUES (?, ?, ?, ?, ?,?,?)
                    """, (id_utilisateur, 1, TYPE_REPAS,
                          Jour_annee,Annee_consomation,Date_Consomation,TYPE_REPAS_STR))  # Corrigé: TYPE_REPAS et Date_Consomation étaient des valeurs fixes
        # envoie la consomation sur la firebird

        conn_sqlite.commit()

        if cur.rowcount > 0:
            # Note: nb_repas n'est pas défini ici, cette ligne pourrait causer une erreur.
            # Si nb_repas est le nombre de repas de l'utilisateur, il doit être récupéré avant.
            # print(f"Nbr Repas update OK : {nb_repas - 1}")
            print("Consommation ajoutée avec succès à SQLite.")
        else:
            print("⚠️ Aucun enregistrement modifié (Num_Carte non trouvé ?)")

    except sqlite3.Error as e:
        print(f"❌ Erreur SQLite : {e}")

    finally:
        conn_sqlite.close()

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
    CREATE TABLE IF NOT EXISTS Consomation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_utilisateur INTEGER NOT NULL,
        TYPE_REPAS INTEGER NOT NULL,
        Nbr_repas INTEGER NOT NULL,
        Jour_annee INTEGER NOT NULL,Annee_Consomation INTEGER NOT NULL,
        Date_Consomation TEXT NOT NULL,TYPE_REPAS_STR TEXT ) """)
    print("indice1")
    conn.commit()
    conn.close()
    print("✅ Table 'donnees' créée ou déjà existante.")
    return True
  except Exception as e:
      print(f"❌ Erreur dans init_db(): {e}")
  return False
