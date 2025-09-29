# Importazione delle librerie necessarie
from flask import Flask, request, jsonify # Flask per creare un server web API, request per gestire le richieste, jsonify per risposte JSON
import datetime # Per generare timestamp nel formato ISO
import os # Per operazioni sul file system (es. verifica esistenza file)
import csv # Per gestire la scrittura su file CSV
# Creazione dell'istanza dell'applicazione Flask
app = Flask(__name__)
# ====== Configurazioni ======
LOG_FILE_RAW = 'tracking_log.csv' # Nome del file CSV per i dati senza stabilizzazione
LOG_FILE_FILTERED = 'tracking_log_filtered.csv' # Nome del file CSV per i dati con stabilizzazione
CSV_HEADER = ['timestamp', 'dist0', 'dist1', 'dist2', 'dist3', 'x', 'y'] # Intestazione del file CSV con i campi attesi
# ====== Funzioni di supporto ======
def ensure_header(file_path):
    """
    Crea il file CSV con l'intestazione se non esiste o è vuoto.
    """
    # Controlla se il file non esiste o è vuoto (dimensione 0)
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        with open(file_path, 'w', newline='') as f: # Apre il file in modalità scrittura
            writer = csv.writer(f) # Crea un oggetto writer per il CSV
            writer.writerow(CSV_HEADER) # Scrive l'intestazione definita

def log_data_generic(file_path):
    """
    Funzione generica per registrare dati in un file CSV specifico.
    """
    ensure_header(file_path) # Assicura che il file CSV abbia l'intestazione
    # Estrae i dati JSON dalla richiesta (silent=True evita errori se JSON non valido)
    data = request.get_json(silent=True) or {}
    # Valida la presenza dei campi obbligatori
    required = ['dist0', 'dist1', 'dist2', 'dist3', 'x', 'y']
    missing = [k for k in required if k not in data] # Trova eventuali campi mancanti
    if missing: # Se mancano campi, restituisce errore
        return jsonify({'status': 'error', 'missing': missing}), 400
    try:
        # Crea una riga per il CSV, convertendo i valori in float dove necessario
        row = [
            datetime.datetime.now().isoformat(), # Timestamp corrente in formato ISO
            float(data['dist0']) if data['dist0'] is not None else '', # Converte dist0 in float o lascia vuoto
            float(data['dist1']) if data['dist1'] is not None else '', # Converte dist1 in float o lascia vuoto
            float(data['dist2']) if data['dist2'] is not None else '', # Converte dist2 in float o lascia vuoto
            float(data['dist3']) if data['dist3'] is not None else '', # Converte dist3 in float o lascia vuoto
            float(data['x']), # Converte x in float
            float(data['y']), # Converte y in float
        ]
    except (TypeError, ValueError): # Gestisce errori di conversione numerica
        return jsonify({'status': 'error', 'message': 'invalid numeric payload'}), 400
    # Scrive la riga nel file CSV
    with open(file_path, 'a', newline='') as f: # Apre il file in modalità append
        writer = csv.writer(f) # Crea un oggetto writer per il CSV
        writer.writerow(row) # Scrive la riga con i dati
    # Restituisce una risposta di successo
    return jsonify({'status': 'ok'}), 200

# ====== Endpoint Flask ======
@app.route('/log', methods=['POST'])
def log_data_raw():
    """
    Endpoint POST per i dati senza stabilizzazione (salva in tracking_log.csv).
    """
    return log_data_generic(LOG_FILE_RAW)

@app.route('/log_filtered', methods=['POST'])
def log_data_filtered():
    """
    Endpoint POST per i dati con stabilizzazione (salva in tracking_log_filtered.csv).
    """
    return log_data_generic(LOG_FILE_FILTERED)

# ====== Esecuzione principale ======
if __name__ == '__main__':
    # Avvia il server Flask
    # Host 0.0.0.0 consente connessioni da qualsiasi indirizzo, porta 5050 per compatibilità con SERVER_URL
    app.run(host='0.0.0.0', port=5050)
