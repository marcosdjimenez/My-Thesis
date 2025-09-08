# Importazione delle librerie necessarie
import os, sys, io  # Per operazioni sul file system, gestione del sistema e I/O
import M5  # Libreria specifica per l'hardware M5Stack
from M5 import *  # Importa tutte le funzionalità di M5Stack (es. Widgets, Power)
from unit import UWBUnit  # Modulo per gestire il dispositivo UWB (Ultra-Wideband)
import time  # Per gestione del tempo e ritardi
import math  # Per calcoli matematici
import network  # Per gestire la connessione Wi-Fi
import requests  # Per inviare richieste HTTP al server

# ====== Variabili globali ======
# Etichette per l'interfaccia utente
dist0 = None  # Etichetta per "Dist0:"
dist1 = None  # Etichetta per "Dist1:"
dist2 = None  # Etichetta per "Dist2:"
dist3 = None  # Etichetta per "Dist3:"
label4 = None  # Etichetta statica "Dist3:"
battery = None  # Etichetta per "Battery:"
label0 = None  # Etichetta per il valore di distanza 0
label1 = None  # Etichetta per il valore di distanza 1
label2 = None  # Etichetta per il valore di distanza 2
label3 = None  # Etichetta per il valore della batteria
# Oggetti e valori
uwb_0 = None  # Oggetto per il dispositivo UWB
distance0 = None  # Distanza dall'ancora 0
distance1 = None  # Distanza dall'ancora 1
distance2 = None  # Distanza dall'ancora 2
distance3 = None  # Distanza dall'ancora 3
# Coordinate fisse delle ancore (in metri)
anchor0 = (0.0, 0.0)  # Coordinata dell'ancora A0
anchor1 = (1.7, 0.0)  # Coordinata dell'ancora A1
anchor2 = (0.0, 6.3)  # Coordinata dell'ancora A2
anchor3 = (1.7, 6.3)  # Coordinata dell'ancora A3
position_x = None  # Coordinata x calcolata del tag
position_y = None  # Coordinata y calcolata del tag
# Configurazione Wi-Fi
WIFI_SSID = 'Modem 4G Wi-Fi_CA5A'  # Nome della rete Wi-Fi
WIFI_PASSWORD = '02738204'  # Password della rete Wi-Fi
SERVER_URL = 'http://192.168.1.163:5050/log'  # URL del server per inviare i dati

