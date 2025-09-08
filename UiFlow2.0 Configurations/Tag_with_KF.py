# Importazione delle librerie necessarie
import time, math  # Per gestione del tempo e calcoli matematici
import network  # Per gestire la connessione Wi-Fi
import requests  # Per inviare richieste HTTP al server
import M5  # Libreria specifica per l'hardware M5Stack
from M5 import *  # Importa tutte le funzionalità di M5Stack (es. Widgets, Power)
from unit import UWBUnit  # Modulo per gestire il dispositivo UWB (Ultra-Wideband)

# ====== Configurazioni ======
WIFI_SSID = 'Modem 4G Wi-Fi_CA5A'  # Nome della rete Wi-Fi
WIFI_PASSWORD = '02738204'  # Password della rete Wi-Fi
SERVER_URL = 'http://192.168.1.163:5050/log'  # URL del server per inviare i dati di tracking
ANCHORS = [
    (0.0, 0.0),  # Coordinata dell'ancora A0
    (1.7, 0.0),  # Coordinata dell'ancora A1
    (0.0, 6.3),  # Coordinata dell'ancora A2
    (1.7, 6.3)   # Coordinata dell'ancora A3
]
# Parametri per la media mobile
MA_WINDOW = 5  # Dimensione della finestra per la media mobile per ogni ancora
# Parametri per il filtro di Kalman esteso (EKF)
DT = 0.2  # Periodo del ciclo in secondi (deve corrispondere al tempo di sleep)
SIGMA_A = 0.8  # Deviazione standard dell'accelerazione (m/s^2, parametro di tuning)
SIGMA_R_DEFAULT = 0.2  # Deviazione standard del rumore di misura per ogni ancora (metri, default)
MAHAL_THR_MULT = 6.0  # Moltiplicatore per la soglia di gating Mahalanobis (per rilevamento outlier)
MIN_ANCHORS_FOR_POS = 3  # Numero minimo di ancore per calcolare la posizione (almeno 3 per 2D)
LOOP_MS = int(DT*1000)  # Tempo di ciclo in millisecondi (200 ms)

# ====== Funzioni matematiche per matrici e vettori ======
def mat_add(A, B):
    """
    Somma due matrici elemento per elemento.
    Args:
        A, B: Matrici dello stesso ordine (lista di liste)
    Returns:
        list: Matrice risultante
    """
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]

def mat_sub(A, B):
    """
    Sottrae due matrici elemento per elemento.
    Args:
        A, B: Matrici dello stesso ordine
    Returns:
        list: Matrice risultante
    """
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]

def mat_mul(A, B):
    """
    Moltiplica due matrici.
    Args:
        A: Matrice n x p
        B: Matrice p x m
    Returns:
        list: Matrice risultante n x m
    """
    n = len(A); p = len(A[0]); m = len(B[0])
    C = [[0.0]*m for _ in range(n)]
    for i in range(n):
        for k in range(p):
            aik = A[i][k]
            if aik == 0.0:  # Ottimizzazione: salta se elemento nullo
                continue
            rowB = B[k]
            for j in range(m):
                C[i][j] += aik * rowB[j]
    return C

def mat_transpose(A):
    """
    Trasposta di una matrice.
    Args:
        A: Matrice
    Returns:
        list: Matrice trasposta
    """
    return [list(row) for row in zip(*A)]

def scalar_mul(A, s):
    """
    Moltiplica una matrice per uno scalare.
    Args:
        A: Matrice
        s: Scalare
    Returns:
        list: Matrice risultante
    """
    return [[A[i][j]*s for j in range(len(A[0]))] for i in range(len(A))]

def eye(n, eps=0.0):
    """
    Crea una matrice identità n x n con opzionale valore epsilon sulla diagonale.
    Args:
        n: Dimensione della matrice
        eps: Valore da aggiungere alla diagonale (default 0.0)
    Returns:
        list: Matrice identità
    """
    return [[(1.0 if i==j else 0.0) + (eps if i==j else 0.0) for j in range(n)] for i in range(n)]

