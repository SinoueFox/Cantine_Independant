import subprocess
import time
import sys

# --- Paramètres du hotspot ---
HOTSPOT_NAME = "Raspberry_Hotspot"
HOTSPOT_PASSWORD = "12345678"
INTERFACE = "wlan0"  # adapte si ton interface Wi-Fi a un autre nom (ex: wlan1)

def run_cmd(cmd):
    """Exécute une commande shell et affiche le résultat."""
    print(f"▶️ {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur : {e.stderr.strip()}")
        return None

def hotspot_exists():
    """Vérifie si un hotspot existe déjà."""
    result = run_cmd("nmcli connection show")
    return HOTSPOT_NAME in (result or "")

def start_hotspot():
    """Crée et démarre le hotspot Wi-Fi."""
    print("🚀 Démarrage du hotspot Wi-Fi...")

    # Arrêter d’éventuelles connexions actives sur wlan0
    run_cmd(f"nmcli device disconnect {INTERFACE}")

    if not hotspot_exists():
        # Créer un nouveau point d’accès
        run_cmd(
            f"nmcli device wifi hotspot ifname {INTERFACE} con-name {HOTSPOT_NAME} "
            f"ssid {HOTSPOT_NAME} password {HOTSPOT_PASSWORD}"
        )
    else:
        # Si déjà existant, juste le démarrer
        run_cmd(f"nmcli connection up {HOTSPOT_NAME}")

    print("✅ Hotspot Wi-Fi actif !")
    print(f"📶 SSID : {HOTSPOT_NAME}")
    print(f"🔑 Mot de passe : {HOTSPOT_PASSWORD}")

def check_networkmanager():
    """Vérifie que NetworkManager est installé et actif."""
    status = run_cmd("systemctl is-active NetworkManager")
    if status != "active":
        print("❌ NetworkManager n'est pas actif. Essaie : sudo systemctl start NetworkManager")
        sys.exit(1)

if __name__ == "__main__":
    check_networkmanager()
    start_hotspot()
    print("⏳ Attente de stabilisation du réseau...")
    time.sleep(5)


