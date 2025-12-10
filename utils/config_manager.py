import os
import re
import config as cfg  # Utilise l'alias 'cfg' pour l'accès aux variables


def get_config_for_template():
    """
    Récupère les variables du module config et les organise par catégorie
    pour l'affichage dans le template HTML.
    """
    config_data = {}

    # Itération sur les variables du module config
    for key, value in vars(cfg).items():
        # Filtre les attributs internes de Python (commence par '_')
        if not key.startswith('_') and key not in ['os', 'BASE_DIR', 're']:
            config_data[key] = value

    # Organisation des données par catégories
    categories = {
        "Base de Données": {k: v for k, v in config_data.items() if k in ['DB_FILE']},
        "Périphériques & IP": {k: v for k, v in config_data.items() if k.startswith(('POINTEUSE', 'PRINTER', 'GPIO'))},
        "Modes Fonctionnement": {k: v for k, v in config_data.items() if k.startswith('MODE')},
        "Logs & Utils": {k: v for k, v in config_data.items() if k.endswith(('PATH', 'INTERVAL'))}
    }
    return categories


def update_config_file(data):
    """
    Met à jour le fichier config.py avec les nouvelles données soumises
    via le formulaire web.
    """

    # Utilisation de BASE_DIR de config.py pour garantir le bon chemin
    config_path = os.path.join(cfg.BASE_DIR, "config.py")

    # Lecture du contenu actuel du fichier
    try:
        with open(config_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return False, f"Fichier config.py non trouvé au chemin : {config_path}"

    new_lines = []

    # Expression régulière pour trouver la ligne clé = valeur
    config_pattern = re.compile(r'^(\s*)(\w+)(\s*=\s*)(.*)$')
    print('update config')
    for line in lines:
        match = config_pattern.match(line)

        if match:
            indent, key, equals, value_old = match.groups()

            if key in data:
                new_value = data[key]

                # Tente de convertir en entier ou laisse tel quel
                try:
                    # Si la valeur est un nombre (entier), on la laisse sans guillemets
                    int(new_value)
                    is_string = False
                except ValueError:
                    # Si ce n'est pas un nombre, c'est probablement une chaîne (IP, chemin)
                    is_string = True

                if is_string:
                    # Enveloppe de guillemets doubles
                    line = f'{indent}{key}{equals}"{new_value}"\n'
                else:
                    # Laisse comme un nombre (0, 1, 12, etc.)
                    line = f"{indent}{key}{equals}{new_value}\n"

                del data[key]

        new_lines.append(line)

    # Réécriture du fichier avec les nouvelles valeurs
    try:
        # NOTE : Il est critique d'avoir les permissions d'écriture sur ce fichier pour l'utilisateur qui exécute Flask
        with open(config_path, 'w') as f:
            f.writelines(new_lines)
        return True, "Configuration mise à jour avec succès. REDÉMARRAGE DU SERVICE NÉCESSAIRE."
    except Exception as e:
        return False, f"Erreur d'écriture du fichier : {e}"

def definit_mode_fonctionnement():
    from config import MODE_TICKET,MODE_ABONNEMENT,MODE_S_AB_TICK,MODE_AB_TICK
    if MODE_TICKET == 1 : MODE_FONCTIONNEMENT = 'Mode_Ticket'
    if MODE_ABONNEMENT == 1: MODE_FONCTIONNEMENT = 'Mode_Abonnement'
    if MODE_S_AB_TICK == 1: MODE_FONCTIONNEMENT = 'Mode_S_AB_Tick'
    if MODE_AB_TICK == 1: MODE_FONCTIONNEMENT = 'Mode_Abonnement_Ticket'

    # Détermination du mode de fonctionnement (inchangée)
    # mode_fonctionnement = 'Mode_S_AB_Tick'
    #
    # if MODE_TICKET == 1:
    #     mode_fonctionnement = 'Mode_Ticket'
    # elif MODE_ABONNEMENT == 1:
    #     mode_fonctionnement = 'Mode_Abonnement'
    # elif MODE_AB_TICK == 1:
    #     mode_fonctionnement = 'Mode_AB_Tick'
    return MODE_FONCTIONNEMENT