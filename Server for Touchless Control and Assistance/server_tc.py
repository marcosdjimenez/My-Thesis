import cv2
import numpy as np
from flask import Flask, request, jsonify
import os
import threading
import signal
import sys
import time
from datetime import datetime
import pygame  # Per feedback auditivo
import subprocess  # Per afplay su macOS

app = Flask(__name__)

# ====== Percorsi/Config ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'server_log.txt')
WINDOW_TITLE = 'Notifiche Pazienti'
BASE_WIDTH = 1280  # Aumentato per Retina
BASE_HEIGHT = 960

# ====== Stato condiviso ======
alerts = []
lock = threading.Lock()
running = True

# ====== Inizializzazione audio ======
try:
    pygame.mixer.init()
    print("pygame.mixer inizializzato correttamente")
except Exception as e:
    print(f"Errore inizializzazione pygame.mixer: {e}")

# File audio (opzionale)
SOUND_NORMAL = os.path.join(BASE_DIR, 'beep.wav')  # File per notifiche standard
SOUND_URGENT = os.path.join(BASE_DIR, 'urgent.wav')  # File per assistenza urgente

# Funzione per generare un beep sintetico
def play_synthetic_beep(frequency=1000, duration=500):
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * duration / 1000)
        t = np.linspace(0, duration / 1000, n_samples, False)
        wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        sound = np.array([32767 * wave], dtype=np.int16).T
        sound_obj = pygame.sndarray.make_sound(sound)
        sound_obj.play()
        print(f"Beep sintetico riprodotto: {frequency} Hz, {duration} ms")
    except Exception as e:
        print(f"Errore beep sintetico: {e}")
        # Fallback con afplay
        try:
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'])
            print("Beep di fallback (afplay) riprodotto")
        except Exception as e:
            print(f"Errore afplay: {e}")

def play_alert_sound(action):
    try:
        if action == 'urgent_assistance':
            if os.path.exists(SOUND_URGENT):
                pygame.mixer.Sound(SOUND_URGENT).play()
                print(f"Suono urgente riprodotto: {SOUND_URGENT}")
            else:
                play_synthetic_beep(frequency=1500, duration=1000)
        else:
            if os.path.exists(SOUND_NORMAL):
                pygame.mixer.Sound(SOUND_NORMAL).play()
                print(f"Suono standard riprodotto: {SOUND_NORMAL}")
            else:
                play_synthetic_beep(frequency=1000, duration=500)
    except Exception as e:
        print(f"Errore riproduzione suono: {e}")
        try:
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'])
            print("Beep di fallback (afplay) riprodotto")
        except Exception as e:
            print(f"Errore afplay: {e}")

def log_alert(alert):
    formatted_time = datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{formatted_time}: {alert['action']} - Device: {alert['device_id']} - Location: {alert['location']}\n")
        print(f"Log salvato: {formatted_time}, {alert['action']}")
    except Exception as e:
        print(f"Errore scrittura log: {e}")

