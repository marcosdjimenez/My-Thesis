# Importazione delle librerie necessarie
import os, sys, io  # Per operazioni sul file system, gestione del sistema e I/O
import M5  # Libreria specifica per l'hardware M5Stack
from M5 import *  # Importa tutte le funzionalità di M5Stack (es. Widgets)
import m5ui  # Modulo per l'interfaccia utente grafica su M5Stack
import lvgl as lv  # Libreria LVGL per la gestione di interfacce grafiche
import requests2  # Per inviare richieste HTTP al server
from hardware import I2C, Pin  # Per gestire l'interfaccia I2C e i pin
from unit import GestureUnit  # Modulo per il sensore di gesti
import time  # Per gestione del tempo e ritardi
import network  # Per gestire la connessione Wi-Fi

# ====== Variabili globali ======
page0 = None  # Oggetto per la pagina dell'interfaccia grafica
label0 = None  # Etichetta per mostrare lo stato dei gesti
label_patient = None  # Etichetta per mostrare l'ID del paziente
http_req = None  # Oggetto per la richiesta HTTP
i2c0 = None  # Oggetto per l'interfaccia I2C
gesture_0 = None  # Oggetto per il sensore di gesti
gesture_num = None  # Numero del gesto rilevato
device_id = 'M5_001'  # Identificativo del dispositivo
location = 'Stanza 101'  # Posizione del dispositivo
last_action_time = 0  # Timestamp dell'ultima azione rilevata
feedback_duration = 2  # Durata del feedback visivo (in secondi)
SERVER_URL = 'http://192.168.1.163:5050/command'  # URL del server per inviare comandi
WIFI_SSID = 'Modem 4G Wi-Fi_CA5A'  # Nome della rete Wi-Fi
WIFI_PASSWORD = '02738204'  # Password della rete Wi-Fi

# ====== Funzioni di supporto ======
def log_gesture(action):
    """
    Registra un'azione nel file di log.
    Args:
        action: Azione da registrare (es. 'request_water')
    """
    global device_id, location
    timestamp = time.time()  # Ottiene il timestamp corrente
    try:
        with open('log.txt', 'a') as f:  # Apre il file di log in modalità append
            f.write(f"{timestamp}: {action} - Device: {device_id} - Location: {location}\n")
    except Exception as e:
        print(f"Errore scrittura log: {e}")  # Gestisce errori di scrittura

def send_request(action):
    """
    Invia una richiesta HTTP al server con l'azione specificata.
    Args:
        action: Azione da inviare (es. 'request_water')
    Returns:
        bool: True se la richiesta è stata inviata con successo, False altrimenti
    """
    global http_req, device_id, location
    # Crea il payload per la richiesta
    payload = {
        'action': action,
        'device_id': device_id,
        'location': location,
        'timestamp': time.time()
    }
    print(f"Invio richiesta: {action}, payload: {payload}")  # Debug
    try:
        http_req = requests2.post(SERVER_URL, json=payload, timeout=3)  # Invia richiesta POST
        print(f"Risposta server: {http_req.status_code}")
        if http_req.status_code == 200:  # Se la richiesta ha successo
            log_gesture(action)  # Registra l'azione nel log
            return True
        else:
            print(f"Errore server: {http_req.status_code}")
            return False
    except Exception as e:
        print(f"Errore connessione: {e}")  # Gestisce errori di connessione
        return False

# ====== Funzioni per la gestione dei gesti ======
def request_water():
    """
    Gestisce la richiesta di acqua rilevata tramite gesto.
    """
    global last_action_time
    label0.set_text(str('Richiesta Acqua Rilevata'))  # Aggiorna l'etichetta
    page0.set_bg_color(0xff6666, 255, 0)  # Imposta lo sfondo rosso chiaro
    last_action_time = time.time()  # Registra il tempo dell'azione
    if send_request('request_water'):  # Invia la richiesta
        label0.set_text(str('Richiesta Acqua Inoltrata, attendere...'))
    else:
        label0.set_text(str('Errore: Richiesta Acqua non inviata'))

def report_pain():
    """
    Gestisce la segnalazione di dolore rilevata tramite gesto.
    """
    global last_action_time
    label0.set_text(str('Segnalazione Dolore Rilevata'))  # Aggiorna l'etichetta
    page0.set_bg_color(0xff6666, 255, 0)  # Imposta lo sfondo rosso chiaro
    last_action_time = time.time()  # Registra il tempo dell'azione
    if send_request('report_pain'):  # Invia la richiesta
        label0.set_text(str('Segnalazione Dolore Inoltrata, attendere...'))
    else:
        label0.set_text(str('Errore: Segnalazione Dolore non inviata'))

