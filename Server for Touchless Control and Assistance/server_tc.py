# Importazione delle librerie necessarie
import cv2  # OpenCV per la gestione della GUI e rendering delle immagini
import numpy as np  # NumPy per operazioni su array, usato per creare immagini vuote
from flask import Flask, request, jsonify  # Flask per creare un server web API
import os  # Per operazioni sul file system (es. gestione cartelle e file)
import threading  # Per gestire thread paralleli (es. server Flask e GUI OpenCV)
import signal  # Per gestire segnali di sistema (es. SIGINT per Ctrl+C)
import sys  # Per operazioni di sistema (es. uscita dal programma)
import time  # Non usato esplicitamente, ma importato per possibili estensioni
from datetime import datetime  # Per formattare i timestamp degli alert
import pygame  # Per la gestione di feedback audio (riproduzione suoni)
import subprocess  # Per eseguire comandi di sistema (es. afplay su macOS)

# Creazione dell'istanza dell'applicazione Flask
app = Flask(__name__)

# ====== Percorsi/Config ======
# Definizione delle configurazioni di base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory assoluta del file corrente
LOG_FILE = os.path.join(BASE_DIR, 'server_log.txt')  # Percorso del file di log per registrare gli alert
WINDOW_TITLE = 'Notifiche Pazienti'  # Titolo della finestra OpenCV
BASE_WIDTH = 1280  # Larghezza di base della finestra (ottimizzata per display Retina)
BASE_HEIGHT = 960  # Altezza di base della finestra

# ====== Stato condiviso ======
# Variabili globali per gestire lo stato condiviso tra thread
alerts = []  # Lista degli alert ricevuti
lock = threading.Lock()  # Lock per sincronizzare l'accesso alle variabili condivise
running = True  # Flag per controllare il ciclo principale

# ====== Inizializzazione audio ======
try:
    pygame.mixer.init()  # Inizializza il modulo audio di pygame
    print("pygame.mixer inizializzato correttamente")
except Exception as e:
    print(f"Errore inizializzazione pygame.mixer: {e}")  # Gestisce errori di inizializzazione audio

# File audio (opzionale)
SOUND_NORMAL = os.path.join(BASE_DIR, 'beep.wav')  # Percorso del file audio per notifiche standard
SOUND_URGENT = os.path.join(BASE_DIR, 'urgent.wav')  # Percorso del file audio per notifiche urgenti

# Funzione per generare un beep sintetico
def play_synthetic_beep(frequency=1000, duration=500):
    """
    Genera e riproduce un beep sintetico usando pygame.
    Args:
        frequency (int): Frequenza del beep in Hz (default: 1000)
        duration (int): Durata del beep in millisecondi (default: 500)
    """
    try:
        sample_rate = 44100  # Frequenza di campionamento standard (44.1 kHz)
        n_samples = int(sample_rate * duration / 1000)  # Numero di campioni per la durata
        t = np.linspace(0, duration / 1000, n_samples, False)  # Vettore temporale
        wave = 0.5 * np.sin(2 * np.pi * frequency * t)  # Genera un'onda sinusoidale
        sound = np.array([32767 * wave], dtype=np.int16).T  # Converte in formato audio 16-bit
        sound_obj = pygame.sndarray.make_sound(sound)  # Crea oggetto sonoro pygame
        sound_obj.play()  # Riproduce il suono
        print(f"Beep sintetico riprodotto: {frequency} Hz, {duration} ms")
    except Exception as e:
        print(f"Errore beep sintetico: {e}")
        # Fallback con afplay (per macOS)
        try:
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'])  # Usa suono di sistema
            print("Beep di fallback (afplay) riprodotto")
        except Exception as e:
            print(f"Errore afplay: {e}")

def play_alert_sound(action):
    """
    Riproduce un suono in base al tipo di alert ricevuto.
    Args:
        action (str): Tipo di azione ('urgent_assistance' o altro)
    """
    try:
        if action == 'urgent_assistance':
            if os.path.exists(SOUND_URGENT):  # Controlla se il file urgente esiste
                pygame.mixer.Sound(SOUND_URGENT).play()  # Riproduce suono urgente
                print(f"Suono urgente riprodotto: {SOUND_URGENT}")
            else:
                play_synthetic_beep(frequency=1500, duration=1000)  # Beep sintetico per urgenza
        else:
            if os.path.exists(SOUND_NORMAL):  # Controlla se il file standard esiste
                pygame.mixer.Sound(SOUND_NORMAL).play()  # Riproduce suono standard
                print(f"Suono standard riprodotto: {SOUND_NORMAL}")
            else:
                play_synthetic_beep(frequency=1000, duration=500)  # Beep sintetico standard
    except Exception as e:
        print(f"Errore riproduzione suono: {e}")
        # Fallback con afplay (per macOS)
        try:
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'])
            print("Beep di fallback (afplay) riprodotto")
        except Exception as e:
            print(f"Errore afplay: {e}")