def render_alerts(window_size):
    width, height = window_size
    print(f"Dimensioni finestra rilevate: {width}x{height}")  # Debug
    # Calcola fattore di scala
    scale = min(width / BASE_WIDTH, height / BASE_HEIGHT)
    scaled_width = int(BASE_WIDTH * scale)
    scaled_height = int(BASE_HEIGHT * scale)

    # Margine di sicurezza e dimensioni minime
    margin = int(20 * scale)
    scaled_width = max(scaled_width, 200)
    scaled_height = max(scaled_height, 200)

    # Crea immagine con dimensioni scalate
    img = np.zeros((scaled_height, scaled_width, 3), dtype=np.uint8)
    # Aggiungi bordo per debug visivo
    cv2.rectangle(img, (0, 0), (scaled_width-1, scaled_height-1), (255, 255, 255), 1)
    print(f"Immagine renderizzata: {scaled_width}x{scaled_height}, scala: {scale}")  # Debug

    if not alerts:
        # Testo "Nessuna notifica" centrato
        text = "Nessuna notifica"
        font_scale = 1.0 * scale  # Aumentato per leggibilità
        thickness = max(2, int(3 * scale))  # Spessore maggiore
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (scaled_width - text_size[0]) // 2
        text_y = (scaled_height + text_size[1]) // 2
        cv2.putText(img, text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
        print("Rendering: Nessuna notifica")
        return img

    # Rendering degli alert
    y = int(60 * scale)  # Margine superiore maggiore
    for alert in alerts[-5:]:
        action_text = {
            'request_water': 'Richiesta Acqua',
            'report_pain': 'Segnalazione Dolore',
            'urgent_assistance': 'Assistenza Urgente'
        }.get(alert['action'], 'Azione Sconosciuta')
        text = f"{alert['formatted_time']} - {action_text} - {alert['device_id']} @ {alert['location']}"
        font_scale = 0.8 * scale  # Aumentato per leggibilità
        thickness = max(1, int(2 * scale))
        cv2.putText(img, text, (margin, y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        y += int(50 * scale)
        print(f"Rendering alert: {text}")
    return img

@app.route('/status', methods=['GET'])
def status():
    with lock:
        print(f"Status richiesto: {len(alerts)} alert")
        return jsonify({
            'alert_count': len(alerts),
            'recent_alerts': alerts[-5:]
        })

@app.route('/command', methods=['POST', 'GET'])
def handle_command():
    if request.method == 'POST' and request.json:
        data = request.json
    else:
        data = request.args.to_dict()

    print(f"Richiesta ricevuta: {data}")
    action = data.get('action')
    if not action:
        print("Errore: action mancante")
        return jsonify({'status': 'error', 'message': 'missing action'}), 400

    required_fields = ['device_id', 'location', 'timestamp']
    if any(field not in data for field in required_fields):
        print(f"Errore: campi mancanti {required_fields}")
        return jsonify({'status': 'error', 'message': 'missing fields'}), 400

    try:
        timestamp = float(data['timestamp'])
    except ValueError:
        print("Errore: timestamp non valido")
        return jsonify({'status': 'error', 'message': 'invalid timestamp'}), 400

    with lock:
        if action not in ['request_water', 'report_pain', 'urgent_assistance']:
            print(f"Errore: azione sconosciuta {action}")
            return jsonify({'status': 'error', 'message': 'unknown action'}), 400

        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        alert = {
            'action': action,
            'device_id': data['device_id'],
            'location': data['location'],
            'timestamp': timestamp,
            'formatted_time': formatted_time
        }
        alerts.append(alert)
        log_alert(alert)
        play_alert_sound(action)
        print(f"[ALERT] {action} | Device: {alert['device_id']} | Location: {alert['location']} | Time: {formatted_time}")
        return jsonify({'status': 'success', 'action': action, 'received': alert})

def run_flask():
    print("Avvio server Flask su 0.0.0.0:5050")
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)

def main():
    global running
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Log delle notifiche\n")

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Crea finestra ridimensionabile
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, BASE_WIDTH, BASE_HEIGHT)
    print("Finestra OpenCV avviata (ridimensionabile)")

    while running:
        with lock:
            try:
                # Ottieni dimensioni finestra
                window_size = cv2.getWindowImageRect(WINDOW_TITLE)[2:4]
                if window_size[0] <= 0 or window_size[1] <= 0:
                    window_size = (BASE_WIDTH, BASE_HEIGHT)
            except Exception as e:
                print(f"Errore getWindowImageRect: {e}")
                window_size = (BASE_WIDTH, BASE_HEIGHT)
            frame = render_alerts(window_size)
        cv2.imshow(WINDOW_TITLE, frame)
        k = cv2.waitKey(30) & 0xFF
        if k == ord('q'):
            running = False
            break

    cv2.destroyAllWindows()
    try:
        pygame.mixer.quit()
    except:
        pass

def handle_sigint(sig, frame):
    global running
    running = False

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_sigint)
    try:
        main()
    except Exception as e:
        print(f"Fatal: {e}")
        try:
            cv2.destroyAllWindows()
            pygame.mixer.quit()
        except:
            pass
        sys.exit(1)