def urgent_assistance():
    """
    Gestisce la richiesta di assistenza urgente rilevata tramite gesto.
    """
    global last_action_time
    label0.set_text(str('Assistenza Urgente Rilevata'))  # Aggiorna l'etichetta
    page0.set_bg_color(0x66ff99, 255, 0)  # Imposta lo sfondo verde chiaro
    last_action_time = time.time()  # Registra il tempo dell'azione
    if send_request('urgent_assistance'):  # Invia la richiesta
        label0.set_text(str('Assistenza Urgente Inoltrata, attendere...'))
    else:
        label0.set_text(str('Errore: Assistenza Urgente non inviata'))

# ====== Funzione di inizializzazione ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente, il sensore di gesti e la connessione Wi-Fi.
    """
    global page0, label0, label_patient, i2c0, gesture_0, gesture_num
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(1)  # Imposta la rotazione dello schermo
    m5ui.init()  # Inizializza il modulo UI
    # Crea la pagina principale con sfondo bianco
    page0 = m5ui.M5Page(bg_c=0xffffff)
    # Crea etichette per lo stato e l'ID del paziente
    label0 = m5ui.M5Label("label0", x=15, y=105, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_24, parent=page0)
    label_patient = m5ui.M5Label("patient_id", x=150, y=10, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_16, parent=page0)
    label_patient.set_text(f"Paziente: {device_id}")  # Imposta l'ID del paziente
    # Connessione Wi-Fi
    wlan = network.WLAN(network.STA_IF)  # Inizializza l'interfaccia Wi-Fi
    wlan.active(True)  # Attiva l'interfaccia
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)  # Connette alla rete
    print("Connessione WiFi in corso...")
    while not wlan.isconnected():
        time.sleep(1)  # Attende 1 secondo tra i tentativi
    print("Connesso a WiFi: " + str(wlan.ifconfig()))  # Stampa informazioni di connessione
    # Inizializza l'interfaccia I2C e il sensore di gesti
    i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)  # Configura I2C con frequenza 100 kHz
    gesture_0 = GestureUnit(i2c0)  # Inizializza il sensore di gesti
    gesture_0.set_gesture_highrate(True)  # Imposta modalità ad alta frequenza per i gesti
    page0.screen_load()  # Carica la pagina sullo schermo
    page0.set_bg_color(0xcccccc, 255, 0)  # Imposta lo sfondo grigio chiaro
    label0.set_text(str('In attesa di gesto...'))  # Imposta il messaggio iniziale
    # Crea o verifica il file di log
    try:
        with open('log.txt', 'r') as f:
            pass
    except:
        with open('log.txt', 'w') as f:
            f.write("Log dei gesti\n")  # Crea il file con intestazione

# ====== Ciclo principale ======
def loop():
    """
    Ciclo principale per rilevare gesti e aggiornare l'interfaccia utente.
    """
    global page0, label0, i2c0, gesture_0, gesture_num, last_action_time
    M5.update()  # Aggiorna lo stato dell'hardware M5Stack
    # Ripristina lo stato predefinito dopo la durata del feedback
    if last_action_time and (time.time() - last_action_time > feedback_duration):
        label0.set_text(str('In attesa di gesto...'))
        page0.set_bg_color(0xcccccc, 255, 0)  # Ripristina lo sfondo grigio
        last_action_time = 0
    # Rileva il gesto
    gesture_num = gesture_0.get_hand_gestures()
    print(f"Gesture rilevata: {gesture_num}")  # Debug
    # Elabora il gesto solo se non è in corso un feedback
    if last_action_time == 0:
        if gesture_num == 1:
            request_water()  # Gesto 1: richiesta acqua
        elif gesture_num == 2:
            report_pain()  # Gesto 2: segnalazione dolore
        elif gesture_num == 4:
            urgent_assistance()  # Gesto 4: assistenza urgente
    else:
        # Ripristina lo stato solo se il messaggio attuale non è relativo a un'azione in corso
        if label0.get_text() not in [
            'Richiesta Acqua Rilevata', 'Richiesta Acqua Inoltrata, attendere...', 'Errore: Richiesta Acqua non inviata',
            'Segnalazione Dolore Rilevata', 'Segnalazione Dolore Inoltrata, attendere...', 'Errore: Segnalazione Dolore non inviata',
            'Assistenza Urgente Rilevata', 'Assistenza Urgente Inoltrata, attendere...', 'Errore: Assistenza Urgente non inviata'
        ]:
            label0.set_text(str('In attesa di gesto...'))
            page0.set_bg_color(0xcccccc, 255, 0)
    time.sleep(0.1)  # Ritardo di 100 ms per il ciclo

# ====== Esecuzione principale ======
if __name__ == '__main__':
    try:
        setup()  # Esegue l'inizializzazione
        while True:
            loop()  # Esegue il ciclo principale
    except (Exception, KeyboardInterrupt) as e:
        try:
            m5ui.deinit()  # Deinizializza l'interfaccia UI
            from utility import print_error_msg
            print_error_msg(e)  # Stampa messaggio di errore formattato
        except ImportError:
            print("please update to latest firmware")  # Messaggio di fallback per firmware obsoleto
