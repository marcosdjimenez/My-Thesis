# Importazione delle librerie necessarie
import os, sys, io
import M5
from M5 import *
from unit import UWBUnit
import time
import math
import network
import requests
# ====================================================================
# CLASSE PER IL FILTRAGGIO DELLA DISTANZA
# ====================================================================
class FilteredDistance:
    """
    Gestisce il filtraggio di un singolo canale di distanza UWB.
    Implementa un validatore di spike e uno smoothing esponenziale (EMA).
    """
    def __init__(self, alpha, validation_threshold):
        self.alpha = alpha
        self.threshold = validation_threshold
        self.smoothed_value = None
        self.last_valid_raw = None

    def update(self, raw_distance):
        if raw_distance is None:
            return self.smoothed_value
        if self.smoothed_value is None:
            self.smoothed_value = raw_distance
            self.last_valid_raw = raw_distance
            return self.smoothed_value
        if abs(raw_distance - self.last_valid_raw) > self.threshold:
            return self.smoothed_value
        self.last_valid_raw = raw_distance
        self.smoothed_value = (self.alpha * raw_distance) + ((1 - self.alpha) * self.smoothed_value)
        return self.smoothed_value
# ====== Variabili globali ======
dist0 = None
dist1 = None
dist2 = None
dist3 = None
label4 = None
battery = None
label0 = None
label1 = None
label2 = None
label3 = None
uwb_0 = None
# Coordinate fisse delle ancore (in metri) - ignoriamo anchor1 poiché non funziona
anchor0 = (0.0, 0.0)
anchor2 = (0.0, 6.3)
anchor3 = (1.7, 6.3)
position_x = None
position_y = None
# Configurazione Wi-Fi
WIFI_SSID = 'Modem 4G Wi-Fi_CA5A'
WIFI_PASSWORD = '02738204'
SERVER_URL = 'http://192.168.1.129:5050/log_filtered'  # Usa il tuo IP corretto
# ====== OGGETTI FILTRO ======
# Filtri solo per le ancore funzionanti (0,2,3)
dist_filter0 = FilteredDistance(alpha=0.4, validation_threshold=1.5)
dist_filter2 = FilteredDistance(alpha=0.4, validation_threshold=1.5)
dist_filter3 = FilteredDistance(alpha=0.4, validation_threshold=1.5)
# ====== Funzioni principali ======
def setup():
    global dist0, dist1, dist2, dist3, label4, battery, label0, label1, label2, label3
    global uwb_0
    M5.begin()
    Widgets.setRotation(3)
    Widgets.fillScreen(0x000000)
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
    uwb_0.set_measurement_interval(5)
    uwb_0.set_measurement(True)
    if uwb_0.isconnected():
        print('Tag connesso')
    # Connessione Wi-Fi
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        print('Connessione Wi-Fi in corso...')
        time.sleep(1)
    print('Wi-Fi connesso:', wlan.ifconfig())
def calculate_position_3(dists, anchors):
    # dists = [d0, d2, d3], anchors = [anchor0, anchor2, anchor3]
    if any(d is None for d in dists):
        return None, None
    x4, y4 = anchors[2]  # anchor3 as ref
    d4 = dists[2]
    rows = []
    bs = []
    for i in range(2):  # anchors 0 and 2
        xi, yi = anchors[i]
        di = dists[i]
        Ai = [2 * (x4 - xi), 2 * (y4 - yi)]
        bi = (di**2 - d4**2 + x4**2 - xi**2 + y4**2 - yi**2)
        rows.append(Ai)
        bs.append(bi)
    a11 = sum(r[0]*r[0] for r in rows)
    a12 = sum(r[0]*r[1] for r in rows)
    a22 = sum(r[1]*r[1] for r in rows)
    b1 = sum(r[0]*bs[i] for i, r in enumerate(rows))
    b2 = sum(r[1]*bs[i] for i, r in enumerate(rows))
    det = a11*a22 - a12*a12
    if abs(det) < 1e-6:
        return None, None
    inv11 = a22 / det
    inv12 = -a12 / det
    inv22 = a11 / det
    x = inv11*b1 + inv12*b2
    y = inv12*b1 + inv22*b2
    return x, y
