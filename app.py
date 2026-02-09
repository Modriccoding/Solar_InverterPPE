from flask import Flask, render_template, jsonify, request
import subprocess
import sys
import datetime

app = Flask(__name__)

# --- MÉMOIRE GLOBALE ---
flotte_data = {}          
active_processes = []     
# Limites par défaut (Grid Code)
global_limits = {"w": 4000, "v": 250} 
# Météo par défaut (1.0 = 100% Soleil, 0.5 = Nuageux, 0.0 = Nuit)
weather_factor = 1.0 
attack_mode = False       

@app.route('/')
def index():
    return render_template('dashboard.html')

# --- API MÉTÉO (Nouvelle !) ---
@app.route('/api/weather/set', methods=['POST'])
def set_weather():
    global weather_factor
    data = request.json
    weather_factor = float(data.get('factor', 1.0))
    return jsonify({"status": "ok", "current_factor": weather_factor})

# --- API CONTRÔLE (Spawn/Kill) ---
@app.route('/api/control/spawn', methods=['POST'])
def spawn_inverters():
    count = int(request.json.get('count', 1))
    for i in range(count):
        inverter_id = f"INV-{len(active_processes) + 1 + i:03d}"
        # On passe le weather_factor au démarrage (optionnel)
        proc = subprocess.Popen([sys.executable, 'onduleur_v2.py', inverter_id])
        active_processes.append(proc)
    return jsonify({"status": "ok", "msg": f"{count} onduleurs démarrés"})

@app.route('/api/control/kill', methods=['POST'])
def kill_all():
    global active_processes
    for proc in active_processes:
        proc.terminate()
    active_processes = []
    flotte_data.clear()
    return jsonify({"status": "ok", "msg": "Arrêt d'urgence effectué"})

# --- API RÉGLAGES ---
@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    global global_limits
    data = request.json
    global_limits['w'] = int(data.get('limit_w', global_limits['w']))
    global_limits['v'] = int(data.get('limit_v', global_limits['v']))
    return jsonify({"status": "updated", "current": global_limits})

# --- API TÉLÉMÉTRIE (Le cœur de la simulation) ---
@app.route('/api/telemetry', methods=['POST'])
def telemetry():
    data = request.json
    inv_id = data['id']
    
    # Stockage
    flotte_data[inv_id] = data
    flotte_data[inv_id]['last_seen'] = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Réponse du serveur vers l'onduleur
    response = {
        "command": "CONTINUE",
        "new_limit_w": global_limits['w'],
        "new_limit_v": global_limits['v'],
        "weather_factor": weather_factor  # <--- On envoie la météo à l'onduleur
    }
    
    if attack_mode:
        response["command"] = "SHUTDOWN"

    return jsonify(response)

@app.route('/api/data')
def get_data():
    return jsonify({
        "inverters": flotte_data,
        "global_limits": global_limits,
        "active_count": len(active_processes),
        "weather_factor": weather_factor
    })

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000)
    finally:
        for proc in active_processes:
            proc.terminate()
