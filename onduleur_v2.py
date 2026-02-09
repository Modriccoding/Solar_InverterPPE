import requests
import time
import random
import sys

# Configuration
SERVER_URL = "http://localhost:5000/api/telemetry"
MY_ID = sys.argv[1] if len(sys.argv) > 1 else "INV-TEST"

# Valeurs par défaut
LIMIT_W = 4000
LIMIT_V = 250
WEATHER_FACTOR = 1.0 # Au démarrage, on suppose qu'il fait beau

print(f"--- Démarrage Onduleur {MY_ID} ---")

while True:
    try:
        # 1. Calcul de la PUISSANCE SOLAIRE (Ce que le panneau PEUT fournir)
        # Capacité max théorique du panneau (ex: 3800W max)
        panneau_capacity = random.uniform(3500, 3800)
        
        # Puissance disponible selon la météo
        available_power = panneau_capacity * WEATHER_FACTOR
        
        # Ajout d'un peu de bruit (nuages passagers, vent...)
        noise = random.uniform(-20, 20)
        available_power += noise
        if available_power < 0: available_power = 0

        # 2. Application de la LIMITATION (Ce que l'onduleur A LE DROIT d'injecter)
        # C'est le "Clipping"
        if available_power > LIMIT_W:
            final_power = LIMIT_W
            # Si on produit plus que la limite, on sature (État Jaune)
            status = "SATURATION" 
        else:
            final_power = available_power
            status = "NORMAL"

        # 3. Simulation Voltage (Un peu aléatoire + monte si on produit beaucoup)
        base_voltage = 230
        voltage_rise = (final_power / 4000) * 10 # Le voltage monte avec la charge
        final_voltage = base_voltage + voltage_rise + random.uniform(-1, 1)

        # Vérification surtension
        if final_voltage > LIMIT_V:
            status = "CRITICAL"

        # Si pas de soleil (Nuit)
        if final_power < 50:
            status = "SLEEP"

        # 4. Envoi
        payload = {
            "id": MY_ID,
            "power": round(final_power, 2),
            "voltage": round(final_voltage, 2),
            "status": status,
            "config_limit_w": LIMIT_W
        }

        response = requests.post(SERVER_URL, json=payload, timeout=2).json()

        # 5. Mise à jour des consignes reçues
        if "new_limit_w" in response: LIMIT_W = response["new_limit_w"]
        if "new_limit_v" in response: LIMIT_V = response["new_limit_v"]
        if "weather_factor" in response: WEATHER_FACTOR = response["weather_factor"] # <--- Mise à jour météo
            
        if response.get("command") == "SHUTDOWN":
            status = "OFFLINE" # Juste pour l'affichage local

        # print(f"[{MY_ID}] Météo:{WEATHER_FACTOR} | Dispo:{int(available_power)}W | Injecté:{int(final_power)}W | {status}")

    except Exception as e:
        print(f"Erreur: {e}")
    
    time.sleep(1.0)
