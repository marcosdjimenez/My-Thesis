# Importazione delle librerie necessarie
import os, sys, io  # Per operazioni sul file system, gestione del sistema e I/O
import M5  # Libreria specifica per l'hardware M5Stack
from M5 import *  # Importa tutte le funzionalità di M5Stack (es. Widgets, Power)
import m5ui  # Modulo per l'interfaccia utente grafica su M5Stack
import lvgl as lv  # Libreria LVGL per la gestione di interfacce grafiche
from unit import UWBUnit  # Modulo per il dispositivo UWB (Ultra-Wideband)

# ====== Variabili globali ======
page0 = None  # Oggetto per la pagina dell'interfaccia grafica
id = None  # Etichetta per l'ID del dispositivo
status = None  # Etichetta per lo stato di connessione
bat = None  # Etichetta statica per "Battery:"
batch = None  # Etichetta statica per "Charging:"
battery = None  # Etichetta per il valore della batteria
charge = None  # Etichetta per lo stato di carica
firmware = None  # Etichetta per la versione del firmware
mode = None  # Etichetta per la modalità del dispositivo
label0 = None  # Etichetta statica per "Mode:"
label1 = None  # Etichetta statica per "Anchor Status:"
label2 = None  # Etichetta statica per "Anchor ID:"
label3 = None  # Etichetta statica per "Firmware version:"
uwb_0 = None  # Oggetto per il dispositivo UWB

# ====== Funzione di inizializzazione ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente e il dispositivo UWB in modalità ancora.
    """
    global page0, id, status, bat, batch, battery, charge, firmware, mode, label0, label1, label2, label3, uwb_0
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(1)  # Imposta la rotazione dello schermo a 1 (orientamento specifico)
    m5ui.init()  # Inizializza il modulo UI
    # Crea la pagina principale con sfondo bianco
    page0 = m5ui.M5Page(bg_c=0xffffff)
    # Crea etichette per l'interfaccia utente
    id = m5ui.M5Label("id", x=100, y=30, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # ID dispositivo
    status = m5ui.M5Label("label0", x=130, y=60, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Stato connessione
    bat = m5ui.M5Label("Battery:", x=15, y=150, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta batteria
    batch = m5ui.M5Label("Charging:", x=15, y=180, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta stato carica
    battery = m5ui.M5Label("label4", x=75, y=150, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Valore batteria
    charge = m5ui.M5Label("charge", x=90, y=180, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Valore stato carica
    firmware = m5ui.M5Label("label2", x=145, y=120, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Versione firmware
    mode = m5ui.M5Label("label1", x=70, y=90, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Modalità dispositivo
    label0 = m5ui.M5Label("Mode:", x=15, y=90, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta modalità
    label1 = m5ui.M5Label("Anchor Status:", x=15, y=60, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta stato
    label2 = m5ui.M5Label("Anchor ID:", x=15, y=30, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta ID
    label3 = m5ui.M5Label("Firmware version:", x=15, y=120, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=page0)  # Etichetta firmware
    # Inizializza il dispositivo UWB in modalità ancora
    uwb_0 = UWBUnit(2, port=(18, 17), device_mode=UWBUnit.ANCHOR, device_id=0, verbose=False)
    if uwb_0.isconnected():
        print('Connected')  # Conferma la connessione
    uwb_0.set_measurement_interval(5)  # Imposta l'intervallo di misura (in unità non specificate)
    uwb_0.set_measurement(True)  # Avvia le misurazioni
    page0.screen_load()  # Carica la pagina sullo schermo

# ====== Ciclo principale ======
def loop():
    """
    Ciclo principale per aggiornare l'interfaccia utente con le informazioni del dispositivo UWB e della batteria.
    """
    global page0, id, status, bat, batch, battery, charge, firmware, mode, label0, label1, label2, label3, uwb_0
    M5.update()  # Aggiorna lo stato dell'hardware M5Stack
    # Aggiorna le etichette con i dati del dispositivo UWB e della batteria
    id.set_text(str(uwb_0.get_device_id()))  # ID del dispositivo
    mode.set_text(str(uwb_0.get_device_mode()))  # Modalità (ancora)
    status.set_text(str(uwb_0.isconnected()))  # Stato di connessione
    firmware.set_text(str(uwb_0.get_version()))  # Versione del firmware
    battery.set_text(str(Power.getBatteryLevel()))  # Livello della batteria
    charge.set_text(str(Power.isCharging()))  # Stato di carica

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
