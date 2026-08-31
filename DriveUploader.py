import os
import sys
import pickle
from PyQt5.QtCore import QThread, pyqtSignal
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Standalone function to get Google Drive service."""
    creds = None
    token_path = 'token.pickle'
    
    # Controlla se il token esiste già nella cartella corrente
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    # Se non ci sono credenziali valide, avvia il login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # --- LOGICA PER PYINSTALLER ---
            # Cerca credentials.json nella cartella temporanea dell'exe (MEIPASS) o nella cartella normale
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            
            creds_path = os.path.join(base_path, 'credentials.json')
            
            if not os.path.exists(creds_path):
                raise FileNotFoundError("ERRORE: File credentials.json non trovato!")
            
            # Avvia il server locale per l'autenticazione dal browser
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Salva le credenziali per il prossimo riavvio nella cartella dell'utente
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def create_drive_folder(folder_name, parent_id=None):
    """Creates a folder on Drive and returns its unique ID."""
    service = get_drive_service()
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    # Execute folder creation
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

class DriveUploaderThread(QThread):
    """Thread to upload data in the Google Drive directory."""
    finished_signal = pyqtSignal(str, bool) 
    error_signal = pyqtSignal(str)

    def __init__(self, file_path, folder_id=None):
        super().__init__()
        self.file_path = file_path
        self.folder_id = folder_id

    def run(self):
        try:
            service = get_drive_service()
            file_name = os.path.basename(self.file_path)
            
            file_metadata = {'name': file_name}
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]

            mimetype = 'text/csv' if file_name.endswith('.csv') else 'image/png' if file_name.endswith('.png') else '*/*'

            media = MediaFileUpload(self.file_path, mimetype=mimetype, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            
            self.finished_signal.emit(file_name, True)
            
        except Exception as e:
            self.error_signal.emit(str(e))
