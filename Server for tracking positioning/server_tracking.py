# Importazione delle librerie necessarie
from flask import Flask, request, jsonify  # Flask per creare un server web API, request per gestire le richieste, jsonify per risposte JSON
import datetime  # Per generare timestamp nel formato ISO
import os  # Per operazioni sul file system (es. verifica esistenza file)
import csv  # Per gestire la scrittura su file CSV

# Creazione dell'istanza dell'applicazione Flask
app = Flask(__name__)

# ====== Configurazioni ======
LOG_FILE = 'tracking_log.csv'  # Nome del file CSV per registrare i dati
CSV_HEADER = ['timestamp', 'dist0', 'dist1', 'dist2', 'dist3', 'x', 'y']  # Intestazione del file CSV con i campi attesi

# ====== Funzioni di supporto ======
def ensure_header():
    """
    Crea il file CSV con l'intestazione se non esiste o è vuoto.
    """
    # Controlla se il file non esiste o è vuoto (dimensione 0)
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, 'w', newline='') as f:  # Apre il file in modalità scrittura
            writer = csv.writer(f)  # Crea un oggetto writer per il CSV
            writer.writerow(CSV_HEADER)  # Scrive l'intestazione definita

# ====== Endpoint Flask ======
@app.route('/log', methods=['POST'])
def log_data():
    """
    Endpoint POST per ricevere e registrare dati di tracking in un file CSV.
    Aspetta un payload JSON con i campi dist0, dist1, dist2, dist3, x, y.
    Restituisce una risposta JSON con lo stato dell'operazione.
    """
    ensure_header()  # Assicura che il file CSV abbia l'intestazione
    # Estrae i dati JSON dalla richiesta (silent=True evita errori se JSON non valido)
    data = request.get_json(silent=True) or {}
    # Valida la presenza dei campi obbligatori
    required = ['dist0', 'dist1', 'dist2', 'dist3', 'x', 'y']
    missing = [k for k in required if k not in data]  # Trova eventuali campi mancanti
    if missing:  # Se mancano campi, restituisce errore
        return jsonify({'status': 'error', 'missing': missing}), 400
    try:
        # Crea una riga per il CSV, convertendo i valori in float dove necessario
        row = [
            datetime.datetime.now().isoformat(),  # Timestamp corrente in formato ISO
            float(data['dist0']) if data['dist0'] is not None else '',  # Converte dist0 in float o lascia vuoto
            float(data['dist1']) if data['dist1'] is not None else '',  # Converte dist1 in float o lascia vuoto
            float(data['dist2']) if data['dist2'] is not None else '',  # Converte dist2 in float o lascia vuoto
            float(data['dist3']) if data['dist3'] is not None else '',  # Converte dist3 in float o lascia vuoto
            float(data['x']),  # Converte x in float
            float(data['y']),  # Converte y in float
        ]
    except (TypeError, ValueError):  # Gestisce errori di conversione numerica
        return jsonify({'status': 'error', 'message': 'invalid numeric payload'}), 400
    # Scrive la riga nel file CSV
    with open(LOG_FILE, 'a', newline='') as f:  # Apre il file in modalità append
        writer = csv.writer(f)  # Crea un oggetto writer per il CSV
        writer.writerow(row)  # Scrive la riga con i dati
    # Restituisce una risposta di successo
    return jsonify({'status': 'ok'}), 200

# ====== Esecuzione principale ======
if __name__ == '__main__':
    # Avvia il server Flask
    # Host 0.0.0.0 consente connessioni da qualsiasi indirizzo, porta 5050 per compatibilità con SERVER_URL
    app.run(host='0.0.0.0', port=5050)
