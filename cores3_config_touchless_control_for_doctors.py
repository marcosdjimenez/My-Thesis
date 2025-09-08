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

# ====== Variabili globali ======
page0 = None  # Oggetto per la pagina dell'interfaccia grafica
label0 = None  # Etichetta per mostrare lo stato dei gesti
http_req = None  # Oggetto per la richiesta HTTP
i2c0 = None  # Oggetto per l'interfaccia I2C
gesture_0 = None  # Oggetto per il sensore di gesti
gesture_num = None  # Numero del gesto rilevato

# ====== Funzioni per la gestione dei gesti ======
def next_image():
    """
    Invia una richiesta HTTP per passare all'immagine successiva.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'next_image'})

def prev_image():
    """
    Invia una richiesta HTTP per passare all'immagine precedente.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'prev_image'})

def zoom_in():
    """
    Invia una richiesta HTTP per ingrandire l'immagine.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'zoom_in'})

def zoom_out():
    """
    Invia una richiesta HTTP per rimpicciolire l'immagine.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'zoom_out'})

def rotate_right():
    """
    Invia una richiesta HTTP per ruotare l'immagine a destra.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'rotate_right'})

def rotate_left():
    """
    Invia una richiesta HTTP per ruotare l'immagine a sinistra.
    """
    global gesture_num, page0, label0, http_req, i2c0, gesture_0
    http_req = requests2.post('http://192.168.1.163:5050/command', json={'action': 'rotate_left'})

# ====== Funzione di inizializzazione ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente e il sensore di gesti.
    """
    global page0, label0, http_req, i2c0, gesture_0, gesture_num
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(1)  # Imposta la rotazione dello schermo
    m5ui.init()  # Inizializza il modulo UI
    # Crea la pagina principale con sfondo bianco
    page0 = m5ui.M5Page(bg_c=0xffffff)
    # Crea un'etichetta per mostrare lo stato dei gesti
    label0 = m5ui.M5Label("label0", x=15, y=105, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_24, parent=page0)
    # Inizializza l'interfaccia I2C e il sensore di gesti
    i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)  # Configura I2C con frequenza 100 kHz
    gesture_0 = GestureUnit(i2c0)  # Inizializza il sensore di gesti
    gesture_0.set_gesture_highrate(True)  # Imposta modalità ad alta frequenza per i gesti
    page0.screen_load()  # Carica la pagina sullo schermo
    page0.set_bg_color(0xcccccc, 255, 0)  # Imposta lo sfondo grigio chiaro

# ====== Ciclo principale ======
def loop():
    """
    Ciclo principale per rilevare gesti e aggiornare l'interfaccia utente.
    """
    global page0, label0, http_req, i2c0, gesture_0, gesture_num
    M5.update()  # Aggiorna lo stato dell'hardware M5Stack
    gesture_num = gesture_0.get_hand_gestures()  # Rileva il gesto
    # Gestisce i gesti e aggiorna l'interfaccia
    if gesture_num == 1:
        label0.set_text(str('Prossima Immagine'))  # Mostra messaggio
        page0.set_bg_color(0xff6666, 255, 0)  # Sfondo rosso chiaro
        time.sleep(1)  # Attende 1 secondo per il feedback
        next_image()  # Invia richiesta per immagine successiva
    elif gesture_num == 2:
        label0.set_text(str('Immagine Precedente'))  # Mostra messaggio
        page0.set_bg_color(0xff6666, 255, 0)  # Sfondo rosso chiaro
        time.sleep(1)  # Attende 1 secondo
        prev_image()  # Invia richiesta per immagine precedente
    elif gesture_num == 4:
        label0.set_text(str('Zoom +'))  # Mostra messaggio
        page0.set_bg_color(0x66ff99, 255, 0)  # Sfondo verde chiaro
        time.sleep(1)  # Attende 1 secondo
        zoom_in()  # Invia richiesta per ingrandire
    elif gesture_num == 8:
        label0.set_text(str('Zoom -'))  # Mostra messaggio
        page0.set_bg_color(0x66ff99, 255, 0)  # Sfondo verde chiaro
        time.sleep(1)  # Attende 1 secondo
        zoom_out()  # Invia richiesta per rimpicciolire
    elif gesture_num == 16:
        label0.set_text(str('Ruota Dx'))  # Mostra messaggio
        page0.set_bg_color(0x9999ff, 255, 0)  # Sfondo blu chiaro
        time.sleep(1)  # Attende 1 secondo
        rotate_right()  # Invia richiesta per rotazione a destra
    elif gesture_num == 32:
        label0.set_text(str('Ruota Sx'))  # Mostra messaggio
        page0.set_bg_color(0x9999ff, 255, 0)  # Sfondo blu chiaro
        time.sleep(1)  # Attende 1 secondo
        rotate_left()  # Invia richiesta per rotazione a sinistra
    else:
        label0.set_text(str('In attesa di gesto...'))  # Stato predefinito
        page0.set_bg_color(0xcccccc, 255, 0)  # Sfondo grigio chiaro
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