def log_alert(alert):
    """
    Scrive un alert nel file di log.
    Args:
        alert (dict): Dizionario con dettagli dell'alert (azione, dispositivo, posizione, timestamp)
    """
    formatted_time = datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, 'a') as f:  # Apre il file di log in modalità append
            f.write(f"{formatted_time}: {alert['action']} - Device: {alert['device_id']} - Location: {alert['location']}\n")
        print(f"Log salvato: {formatted_time}, {alert['action']}")
    except Exception as e:
        print(f"Errore scrittura log: {e}")

def render_alerts(window_size):
    """
    Renderizza gli alert su un'immagine OpenCV, adattandosi alla dimensione della finestra.
    Args:
        window_size (tuple): Tuple con larghezza e altezza della finestra (width, height)
    Returns:
        np.ndarray: Immagine renderizzata con gli alert
    """
    width, height = window_size
    print(f"Dimensioni finestra rilevate: {width}x{height}")  # Debug
    # Calcola fattore di scala per adattarsi alla finestra
    scale = min(width / BASE_WIDTH, height / BASE_HEIGHT)
    scaled_width = int(BASE_WIDTH * scale)
    scaled_height = int(BASE_HEIGHT * scale)
    # Margine di sicurezza e dimensioni minime
    margin = int(20 * scale)
    scaled_width = max(scaled_width, 200)  # Dimensione minima per evitare errori
    scaled_height = max(scaled_height, 200)
    # Crea immagine nera con dimensioni scalate
    img = np.zeros((scaled_height, scaled_width, 3), dtype=np.uint8)
    # Aggiunge un bordo bianco per debug visivo
    cv2.rectangle(img, (0, 0), (scaled_width-1, scaled_height-1), (255, 255, 255), 1)
    print(f"Immagine renderizzata: {scaled_width}x{scaled_height}, scala: {scale}")  # Debug
    if not alerts:
        # Se non ci sono alert, mostra "Nessuna notifica"
        text = "Nessuna notifica"
        font_scale = 1.0 * scale  # Scala il font per leggibilità
        thickness = max(2, int(3 * scale))  # Spessore del testo scalato
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (scaled_width - text_size[0]) // 2  # Centra orizzontalmente
        text_y = (scaled_height + text_size[1]) // 2  # Centra verticalmente
        cv2.putText(img, text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
        print("Rendering: Nessuna notifica")
        return img
    # Rendering degli ultimi 5 alert
    y = int(60 * scale)  # Margine superiore scalato
    for alert in alerts[-5:]:  # Mostra solo gli ultimi 5 alert
        # Mappa le azioni a testi leggibili
        action_text = {
            'request_water': 'Richiesta Acqua',
            'report_pain': 'Segnalazione Dolore',
            'urgent_assistance': 'Assistenza Urgente'
        }.get(alert['action'], 'Azione Sconosciuta')
        text = f"{alert['formatted_time']} - {action_text} - {alert['device_id']} @ {alert['location']}"
        font_scale = 0.8 * scale  # Scala il font per leggibilità
        thickness = max(1, int(2 * scale))  # Spessore del testo scalato
        cv2.putText(img, text, (margin, y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        y += int(50 * scale)  # Incrementa la posizione y per il prossimo alert
        print(f"Rendering alert: {text}")
    return img

# ====== Flask endpoints ======
@app.route('/status', methods=['GET'])
def status():
    """
    Endpoint GET che restituisce lo stato attuale del sistema (JSON).
    """
    with lock:  # Sincronizza l'accesso alla lista degli alert
        print(f"Status richiesto: {len(alerts)} alert")
        return jsonify({
            'alert_count': len(alerts),  # Numero totale di alert
            'recent_alerts': alerts[-5:]  # Ultimi 5 alert
        })

@app.route('/command', methods=['POST', 'GET'])
def handle_command():
    """
    Endpoint per gestire comandi di notifica (es. richiesta acqua, dolore, assistenza urgente).
    Accetta sia GET (parametri in query) che POST (dati JSON).
    """
    # Estrae i dati dalla richiesta
    if request.method == 'POST' and request.json:
        data = request.json  # Dati JSON per richieste POST
    else:
        data = request.args.to_dict()  # Parametri query per richieste GET
    print(f"Richiesta ricevuta: {data}")
    action = data.get('action')
    if not action:
        print("Errore: action mancante")
        return jsonify({'status': 'error', 'message': 'missing action'}), 400
    # Controlla la presenza dei campi obbligatori
    required_fields = ['device_id', 'location', 'timestamp']
    if any(field not in data for field in required_fields):
        print(f"Errore: campi mancanti {required_fields}")
        return jsonify({'status': 'error', 'message': 'missing fields'}), 400
    try:
        timestamp = float(data['timestamp'])  # Converte il timestamp in float
    except ValueError:
        print("Errore: timestamp non valido")
        return jsonify({'status': 'error', 'message': 'invalid timestamp'}), 400
    with lock:  # Sincronizza l'accesso alle variabili condivise
        # Controlla se l'azione è valida
        if action not in ['request_water', 'report_pain', 'urgent_assistance']:
            print(f"Errore: azione sconosciuta {action}")
            return jsonify({'status': 'error', 'message': 'unknown action'}), 400
        # Formatta il timestamp
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        # Crea il dizionario dell'alert
        alert = {
            'action': action,
            'device_id': data['device_id'],
            'location': data['location'],
            'timestamp': timestamp,
            'formatted_time': formatted_time
        }
        alerts.append(alert)  # Aggiunge l'alert alla lista
        log_alert(alert)  # Registra l'alert nel file di log
        play_alert_sound(action)  # Riproduce il suono appropriato
        print(f"[ALERT] {action} | Device: {alert['device_id']} | Location: {alert['location']} | Time: {formatted_time}")
        return jsonify({'status': 'success', 'action': action, 'received': alert})

# ====== Thread Flask (server web) ======
def run_flask():
    """
    Avvia il server Flask in un thread separato.
    """
    print("Avvio server Flask su 0.0.0.0:5050")
    # Configura Flask per accettare connessioni concorrenti senza reloader
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)

# ====== Main loop (GUI OpenCV nel thread principale) ======
def main():
    """
    Funzione principale che gestisce la GUI OpenCV e il ciclo principale.
    """
    global running
    os.makedirs(BASE_DIR, exist_ok=True)  # Crea la directory di base se non esiste
    # Crea il file di log se non esiste
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Log delle notifiche\n")
    # Avvia il server Flask in un thread separato (daemon per terminare con il programma)
    t = threading.Thread(target=ಸrun_flask, daemon=True)
    t.start()
    # Crea una finestra OpenCV ridimensionabile
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, BASE_WIDTH, BASE_HEIGHT)
    print("Finestra OpenCV avviata (ridimensionabile)")
    # Ciclo principale della GUI
    while running:
        with lock:  # Sincronizza l'accesso per rendere gli alert
            try:
                # Ottiene le dimensioni attuali della finestra
                window_size = cv2.getWindowImageRect(WINDOW_TITLE)[2:4]
                if window_size[0] <= 0 or window_size[1] <= 0:
                    window_size = (BASE_WIDTH, BASE_HEIGHT)  # Usa dimensioni di default se non valide
            except Exception as e:
                print(f"Errore getWindowImageRect: {e}")
                window_size = (BASE_WIDTH, BASE_HEIGHT)
            frame = render_alerts(window_size)  # Renderizza gli alert
        cv2.imshow(WINDOW_TITLE, frame)  # Mostra l'immagine nella finestra
        k = cv2.waitKey(30) & 0xFF  # Attende 30ms per input da tastiera
        if k == ord('q'):  # Se premuto 'q', esce dal ciclo
            running = False
            break
    cv2.destroyAllWindows()  # Chiude tutte le finestre OpenCV
    try:
        pygame.mixer.quit()  # Chiude il mixer audio di pygame
    except:
        pass

def handle_sigint(sig, frame):
    """
    Gestisce il segnale SIGINT (Ctrl+C) per terminare il programma in modo pulito.
    """
    global running
    running = False  # Imposta il flag per uscire dal ciclo principale

if __name__ == '__main__':
    # Associa il gestore di segnali per SIGINT
    signal.signal(signal.SIGINT, handle_sigint)
    try:
        main()  # Esegue la funzione principale
    except Exception as e:
        print(f"Fatal: {e}")  # Stampa eventuali errori fatali
        try:
            cv2.destroyAllWindows()  # Chiude le finestre OpenCV
            pygame.mixer.quit()  # Chiude il mixer audio
        except:
            pass
        sys.exit(1)  # Esce con codice di errore 1
