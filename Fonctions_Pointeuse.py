from zk import ZK, const
import sqlite3


def charge_tous_consomateurs_sur_pointeuse(IP_Pointeuse,DB_FILE) :
    conn = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    cur = conn.cursor()
    print ('Entree fonction charge_tous_consomateurs_sur_pointeuse')
    # Récupération de tous les consomateurs
    cur.execute("SELECT Code_Employe, Nom_Prenom, Num_Carte FROM Consomateurs")
    utilisateurs = cur.fetchall()
    print ('ok1')
    zk = ZK(IP_Pointeuse, port=4370, timeout=5, password=0, force_udp=False, ommit_ping=False)
    try:
        print('ok2')
        device = zk.connect()
        device.disable_device()
        print('ok3')
        # Charger les utilisateurs existants de la pointeuse
        deja = device.get_users()
        print('ok4')
        dict_deja = {int(u.user_id): u for u in deja}

        for code_employe, nom_prenom, num_carte in utilisateurs:
            print('employe =' + nom_prenom)
            if code_employe in dict_deja:
                # Mise à jour si nécessaire
                device.set_user(
                    uid=code_employe,
                    name=nom_prenom,
                    user_id=str(code_employe),
                    card=num_carte
                )
            else:
                # Nouvel utilisateur
                print('code employe =' + str(code_employe))
                if num_carte is None: num_carte = 0
                device.set_user(
                    uid=code_employe,
                    name=nom_prenom,
                    user_id=str(code_employe),
                    card=num_carte
                )

        device.enable_device()
        device.disconnect()
        print("✔ Synchronisation Consomateurs sur pointeuse terminée !")

    except Exception as e:
        print("Erreur :", e)
    return

def envoyer_un_consomateur(ip_pointeuse, code_employe):

    conn = sqlite3.connect("data.db", timeout=10, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("SELECT Code_Employe, Nom_Prenom, Num_Carte FROM Consomateurs WHERE Code_Employe = ?", (code_employe,))
    row = cur.fetchone()

    if not row:
        print("❌ Consomateur introuvable dans la base SQLite.")
        return

    code, nom, carte = row

    zk = ZK(ip_pointeuse, port=4370, timeout=5)

    try:
        device = zk.connect()
        device.disable_device()

        # Vérifier existence
        deja = device.get_users()
        existe = any(int(u.user_id) == code for u in deja)

        device.set_user(
            uid=code,
            name=nom,
            user_id=str(code),
            card=carte
        )

        device.enable_device()
        device.disconnect()

        if existe:
            print("✔ Utilisateur mis à jour sur la pointeuse.")
        else:
            print("✔ Nouvel utilisateur envoyé à la pointeuse.")

    except Exception as e:
        print("Erreur :", e)