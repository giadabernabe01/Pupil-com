import os
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
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
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