# Importazione delle librerie necessarie
import cv2  # OpenCV per la gestione delle immagini e la GUI
import numpy as np  # NumPy per operazioni su array, usato per creare immagini vuote
from flask import Flask, request, jsonify  # Flask per creare un server web API
import os  # Per operazioni sul file system (es. gestione cartelle e file)
import threading  # Per gestire thread paralleli (es. server Flask e GUI OpenCV)
import signal  # Per gestire segnali di sistema (es. SIGINT per Ctrl+C)
import sys  # Per operazioni di sistema (es. uscita dal programma)
import time  # Non usato esplicitamente nel codice, ma importato per possibili estensioni future

# Creazione dell'istanza dell'applicazione Flask
app = Flask(__name__)

# ====== Percorsi/Config ======
# Definizione delle configurazioni di base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory assoluta del file corrente
IMAGE_FOLDER = os.path.join(BASE_DIR, 'immagini')  # Cartella per le immagini, situata nella directory del programma
VALID_EXT = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')  # Estensioni di file immagine valide
WINDOW_TITLE = 'Immagine Chirurgica'  # Titolo della finestra OpenCV

# ====== Stato condiviso ======
# Variabili globali per gestire lo stato condiviso tra thread
image_files = []  # Lista dei file immagine trovati nella cartella
current_image_index = 0  # Indice dell'immagine corrente nella lista
current_image = None  # Immagine corrente caricata (matrice OpenCV)
zoom_factor = 1.0  # Fattore di zoom attuale (1.0 = nessuna modifica)
rotation_quarters = 0  # Rotazione in multipli di 90° (0, 1, 2, 3)
lock = threading.Lock()  # Lock per sincronizzare l'accesso alle variabili condivise
running = True  # Flag per controllare il ciclo principale

# ====== Utility immagini ======
def scan_images():
    """
    Scansiona la cartella delle immagini e aggiorna la lista dei file validi.
    """
    global image_files
    os.makedirs(IMAGE_FOLDER, exist_ok=True)  # Crea la cartella 'immagini' se non esiste
    # Filtra i file nella cartella con estensioni valide, ordinandoli alfabeticamente
    image_files = sorted([f for f in os.listdir(IMAGE_FOLDER)
                          if f.lower().endswith(VALID_EXT)])

def load_current_image():
    """
    Carica l'immagine corrente in base all'indice attuale.
    """
    global current_image
    if not image_files:  # Se non ci sono immagini, imposta current_image a None
        current_image = None
        return
    # Costruisce il percorso dell'immagine corrente e la carica con OpenCV
    path = os.path.join(IMAGE_FOLDER, image_files[current_image_index])
    current_image = cv2.imread(path)

def render_image():
    """
    Restituisce l'immagine corrente con zoom e rotazione applicati.
    Se non ci sono immagini, restituisce un'immagine vuota con un messaggio.
    """
    if current_image is None:
        # Crea un'immagine nera (480x640, 3 canali) se non ci sono immagini
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        # Aggiunge un messaggio di errore in rosso
        cv2.putText(blank, "Nessuna immagine trovata", (40, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return blank
    img = current_image.copy()  # Crea una copia dell'immagine corrente per non modificarla
    # Applica la rotazione in base a rotation_quarters (0, 90, 180, 270 gradi)
    k = rotation_quarters % 4
    if k == 1:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)  # Rotazione di 90° in senso orario
    elif k == 2:
        img = cv2.rotate(img, cv2.ROTATE_180)  # Rotazione di 180°
    elif k == 3:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)  # Rotazione di 90° in senso antiorario
    # Applica lo zoom se diverso da 1.0
    if zoom_factor != 1.0:
        h, w = img.shape[:2]  # Ottiene altezza e larghezza dell'immagine
        # Ridimensiona l'immagine in base al fattore di zoom
        img = cv2.resize(img, (max(1, int(w * zoom_factor)), max(1, int(h * zoom_factor))),
                         interpolation=cv2.INTER_LINEAR)  # Interpolazione lineare per ridimensionamento
    return img

# ====== Flask endpoints ======
@app.route('/status', methods=['GET'])
def status():
    """
    Endpoint GET che restituisce lo stato attuale del sistema (JSON).
    """
    with lock:  # Usa il lock per accedere in sicurezza alle variabili condivise
        return jsonify({
            'images_dir': IMAGE_FOLDER,  # Percorso della cartella immagini
            'count': len(image_files),  # Numero di immagini disponibili
            'index': current_image_index if image_files else None,  # Indice immagine corrente
            'current': image_files[current_image_index] if image_files else None,  # Nome file corrente
            'zoom': zoom_factor,  # Fattore di zoom attuale
            'rot90': rotation_quarters  # Rotazione attuale (in multipli di 90°)
        })