def vec_add(a, b):
    """
    Somma due vettori.
    Args:
        a, b: Vettori della stessa lunghezza
    Returns:
        list: Vettore risultante
    """
    return [a[i]+b[i] for i in range(len(a))]

def vec_sub(a, b):
    """
    Sottrae due vettori.
    Args:
        a, b: Vettori della stessa lunghezza
    Returns:
        list: Vettore risultante
    """
    return [a[i]-b[i] for i in range(len(a))]

def vec_dot(a, b):
    """
    Prodotto scalare di due vettori.
    Args:
        a, b: Vettori della stessa lunghezza
    Returns:
        float: Prodotto scalare
    """
    return sum(a[i]*b[i] for i in range(len(a))]

def mat_inv(A):
    """
    Inverte una matrice quadrata usando l'algoritmo di Gauss-Jordan.
    Args:
        A: Matrice quadrata
    Returns:
        list: Matrice inversa
    Raises:
        ValueError: Se la matrice è singolare
    """
    n = len(A)
    # Crea matrice aumentata [A | I]
    M = [list(A[i]) + [0.0]*n for i in range(n)]
    for i in range(n):
        M[i][n+i] = 1.0
    # Eliminazione in avanti
    for i in range(n):
        pivot = M[i][i]
        if abs(pivot) < 1e-12:  # Controlla se il pivot è troppo piccolo
            # Tenta di scambiare con una riga inferiore
            for k in range(i+1, n):
                if abs(M[k][i]) > 1e-12:
                    M[i], M[k] = M[k], M[i]
                    pivot = M[i][i]
                    break
            else:
                raise ValueError("Matrix singular for inversion")
        # Normalizza la riga
        inv_p = 1.0 / pivot
        for j in range(2*n):
            M[i][j] *= inv_p
        # Elimina le altre righe
        for r in range(n):
            if r == i:
                continue
            factor = M[r][i]
            if factor == 0.0:
                continue
            for c in range(i, 2*n):
                M[r][c] -= factor * M[i][c]
    # Estrae la matrice inversa
    Inv = [row[n:] for row in M]
    return Inv

def solve_linear(A, b):
    """
    Risolve un sistema lineare Ax = b usando l'eliminazione di Gauss.
    Args:
        A: Matrice quadrata n x n
        b: Vettore di lunghezza n
    Returns:
        list: Soluzione x
    Raises:
        ValueError: Se la matrice è singolare
    """
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]  # Matrice aumentata [A | b]
    # Eliminazione in avanti
    for i in range(n):
        pivot = M[i][i]
        if abs(pivot) < 1e-12:
            for k in range(i+1, n):
                if abs(M[k][i]) > 1e-12:
                    M[i], M[k] = M[k], M[i]
                    pivot = M[i][i]
                    break
            else:
                raise ValueError("Singular matrix in solve")
        invp = 1.0 / pivot
        for j in range(i, n+1):
            M[i][j] *= invp
        for r in range(n):
            if r == i:
                continue
            f = M[r][i]
            if f == 0.0:
                continue
            for c in range(i, n+1):
                M[r][c] -= f * M[i][c]
    return [M[i][n] for i in range(n)]

# ====== Classe per la media mobile ======
class MovingAverage:
    def __init__(self, N):
        """
        Inizializza un filtro a media mobile.
        Args:
            N: Dimensione della finestra
        """
        self.N = max(1, int(N))  # Assicura che la finestra sia almeno 1
        self.buf = []  # Buffer per i valori

    def add(self, v):
        """
        Aggiunge un valore al buffer.
        Args:
            v: Valore da aggiungere
        """
        self.buf.append(v)
        if len(self.buf) > self.N:
            self.buf.pop(0)  # Rimuove il valore più vecchio se il buffer è pieno

    def mean(self):
        """
        Calcola la media dei valori nel buffer.
        Returns:
            float: Media, o None se il buffer è vuoto
        """
        if not self.buf:
            return None
        return sum(self.buf) / len(self.buf)

    def ready(self):
        """
        Verifica se il buffer ha almeno un valore.
        Returns:
            bool: True se il buffer ha dati
        """
        return len(self.buf) >= 1