# ====== Funzioni principali ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente, il dispositivo UWB e la connessione Wi-Fi.
    """
    global dist0, dist1, dist2, dist3, label4, battery, label0, label1, label2, label3
    global uwb_0, distance0, distance1, distance2, distance3, position_x, position_y
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(3)  # Imposta la rotazione dello schermo a 3 (orientamento specifico)
    Widgets.fillScreen(0x000000)  # Imposta lo sfondo nero
    # Crea etichette per l'interfaccia utente
    dist0 = Widgets.Label("Dist0:", 10, 10, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    dist1 = Widgets.Label("Dist1:", 10, 35, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    dist2 = Widgets.Label("Dist2:", 10, 60, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    label4 = Widgets.Label("Dist3:", 10, 85, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    battery = Widgets.Label("Battery:", 10, 105, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    label0 = Widgets.Label("dis0", 70, 10, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    label1 = Widgets.Label("dis1", 70, 35, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    label2 = Widgets.Label("dis2", 70, 60, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    dist3 = Widgets.Label("dis3", 70, 85, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    label3 = Widgets.Label("bat", 90, 105, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    # Inizializza il dispositivo UWB in modalità tag
    uwb_0 = UWBUnit(2, port=(33, 32), device_mode=UWBUnit.TAG, verbose=True)
    uwb_0.set_measurement_interval(5)  # Imposta l'intervallo di misura (in unità non specificate)
    uwb_0.set_measurement(True)  # Avvia le misurazioni
    if uwb_0.isconnected():
        print('Tag connesso')  # Conferma la connessione del tag UWB
    # Connessione Wi-Fi
    wlan = network.WLAN(network.STA_IF)  # Inizializza l'interfaccia Wi-Fi in modalità station
    wlan.active(True)  # Attiva l'interfaccia Wi-Fi
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)  # Connette alla rete Wi-Fi
    while not wlan.isconnected():
        print('Connessione Wi-Fi in corso...')
        time.sleep(1)  # Attende 1 secondo tra i tentativi
    print('Wi-Fi connesso:', wlan.ifconfig())  # Stampa informazioni di connessione

def calculate_position_4(dists, anchors):
    """
    Calcola la posizione (x, y) del tag usando trilaterazione lineare con 4 ancore.
    Args:
        dists: Lista di 4 distanze dalle ancore
        anchors: Lista di coordinate delle ancore
    Returns:
        tuple: (x, y) se calcolabile, (None, None) altrimenti
    """
    # Richiede tutte e 4 le distanze
    if any(d is None for d in dists):
        return None, None
    x4, y4 = anchors[3]  # Usa l'ancora 3 come riferimento
    d4 = dists[3]
    # Costruisce la matrice A (3x2) e il vettore b (3x1)
    rows = []
    bs = []
    for i in range(3):  # Confronta le ancore 0, 1, 2 con l'ancora 3
        xi, yi = anchors[i]
        di = dists[i]
        Ai = [2 * (x4 - xi), 2 * (y4 - yi)]  # Coefficienti per x e y
        bi = (di**2 - d4**2 + x4**2 - xi**2 + y4**2 - yi**2)  # Termine noto
        rows.append(Ai)
        bs.append(bi)
    # Equazioni normali: (A^T A) p = A^T b
    a11 = sum(r[0]*r[0] for r in rows)  # Elemento (1,1) di A^T A
    a12 = sum(r[0]*r[1] for r in rows)  # Elemento (1,2) di A^T A
    a22 = sum(r[1]*r[1] for r in rows)  # Elemento (2,2) di A^T A
    b1 = sum(r[0]*bs[i] for i, r in enumerate(rows))  # Elemento 1 di A^T b
    b2 = sum(r[1]*bs[i] for i, r in enumerate(rows))  # Elemento 2 di A^T b
    det = a11*a22 - a12*a12  # Determinante di A^T A
    if abs(det) < 1e-6:  # Controlla se la matrice è singolare
        return None, None
    # Calcola l'inversa di A^T A
    inv11 = a22 / det
    inv12 = -a12 / det
    inv22 = a11 / det
    # Calcola la posizione
    x = inv11*b1 + inv12*b2
    y = inv12*b1 + inv22*b2
    return x, y

def loop():
    """
    Ciclo principale per leggere le distanze, calcolare la posizione e inviare i dati al server.
    """
    global dist0, dist1, dist2, dist3, label4, battery, label0, label1, label2, label3
    global uwb_0, distance0, distance1, distance2, distance3, position_x, position_y
    M5.update()  # Aggiorna lo stato dell'hardware M5Stack
    uwb_0.update()  # Aggiorna lo stato del dispositivo UWB
    # Legge le distanze dalle quattro ancore
    distance0 = uwb_0.get_distance(0)
    distance1 = uwb_0.get_distance(1)
    distance2 = uwb_0.get_distance(2)
    distance3 = uwb_0.get_distance(3)
    # Aggiorna le etichette dell'interfaccia utente con i valori delle distanze
    label0.setText(str(distance0))
    label1.setText(str(distance1))
    label2.setText(str(distance2))
    dist3.setText(str(distance3))
    label3.setText(str(M5.Power.getBatteryLevel()))  # Aggiorna il livello della batteria
    # Calcola la posizione usando trilaterazione
    position_x, position_y = calculate_position_4(
        [distance0, distance1, distance2, distance3],
        [anchor0, anchor1, anchor2, anchor3]
    )
    if position_x is not None:
        print(f'Posizione: ({position_x:.2f}, {position_y:.2f}) m')  # Stampa la posizione
        # Prepara i dati da inviare al server
        data = {
            'dist0': distance0,
            'dist1': distance1,
            'dist2': distance2,
            'dist3': distance3,
            'x': position_x,
            'y': position_y
        }
        try:
            response = requests.post(SERVER_URL, json=data)  # Invia i dati al server
            response.close()
            print('Dati inviati al PC')
        except Exception as e:
            print('Errore invio:', str(e))  # Gestisce errori di invio
    else:
        print('Impossibile calcolare la posizione (sistema degenerato o dati mancanti)')
    time.sleep_ms(200)  # Ritardo di 200 ms per il ciclo

if __name__ == '__main__':
    try:
        setup()  # Esegue l'inizializzazione
        while True:
            loop()  # Esegue il ciclo principale
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)  # Stampa messaggio di errore formattato (se disponibile)
        except ImportError:
            print("please update to latest firmware")  # Messaggio di fallback per firmware obsoleto
