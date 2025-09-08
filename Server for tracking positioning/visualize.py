# Importazione delle librerie necessarie
import matplotlib.pyplot as plt  # Matplotlib per la creazione di grafici e visualizzazioni
from matplotlib.animation import FuncAnimation  # Per animazioni in tempo reale
import csv  # Per leggere il file CSV con i dati di tracking
import os  # Per operazioni sul file system (es. verifica esistenza file)

# ====== Configurazioni ======
# Coordinate delle ancore (fisse, definite in metri)
# Devono corrispondere alle posizioni usate nel sistema di tracking
anchor0 = (0.0, 0.0)  # Coordinata dell'ancora A0 (origine)
anchor1 = (1.7, 0.0)  # Coordinata dell'ancora A1
anchor2 = (0.0, 6.3)  # Coordinata dell'ancora A2
anchor3 = (1.7, 6.3)  # Coordinata dell'ancora A3
LOG_FILE = 'tracking_log.csv'  # Nome del file CSV contenente i dati di tracking

# ====== Inizializzazione del grafico ======
# Crea una figura e un asse per il grafico
fig, ax = plt.subplots()
ax.set_title('UWB Tag Tracking (live)')  # Imposta il titolo del grafico
# Imposta i limiti degli assi per coprire l'area delle ancore con margini
ax.set_xlim(-2, 4)  # Limiti x: da -2 a 4 per includere le ancore e margini
ax.set_ylim(-1, 8)  # Limiti y: da -1 a 8 per includere le ancore e margini

# Plotta le ancore come punti blu ('bo')
ax.plot(
    [anchor0[0], anchor1[0], anchor2[0], anchor3[0]],  # Coordinate x delle ancore
    [anchor0[1], anchor1[1], anchor2[1], anchor3[1]],  # Coordinate y delle ancore
    'bo',  # Formato: cerchi blu ('b' per blu, 'o' per cerchio)
    label='Ancore'  # Etichetta per la legenda
)

# Aggiunge etichette testuali vicino alle ancore (con piccolo offset per leggibilità)
ax.text(anchor0[0]+0.05, anchor0[1]+0.05, 'A0')  # Etichetta per ancora A0
ax.text(anchor1[0]+0.05, anchor1[1]+0.05, 'A1')  # Etichetta per ancora A1
ax.text(anchor2[0]+0.05, anchor2[1]+0.05, 'A2')  # Etichetta per ancora A2
ax.text(anchor3[0]+0.05, anchor3[1]+0.05, 'A3')  # Etichetta per ancora A3

# Crea un punto per il tag (inizialmente vuoto), mostrato come cerchio rosso ('ro')
scatter, = ax.plot([], [], 'ro', label='Tag')  # 'r' per rosso, 'o' per cerchio
ax.legend(loc='upper left')  # Aggiunge la legenda in alto a sinistra

# ====== Funzioni di supporto ======
def read_last_xy(filepath):
    """
    Legge l'ultima riga valida del file CSV e restituisce le coordinate (x, y).
    Args:
        filepath (str): Percorso del file CSV
    Returns:
        tuple: (x, y) se valide, altrimenti (None, None)
    """
    # Controlla se il file esiste e non è vuoto
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return None, None
    last = None
    # Apre il file CSV in modalità lettura
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)  # Crea un oggetto reader per il CSV
        rows = list(reader)  # Legge tutte le righe in una lista
        if len(rows) < 2:  # Se c'è solo l'intestazione o il file è vuoto
            return None, None
        last = rows[-1]  # Prende l'ultima riga
    # Formato atteso: [timestamp, dist0, dist1, dist2, dist3, x, y]
    try:
        x = float(last[5])  # Estrae e converte la coordinata x
        y = float(last[6])  # Estrae e converte la coordinata y
        return x, y
    except (IndexError, ValueError):  # Gestisce errori di formato o valori non numerici
        return None, None

# ====== Funzione di aggiornamento per l'animazione ======
def update(_frame):
    """
    Aggiorna il grafico con le coordinate più recenti del tag.
    Args:
        _frame: Parametro richiesto da FuncAnimation (non usato)
    Returns:
        tuple: Oggetti da aggiornare (il punto del tag)
    """
    x, y = read_last_xy(LOG_FILE)  # Legge le coordinate x, y più recenti
    if x is not None and y is not None:
        scatter.set_data([x], [y])  # Aggiorna la posizione del punto del tag
    return scatter,  # Restituisce l'oggetto scatter per l'animazione

# ====== Animazione ======
# Crea un'animazione che aggiorna il grafico ogni 200 ms
ani = FuncAnimation(fig, update, interval=200)  # Chiama update ogni 200 millisecondi

# ====== Esecuzione principale ======
plt.show()  # Mostra il grafico con l'animazione attiva
