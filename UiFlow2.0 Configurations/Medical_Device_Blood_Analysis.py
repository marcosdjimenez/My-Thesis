# Importazione delle librerie necessarie
import os, sys, io  # Per operazioni sul file system, gestione del sistema e I/O
import M5  # Libreria specifica per l'hardware M5Stack
from M5 import *  # Importa tutte le funzionalità di M5Stack (es. Widgets, Power)
from hardware import I2C, Pin  # Per gestire l'interfaccia I2C e i pin
from unit import GestureUnit, HeartUnit  # Moduli per il sensore di gesti e il sensore di frequenza cardiaca/SpO2
import time  # Per gestione del tempo e ritardi

# ====== Variabili globali ======
label0 = None  # Etichetta per "HR:"
label1 = None  # Etichetta per "SpO2:"
label2 = None  # Etichetta per "Gesture:"
h_r = None  # Etichetta per il valore della frequenza cardiaca
spo2 = None  # Etichetta per il valore di SpO2
gesture = None  # Etichetta per la descrizione del gesto
label3 = None  # Etichetta per "Battery:"
bat = None  # Etichetta per il valore della batteria
i2c0 = None  # Oggetto per l'interfaccia I2C
gesture_0 = None  # Oggetto per il sensore di gesti
heart_0 = None  # Oggetto per il sensore di frequenza cardiaca/SpO2

# ====== Funzione di inizializzazione ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente e i sensori (gesti e frequenza cardiaca/SpO2).
    """
    global label0, label1, label2, h_r, spo2, gesture, label3, bat, i2c0, gesture_0, heart_0
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(3)  # Imposta la rotazione dello schermo a 3 (orientamento specifico)
    Widgets.fillScreen(0x000000)  # Imposta lo sfondo nero
    # Crea etichette per l'interfaccia utente
    label0 = Widgets.Label("HR:", 10, 10, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Etichetta per frequenza cardiaca
    label1 = Widgets.Label("SpO2:", 10, 40, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Etichetta per SpO2
    label2 = Widgets.Label("Gesture:", 10, 70, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Etichetta per gesto
    h_r = Widgets.Label("label3", 45, 10, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Valore frequenza cardiaca
    spo2 = Widgets.Label("label3", 70, 40, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Valore SpO2
    gesture = Widgets.Label("label3", 95, 70, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Valore gesto
    label3 = Widgets.Label("Battery: ", 10, 100, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Etichetta batteria
    bat = Widgets.Label("label4", 95, 100, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)  # Valore batteria
    # Inizializza l'interfaccia I2C
    i2c0 = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)  # Configura I2C con frequenza 100 kHz
    print('I2C scan:', i2c0.scan())  # Debug: mostra gli indirizzi I2C rilevati (attesi [87, 115])
    # Inizializza il sensore di gesti
    try:
        gesture_0 = GestureUnit(i2c0)
        print('Gesture init OK')
    except Exception as e:
        print('Errore Gesture init:', str(e))  # Gestisce errori di inizializzazione
    # Inizializza il sensore di frequenza cardiaca/SpO2
    try:
        heart_0 = HeartUnit(i2c0, 0x57)  # Inizializza con indirizzo I2C 0x57
        heart_0.start()  # Avvia le misurazioni
        print('Heart init OK')
    except Exception as e:
        print('Errore Heart init:', str(e))  # Gestisce errori di inizializzazione

# ====== Ciclo principale ======
def loop():
    """
    Ciclo principale per leggere i dati dai sensori e aggiornare l'interfaccia utente.
    """
    global label0, label1, label2, h_r, spo2, gesture, label3, bat, i2c0, gesture_0, heart_0
    M5.update()  # Aggiorna lo stato dell'hardware M5Stack
    # Legge frequenza cardiaca e SpO2
    try:
        h_r.setText(str(heart_0.get_heart_rate()))  # Aggiorna la frequenza cardiaca
        spo2.setText(str(heart_0.get_spo2()))  # Aggiorna il valore di SpO2
    except Exception as e:
        h_r.setText('Error')  # Mostra errore in caso di problema
        spo2.setText('Error')
        print('Errore lettura Heart:', str(e))  # Debug
    # Legge il gesto
    try:
        gest_val = gesture_0.get_gesture()  # Ottiene il valore del gesto
        desc = gesture_0.gesture_description(gest_val)  # Ottiene la descrizione del gesto
        gesture.setText(desc)  # Aggiorna l'etichetta del gesto
    except Exception as e:
        gesture.setText('Error')  # Mostra errore in caso di problema
        print('Errore lettura Gesture:', str(e))  # Debug
    bat.setText(str(Power.getBatteryLevel()))  # Aggiorna il livello della batteria
    time.sleep(5)  # Ritardo di 5 secondi per il ciclo

# ====== Esecuzione principale ======
if __name__ == '__main__':
    try:
        setup()  # Esegue l'inizializzazione
        while True:
            loop()  # Esegue il ciclo principale
    except (Exception, KeyboardInterrupt) as e:
        try:
            if heart_0:
                heart_0.deinit()  # Deinizializza il sensore di frequenza cardiaca
            from utility import print_error_msg
            print_error_msg(e)  # Stampa messaggio di errore formattato
        except ImportError:
            print("please update to latest firmware")  # Messaggio di fallback per firmware obsoleto