def loop():
    global position_x, position_y
    M5.update()
    uwb_0.update()
   
    # 1. LEGGI LE DISTANZE GREZZE - ignoriamo distance1_raw poiché anchor1 non funziona
    distance0_raw = uwb_0.get_distance(0)
    distance1_raw = uwb_0.get_distance(1)  # Mantenuto per UI, ma non usato in posizione
    distance2_raw = uwb_0.get_distance(2)
    distance3_raw = uwb_0.get_distance(3)
   
    # Debug: Stampa raw
    print(f'Raw: d0={distance0_raw}, d1={distance1_raw}, d2={distance2_raw}, d3={distance3_raw}')
   
    # 2. APPLICA IL FILTRO solo alle funzionanti
    distance0_filtered = dist_filter0.update(distance0_raw)
    # distance1_filtered non usato, set to raw or None for data
    distance1_filtered = distance1_raw  # O None, ma per compatibilità
    distance2_filtered = dist_filter2.update(distance2_raw)
    distance3_filtered = dist_filter3.update(distance3_raw)
   
    # Debug: Stampa filtered
    print(f'Filtered: d0={distance0_filtered}, d1={distance1_filtered}, d2={distance2_filtered}, d3={distance3_filtered}')
   
    # Aggiorna UI con filtered (dist1 mostrerà 0.00 o N/A)
    label0.setText("{:.2f}m".format(distance0_filtered) if distance0_filtered is not None else "N/A")
    label1.setText("{:.2f}m".format(distance1_filtered) if distance1_filtered is not None else "N/A")
    label2.setText("{:.2f}m".format(distance2_filtered) if distance2_filtered is not None else "N/A")
    dist3.setText("{:.2f}m".format(distance3_filtered) if distance3_filtered is not None else "N/A")
    label3.setText(str(M5.Power.getBatteryLevel()))
   
    # 3. CALCOLA POSIZIONE RAW E FILTERED ignorando anchor1
    position_x_raw, position_y_raw = calculate_position_3(
        [distance0_raw, distance2_raw, distance3_raw],
        [anchor0, anchor2, anchor3]
    )
    position_x_filtered, position_y_filtered = calculate_position_3(
        [distance0_filtered, distance2_filtered, distance3_filtered],
        [anchor0, anchor2, anchor3]
    )
   
    # Usa filtered per position_x/y globale
    position_x, position_y = position_x_filtered, position_y_filtered
   
    if position_x_filtered is not None:
        print(f'Posizione filtered: ({position_x_filtered:.2f}, {position_y_filtered:.2f}) m')
    else:
        print('Impossibile calcolare posizione filtered')
   
    if position_x_raw is not None:
        print(f'Posizione raw: ({position_x_raw:.2f}, {position_y_raw:.2f}) m')
   
    # Invia dati (dist1 incluso per compatibilità, anche se non usato)
    data = {
        'dist0_raw': distance0_raw,
        'dist1_raw': distance1_raw,
        'dist2_raw': distance2_raw,
        'dist3_raw': distance3_raw,
        'dist0': distance0_filtered,
        'dist1': distance1_filtered,
        'dist2': distance2_filtered,
        'dist3': distance3_filtered,
        'x_raw': position_x_raw,
        'y_raw': position_y_raw,
        'x': position_x_filtered,
        'y': position_y_filtered
    }
    try:
        response = requests.post(SERVER_URL, json=data)
        response.close()
        print('Dati inviati al PC')
    except Exception as e:
        print('Errore invio:', str(e))
       
    time.sleep_ms(200)
if __name__ == '__main__':
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")