# ====== Classe per il filtro di Kalman esteso (EKF) ======
class EKF2D:
    def __init__(self, dt, sigma_a=SIGMA_A):
        """
        Inizializza il filtro di Kalman esteso per il tracking 2D.
        Args:
            dt: Periodo del ciclo (secondi)
            sigma_a: Deviazione standard dell'accelerazione (m/s^2)
        """
        self.dt = dt
        self.x = [0.0, 0.0, 0.0, 0.0]  # Stato: [x, y, vx, vy]
        # Matrice di covarianza iniziale (incertezza moderata su posizione)
        self.P = [[1.0, 0, 0, 0],
                  [0, 1.0, 0, 0],
                  [0, 0, 1.0, 0],
                  [0, 0, 0, 1.0]]
        self.sigma_a = sigma_a
        self._update_Q()  # Inizializza la matrice di covarianza del rumore di processo

    def _update_Q(self):
        """
        Aggiorna la matrice di covarianza del rumore di processo Q.
        """
        dt = self.dt
        s2 = self.sigma_a**2
        self.Q = [
            [s2*(dt**4)/4.0, 0.0, s2*(dt**3)/2.0, 0.0],
            [0.0, s2*(dt**4)/4.0, 0.0, s2*(dt**3)/2.0],
            [s2*(dt**3)/2.0, 0.0, s2*(dt**2), 0.0],
            [0.0, s2*(dt**3)/2.0, 0.0, s2*(dt**2)]
        ]

    def predict(self):
        """
        Fase di predizione del filtro di Kalman.
        Aggiorna lo stato e la covarianza in base al modello di movimento.
        """
        x, y, vx, vy = self.x
        dt = self.dt
        # Predizione dello stato: x = x + vx*dt, y = y + vy*dt, velocità costante
        self.x = [x + vx*dt, y + vy*dt, vx, vy]
        # Matrice di transizione di stato F
        F = [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]]
        # Aggiorna la covarianza: P = F P F^T + Q
        FP = mat_mul(F, self.P)
        FPFt = mat_mul(FP, mat_transpose(F))
        self.P = mat_add(FPFt, self.Q)

    def get_predicted_ranges(self, anchors):
        """
        Calcola le distanze previste alle ancore in base allo stato predetto.
        Args:
            anchors: Lista di coordinate delle ancore
        Returns:
            list: Distanze previste
        """
        x, y = self.x[0], self.x[1]
        ranges = []
        for ax, ay in anchors:
            dx = x - ax
            dy = y - ay
            ranges.append(math.sqrt(dx*dx + dy*dy))
        return ranges

    def update_with_ranges(self, z_list, anchors, R_diag):
        """
        Fase di aggiornamento del filtro di Kalman con le misurazioni delle distanze.
        Args:
            z_list: Lista delle distanze misurate
            anchors: Lista delle coordinate delle ancore corrispondenti
            R_diag: Lista delle deviazioni standard delle misurazioni
        Returns:
            tuple: (successo, info) - True se l'aggiornamento è riuscito, False altrimenti
        """
        m = len(z_list)
        # Calcola h(x) (distanze previste) e la matrice Jacobiana H
        hx = []
        H = []
        x_est, y_est = self.x[0], self.x[1]
        for i in range(m):
            ax, ay = anchors[i]
            dx = x_est - ax
            dy = y_est - ay
            ri = math.sqrt(dx*dx + dy*dy)
            if ri < 1e-6:  # Evita divisione per zero
                ri = 1e-6
            hx.append(ri)
            H.append([dx/ri, dy/ri, 0.0, 0.0])
        # Innovazione: y = z - h
        y_vec = [[z_list[i] - hx[i]] for i in range(m)]
        # S = H P H^T + R
        H_mat = H
        HP = mat_mul(H_mat, self.P)
        HPHt = mat_mul(HP, mat_transpose(H_mat))
        for i in range(m):
            HPHt[i][i] += R_diag[i]**2
        S = HPHt
        # Gating: calcola la distanza di Mahalanobis y^T S^{-1} y
        try:
            S_inv = mat_inv(S)
            temp = mat_mul(mat_transpose(y_vec), S_inv)
            delta = mat_mul(temp, y_vec)[0][0]
        except Exception:
            return False, "S_inversion_failed"
        # Soglia di gating basata su chi-quadrato
        chi2_threshold = MAHAL_THR_MULT * m
        if delta > chi2_threshold:
            return False, "gating_failed"
        # Calcolo del guadagno di Kalman: K = P H^T S^{-1}
        Ht = mat_transpose(H_mat)
        PHt = mat_mul(self.P, Ht)
        K = mat_mul(PHt, S_inv)
        # Aggiornamento dello stato: x = x + K * y
        Ky = mat_mul(K, y_vec)
        self.x = [self.x[i] + Ky[i][0] for i in range(4)]
        # Aggiornamento della covarianza (forma di Joseph per stabilità)
        I = eye(4)
        KH = mat_mul(K, H_mat)
        IKH = mat_sub(I, KH)
        P_new = mat_mul(mat_mul(IKH, self.P), mat_transpose(IKH))
        KR = [[0.0]*m for _ in range(4)]
        for i in range(4):
            for j in range(m):
                KR[i][j] = K[i][j] * (R_diag[j]**2)
        KRKt = mat_mul(KR, mat_transpose(K))
        self.P = mat_add(P_new, KRKt)
        return True, {"delta": delta}

    def get_state(self):
        """
        Restituisce lo stato attuale del filtro.
        Returns:
            tuple: [x, y, vx, vy]
        """
        return tuple(self.x)

    def set_state(self, x0, P0=None):
        """
        Imposta lo stato e, opzionalmente, la covarianza.
        Args:
            x0: Nuovo stato [x, y, vx, vy]
            P0: Nuova matrice di covarianza (opzionale)
        """
        self.x = list(x0)
        if P0 is not None:
            self.P = [list(row) for row in P0]

