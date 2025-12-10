import sqlite3
from config import DB_FILE

def get_db():
    print('DB File' + DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Création tables si elles n'existent pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Code_Utilisateur TEXT UNIQUE,
            Nom_Prenom TEXT,
            Nombre_Tickets INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Configuration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            NUMERO_BORNE INTEGER,
            NOM_SOCIETE TEXT,
            TOURNIQUET INTEGER,
            GPIO_TOURNIQUET INTEGER,
            LECTEUR_WIEGAND INTEGER,
            GPIO1 INTEGER,
            GPIO2 INTEGER,
            POINTEUSE INTEGER,
            IP_POINTEUSE TEXT
        )
    """)
    conn.commit()
    conn.close()
