import cv2
import numpy as np
from flask import Flask, request, jsonify
import os
import threading
import signal
import sys
import time

app = Flask(__name__)

# ====== Percorsi/Config ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'immagini')
VALID_EXT = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')
WINDOW_TITLE = 'Immagine Chirurgica'

# ====== Stato condiviso ======
image_files = []
current_image_index = 0
current_image = None
zoom_factor = 1.0
rotation_quarters = 0

lock = threading.Lock()
running = True

# ====== Utility immagini ======
def scan_images():
    global image_files
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    image_files = sorted([f for f in os.listdir(IMAGE_FOLDER)
                          if f.lower().endswith(VALID_EXT)])

def load_current_image():
    global current_image
    if not image_files:
        current_image = None
        return
    path = os.path.join(IMAGE_FOLDER, image_files[current_image_index])
    current_image = cv2.imread(path)

def render_image():
    if current_image is None:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, "Nessuna immagine trovata", (40, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return blank

    img = current_image.copy()
    k = rotation_quarters % 4
    if k == 1:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif k == 2:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif k == 3:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    if zoom_factor != 1.0:
        h, w = img.shape[:2]
        img = cv2.resize(img, (max(1, int(w * zoom_factor)), max(1, int(h * zoom_factor))),
                         interpolation=cv2.INTER_LINEAR)
    return img

# ====== Flask endpoints ======
@app.route('/status', methods=['GET'])
def status():
    with lock:
        return jsonify({
            'images_dir': IMAGE_FOLDER,
            'count': len(image_files),
            'index': current_image_index if image_files else None,
            'current': image_files[current_image_index] if image_files else None,
            'zoom': zoom_factor,
            'rot90': rotation_quarters
        })

@app.route('/rescan', methods=['POST'])
def rescan():
    global current_image_index, zoom_factor, rotation_quarters
    with lock:
        old_count = len(image_files)
        scan_images()
        if not image_files:
            current_image_index = 0
            load_current_image()
            return jsonify({'status': 'ok', 'message': 'No images found', 'count': 0})
        if old_count == 0:
            current_image_index = 0
            zoom_factor = 1.0
            rotation_quarters = 0
            load_current_image()
        return jsonify({'status': 'ok', 'count': len(image_files)})

@app.route('/command', methods=['POST', 'GET'])
def handle_command():
    global current_image_index, zoom_factor, rotation_quarters
    action = request.args.get('action') if request.method == 'GET' else (request.json or {}).get('action')
    if not action:
        return jsonify({'status': 'error', 'message': 'missing action'}), 400

    with lock:
        if not image_files and action in ('next_image','prev_image','zoom_in','zoom_out','rotate_right','rotate_left'):
            return jsonify({'status': 'error', 'message': 'no images available'}), 409

        if action == 'next_image':
            current_image_index = (current_image_index + 1) % len(image_files)
            zoom_factor = 1.0; rotation_quarters = 0
            load_current_image()
        elif action == 'prev_image':
            current_image_index = (current_image_index - 1) % len(image_files)
            zoom_factor = 1.0; rotation_quarters = 0
            load_current_image()
        elif action == 'zoom_in':
            zoom_factor = min(5.0, zoom_factor + 0.1)
        elif action == 'zoom_out':
            zoom_factor = max(0.1, zoom_factor - 0.1)
        elif action == 'rotate_right':
            rotation_quarters = (rotation_quarters + 1) % 4
        elif action == 'rotate_left':
            rotation_quarters = (rotation_quarters - 1) % 4
        else:
            return jsonify({'status': 'error', 'message': 'unknown action'}), 400

        print(f"[CMD] {action} | idx={current_image_index} zoom={zoom_factor:.2f} rot90={rotation_quarters}")
        return jsonify({'status':'success','action':action,
                        'image': image_files[current_image_index] if image_files else None,
                        'zoom': zoom_factor, 'rot90': rotation_quarters})

# ====== Thread Flask (server web) ======
def run_flask():
    # niente reloader, thread singolo interno, ma accetta connessioni concorrenti (threaded=True)
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)

# ====== Main loop (GUI OpenCV nel thread principale) ======
def main():
    global running
    scan_images()
    load_current_image()

    # Avvia Flask in un thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Finestra OpenCV nel MAIN thread
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)

    # Loop GUI
    while running:
        with lock:
            frame = render_image()
        cv2.imshow(WINDOW_TITLE, frame)
        # gestisci 'q' per uscire
        k = cv2.waitKey(30) & 0xFF
        if k == ord('q'):
            running = False
            break

    cv2.destroyAllWindows()

def handle_sigint(sig, frame):
    global running
    running = False

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_sigint)
    try:
        main()
    except Exception as e:
        print("Fatal:", e)
        try:
            cv2.destroyAllWindows()
        except:
            pass
        sys.exit(1)