# ====== Variabili globali per l'interfaccia utente ======
uwb = None  # Oggetto per il dispositivo UWB
wlan = None  # Oggetto per la connessione Wi-Fi
ma_buffers = []  # Buffer per la media mobile per ogni ancora
ekf = None  # Oggetto per il filtro di Kalman
dist_prefix = [None] * 4  # Etichette per le distanze nell'interfaccia
dist_value = [None] * 4  # Valori delle distanze nell'interfaccia
battery_prefix = None  # Etichetta per il livello della batteria
battery_value = None  # Valore del livello della batteria
ukt_label = None  # Etichetta per lo stato UKT

# ====== Funzioni principali ======
def setup():
    """
    Inizializza l'hardware, l'interfaccia utente, il dispositivo UWB e il filtro di Kalman.
    """
    global uwb, wlan, ma_buffers, ekf, dist_prefix, dist_value, battery_prefix, battery_value, ukt_label
    M5.begin()  # Inizializza l'hardware M5Stack
    Widgets.setRotation(3)  # Imposta la rotazione dello schermo
    Widgets.fillScreen(0x000000)  # Imposta lo sfondo nero
    # Crea etichette per l'interfaccia
    Widgets.Label("UWB EKF Tag", 10, 5, 1.2, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    ukt_label = Widgets.Label("UKT", 150, 5, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    y_pos = 30
    for i in range(4):
        dist_prefix[i] = Widgets.Label(f"Dist{i}:", 10, y_pos, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
        dist_value[i] = Widgets.Label("N/A", 70, y_pos, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
        y_pos += 25
    battery_prefix = Widgets.Label("Battery:", 10, y_pos, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    battery_value = Widgets.Label("0%", 90, y_pos, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    # Inizializza il dispositivo UWB in modalità tag
    uwb = UWBUnit(2, port=(33, 32), device_mode=UWBUnit.TAG, verbose=True)
    try:
        uwb.set_measurement_interval(int(LOOP_MS))  # Imposta intervallo di misura
        uwb.set_measurement(True)  # Avvia le misurazioni
    except Exception:
        pass
    ma_buffers = [MovingAverage(MA_WINDOW) for _ in ANCHORS]  # Crea buffer per la media mobile
    ekf = EKF2D(dt=DT, sigma_a=SIGMA_A)  # Inizializza il filtro di Kalman
    connect_wifi()  # Connette alla rete Wi-Fi

def connect_wifi():
    """
    Connette il dispositivo alla rete Wi-Fi specificata.
    """
    global wlan
    wlan = network.WLAN(network.STA_IF)  # Inizializza l'interfaccia Wi-Fi in modalità station
    wlan.active(False)  # Disattiva temporaneamente
    time.sleep(0.5)
    wlan.active(True)  # Riattiva
    if wlan.isconnected():
        wlan.disconnect()  # Disconnette se già connesso
        time.sleep(0.5)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)  # Connette alla rete
    t0 = time.time()
    while not wlan.isconnected():
        time.sleep(0.2)
        if time.time() - t0 > 15:  # Timeout di 15 secondi
            print("Wi-Fi timeout, continuing without network")
            return
    print("Wi-Fi connected:", wlan.ifconfig())  # Stampa informazioni di connessione

def read_raw_distances():
    """
    Legge le distanze grezze dal dispositivo UWB.
    Returns:
        list: Lista di 4 distanze (None per misurazioni mancanti)
    """
    d = []
    for i in range(len(ANCHORS)):
        try:
            di = uwb.get_distance(i)  # Legge distanza per l'ancora i
            if di is None:
                d.append(None)
            else:
                d.append(float(di))
        except Exception:
            d.append(None)
    return d

def read_quality_if_available(idx):
    """
    Legge la qualità del segnale (CIR/SNR) per l'ancora specificata, se disponibile.
    Args:
        idx: Indice dell'ancora
    Returns:
        float or None: Valore di qualità o None se non disponibile
    """
    try:
        if hasattr(uwb, "get_quality"):
            q = uwb.get_quality(idx)
            return q
        if hasattr(uwb, "get_cir"):
            return uwb.get_cir(idx)
    except Exception:
        pass
    return None

def trilateration_linear(dists, anchors):
    """
    Esegue la trilaterazione lineare usando un'ancora di riferimento.
    Args:
        dists: Lista delle distanze (con None per valori mancanti)
        anchors: Lista delle coordinate delle ancore
    Returns:
        tuple: (x, y) se calcolabile, None altrimenti
    """
    valid = [(i, dists[i], anchors[i]) for i in range(len(dists)) if dists[i] is not None]
    if len(valid) < MIN_ANCHORS_FOR_POS:
        return None
    idxs = [v[0] for v in valid]
    ref_idx = idxs[-1]
    x4, y4 = anchors[ref_idx]
    d4 = dists[ref_idx]
    rows = []
    bs = []
    for (i, di, (xi, yi)) in valid:
        if i == ref_idx:
            continue
        Ai = [2*(x4 - xi), 2*(y4 - yi)]
        bi = (di**2 - d4**2 - xi**2 + x4**2 - yi**2 + y4**2)
        rows.append(Ai)
        bs.append([bi])
    At = mat_transpose(rows)
    AtA = mat_mul(At, rows)
    Atb = mat_mul(At, bs)
    try:
        sol = solve_linear(AtA, [Atb[0][0], Atb[1][0]])
        return sol[0], sol[1]
    except Exception:
        return None

def adaptive_R_from_quality(qualities):
    """
    Calcola la deviazione standard delle misurazioni in base alla qualità del segnale.
    Args:
        qualities: Lista dei valori di qualità (o None)
    Returns:
        list: Lista delle deviazioni standard per ogni ancora
    """
    R = []
    for q in qualities:
        if q is None:
            R.append(SIGMA_R_DEFAULT)
        else:
            try:
                qf = float(q)
                if qf >= 80:
                    R.append(0.12)  # Qualità alta: deviazione bassa
                elif qf <= 30:
                    R.append(0.6)   # Qualità bassa: deviazione alta
                else:
                    s = (qf - 30.0) / (80.0 - 30.0)
                    R.append(0.6*(1-s) + 0.12*s)  # Interpolazione lineare
            except Exception:
                R.append(SIGMA_R_DEFAULT)
    return R

def main_loop():
    """
    Ciclo principale per il tracking UWB con EKF.
    """
    global ekf
    last_trilat_time = 0
    while True:
        t_loop = time.ticks_ms()  # Tempo di inizio del ciclo
        M5.update()  # Aggiorna lo stato dell'hardware M5Stack
        uwb.update()  # Aggiorna lo stato del dispositivo UWB
        # Legge le distanze grezze
        raw_d = read_raw_distances()
        # Legge la qualità del segnale
        qualities = [read_quality_if_available(i) for i in range(len(ANCHORS))]
        # Applica la media mobile alle distanze
        filtered = [None]*len(ANCHORS)
        for i, val in enumerate(raw_d):
            if val is not None and (not math.isfinite(val) or val <= 0.0):
                val = None
            if val is not None:
                ma_buffers[i].add(val)
            if ma_buffers[i].ready():
                filtered[i] = ma_buffers[i].mean()
            else:
                filtered[i] = None
        # Aggiorna l'interfaccia utente
        for i in range(4):
            val = filtered[i]
            if val is None:
                dist_value[i].setText("N/A")
            else:
                dist_value[i].setText(f"{val:.2f}")
        battery_value.setText(f"{M5.Power.getBatteryLevel()}%")
        # Esegue la trilaterazione per ottenere una stima iniziale
        trilat = trilateration_linear(filtered, ANCHORS)
        # Inizializza o aggiorna l'EKF con la trilaterazione
        if trilat is not None and (ekf is not None):
            x_t, y_t = trilat
            if ekf.P[0][0] > 5.0 or (time.time() - last_trilat_time) > 5.0:
                ekf.x[0] = x_t
                ekf.x[1] = y_t
                ekf.x[2] = 0.0
                ekf.x[3] = 0.0
                ekf.P[0][0] = 0.5; ekf.P[1][1] = 0.5
                last_trilat_time = time.time()
        # Esegue la predizione dell'EKF
        try:
            ekf.predict()
        except Exception as e:
            print("EKF predict error:", e)
        # Esegue l'aggiornamento delle misurazioni se sufficienti
        present_idxs = [i for i, d in enumerate(filtered) if d is not None]
        if len(present_idxs) >= MIN_ANCHORS_FOR_POS:
            z_list = [filtered[i] for i in present_idxs]
            anchors_sub = [ANCHORS[i] for i in present_idxs]
            qualities_sub = [qualities[i] for i in present_idxs]
            R_diag = adaptive_R_from_quality(qualities_sub)
            pred_ranges = ekf.get_predicted_ranges(anchors_sub)
            for j in range(len(z_list)):
                if pred_ranges[j] is not None:
                    if abs(z_list[j] - pred_ranges[j]) > 1.2:
                        R_diag[j] = max(R_diag[j], 1.0)
            try:
                ok, info = ekf.update_with_ranges(z_list, anchors_sub, R_diag)
                if not ok:
                    if info == "gating_failed":
                        R_diag2 = [r*4.0 for r in R_diag]
                        try:
                            ok2, info2 = ekf.update_with_ranges(z_list, anchors_sub, R_diag2)
                            if not ok2:
                                print("EKF update still rejected:", info2)
                        except Exception as e:
                            print("EKF update retry error:", e)
                    else:
                        print("EKF update rejected:", info)
            except Exception as e:
                print("EKF update exception:", e)
        # Ottiene lo stato finale e invia i dati
        x, y, vx, vy = ekf.get_state()
        print("POS: {:.3f},{:.3f} V: {:.3f},{:.3f}".format(x, y, vx, vy))
        # Prepara il payload per il server
        payload = {
            "x": x, "y": y,
            "dist0": filtered[0],
            "dist1": filtered[1],
            "dist2": filtered[2],
            "dist3": filtered[3]
        }
        # Invia il payload al server
        try:
            resp = requests.post(SERVER_URL, json=payload, timeout=1.0)
            resp.close()
        except Exception as e:
            pass
        # Controlla il tempo di ciclo
        t_elapsed = time.ticks_diff(time.ticks_ms(), t_loop)
        sleep_ms = max(10, LOOP_MS - t_elapsed)
        time.sleep_ms(sleep_ms)

if __name__ == "__main__":
    try:
        setup()
        main_loop()
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as e:
        print("Fatal error:", e)
