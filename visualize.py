import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import os

# Coordinate delle ancore (devono corrispondere al codice del tag)
anchor0 = (0.0, 0.0)
anchor1 = (1.7, 0.0)
anchor2 = (0.0, 6.3)
anchor3 = (1.7, 6.3)

LOG_FILE = 'tracking_log.csv'

fig, ax = plt.subplots()
ax.set_title('UWB Tag Tracking (live)')
# Limiti adattati alla griglia 0..5; allarga un po’ i bordi
ax.set_xlim(-2, 4)
ax.set_ylim(-1, 8)

# Plotta le 4 ancore
ax.plot(
    [anchor0[0], anchor1[0], anchor2[0], anchor3[0]],
    [anchor0[1], anchor1[1], anchor2[1], anchor3[1]],
    'bo',
    label='Ancore'
)
# Etichette ancore
ax.text(anchor0[0]+0.05, anchor0[1]+0.05, 'A0')
ax.text(anchor1[0]+0.05, anchor1[1]+0.05, 'A1')
ax.text(anchor2[0]+0.05, anchor2[1]+0.05, 'A2')
ax.text(anchor3[0]+0.05, anchor3[1]+0.05, 'A3')

# Punto del tag
scatter, = ax.plot([], [], 'ro', label='Tag')
ax.legend(loc='upper left')

def read_last_xy(filepath):
    """Legge l’ultima riga valida e ritorna (x, y) oppure (None, None)."""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return None, None

    last = None
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
        if len(rows) < 2:
            return None, None  # solo header o vuoto
        last = rows[-1]

    # Formato: timestamp, dist0, dist1, dist2, dist3, x, y
    try:
        x = float(last[5])
        y = float(last[6])
        return x, y
    except (IndexError, ValueError):
        return None, None

def update(_frame):
    x, y = read_last_xy(LOG_FILE)
    if x is not None and y is not None:
        scatter.set_data([x], [y])
    return scatter,

ani = FuncAnimation(fig, update, interval=200)  # Aggiorna ogni 200 ms
plt.show()
