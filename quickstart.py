import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# SCOPE AGGIORNATO: permette all'app di creare, modificare e caricare file
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    """
    Gestisce l'autenticazione a Google Drive in automatico.
    Se il token non esiste, apre il browser per il login.
    Ritorna l'oggetto 'service' pronto per caricare i file.
    """
    creds = None
    
    # Il file token.json viene salvato e cercato nella cartella in cui si trova l'eseguibile,
    # in questo modo non si perde al riavvio del PC.
    token_path = "token.json"
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    # Se non ci sono credenziali valide, avvia il flusso di login tramite browser
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ricerca intelligente del file credentials.json (funziona sia su Python normale che su .exe)
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            
            creds_path = os.path.join(base_path, "credentials.json")
            
            if not os.path.exists(creds_path):
                print("ERRORE CRITICO: File credentials.json non trovato!")
                return None
            
            # Apre il browser per chiedere l'autorizzazione all'utente
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Salva le credenziali aggiornate per la prossima volta
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        # Crea e ritorna il servizio Drive API
        service = build("drive", "v3", credentials=creds)
        return service
    except HttpError as error:
        print(f"Errore di connessione alle API di Google Drive: {error}")
        return None