@app.route('/rescan', methods=['POST'])
def rescan():
    """
    Endpoint POST che forza una nuova scansione della cartella immagini.
    """
    global current_image_index, zoom_factor, rotation_quarters
    with lock:  # Sincronizza l'accesso alle variabili condivise
        old_count = len(image_files)  # Memorizza il numero di immagini precedenti
        scan_images()  # Riscansiona la cartella
        if not image_files:  # Se non ci sono immagini
            current_image_index = 0
            load_current_image()  # Imposta immagine corrente a None
            return jsonify({'status': 'ok', 'message': 'No images found', 'count': 0})
        if old_count == 0:  # Se non c'erano immagini prima, resetta stato
            current_image_index = 0
            zoom_factor = 1.0
            rotation_quarters = 0
            load_current_image()  # Carica la prima immagine
        return jsonify({'status': 'ok', 'count': len(image_files)})

@app.route('/command', methods=['POST', 'GET'])
def handle_command():
    """
    Endpoint per gestire comandi (es. cambio immagine, zoom, rotazione).
    Accetta sia GET (con parametro 'action') che POST (con JSON).
    """
    global current_image_index, zoom_factor, rotation_quarters
    # Estrae il parametro 'action' dalla richiesta
    action = request.args.get('action') if request.method == 'GET' else (request.json or {}).get('action')
    if not action:  # Se manca il parametro action, restituisce errore
        return jsonify({'status': 'error', 'message': 'missing action'}), 400
    with lock:  # Sincronizza l'accesso alle variabili condivise
        # Controlla se ci sono immagini per comandi che le richiedono
        if not image_files and action in ('next_image', 'prev_image', 'zoom_in', 'zoom_out', 'rotate_right', 'rotate_left'):
            return jsonify({'status': 'error', 'message': 'no images available'}), 409
        if action == 'next_image':  # Passa all'immagine successiva
            current_image_index = (current_image_index + 1) % len(image_files)  # Cicla alla prima se alla fine
            zoom_factor = 1.0; rotation_quarters = 0  # Resetta zoom e rotazione
            load_current_image()  # Carica nuova immagine
        elif action == 'prev_image':  # Passa all'immagine precedente
            current_image_index = (current_image_index - 1) % len(image_files)  # Cicla all'ultima se all'inizio
            zoom_factor = 1.0; rotation_quarters = 0  # Resetta zoom e rotazione
            load_current_image()  # Carica nuova immagine
        elif action == 'zoom_in':  # Aumenta lo zoom
            zoom_factor = min(5.0, zoom_factor + 0.1)  # Limita zoom massimo a 5x
        elif action == 'zoom_out':  # Riduce lo zoom
            zoom_factor = max(0.1, zoom_factor - 0.1)  # Limita zoom minimo a 0.1x
        elif action == 'rotate_right':  # Ruota di 90° in senso orario
            rotation_quarters = (rotation_quarters + 1) % 4
        elif action == 'rotate_left':  # Ruota di 90° in senso antiorario
            rotation_quarters = (rotation_quarters - 1) % 4
        else:  # Azione non riconosciuta
            return jsonify({'status': 'error', 'message': 'unknown action'}), 400
        # Stampa log del comando per debug
        print(f"[CMD] {action} | idx={current_image_index} zoom={zoom_factor:.2f} rot90={rotation_quarters}")
        # Restituisce stato aggiornato
        return jsonify({'status': 'success', 'action': action,
                        'image': image_files[current_image_index] if image_files else None,
                        'zoom': zoom_factor, 'rot90': rotation_quarters})

# ====== Thread Flask (server web) ======
def run_flask():
    """
    Avvia il server Flask in un thread separato.
    """
    # Configura Flask per accettare connessioni concorrenti senza reloader
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)

# ====== Main loop (GUI OpenCV nel thread principale) ======
def main():
    """
    Funzione principale che gestisce la GUI OpenCV e il ciclo principale.
    """
    global running
    scan_images()  # Scansiona inizialmente la cartella immagini
    load_current_image()  # Carica la prima immagine (se presente)
    # Avvia il server Flask in un thread separato (daemon per terminare con il programma)
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    # Crea una finestra OpenCV con dimensione automatica
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)
    # Ciclo principale della GUI
    while running:
        with lock:  # Sincronizza l'accesso per rendere l'immagine
            frame = render_image()  # Ottiene l'immagine renderizzata
        cv2.imshow(WINDOW_TITLE, frame)  # Mostra l'immagine nella finestra
        # Attende 30ms per input da tastiera
        k = cv2.waitKey(30) & 0xFF
        if k == ord('q'):  # Se premuto 'q', esce dal ciclo
            running = False
            break
    cv2.destroyAllWindows()  # Chiude tutte le finestre OpenCV

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
        print("Fatal:", e)  # Stampa eventuali errori fatali
        try:
            cv2.destroyAllWindows()  # Tenta di chiudere le finestre OpenCV
        except:
            pass
        sys.exit(1)  # Esce con codice di errore 1
