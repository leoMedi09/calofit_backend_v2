import os
import uuid
from datetime import datetime

# Directorio base para subidas
UPLOAD_DIR = "app/uploads/profiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class LocalStorage:
    @staticmethod
    def save_file(file_bytes: bytes, original_filename: str) -> str:
        """
        Guarda un archivo en el disco local y retorna la URL pública relativa.
        """
        extension = original_filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}_{int(datetime.utcnow().timestamp())}.{extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        # Retornamos la ruta relativa que será servida por FastAPI
        return f"/uploads/profiles/{unique_filename}"

    @staticmethod
    def get_public_url(relative_path: str) -> str:
        """
        Convierte una ruta relativa en una URL absoluta basada en la IP del servidor.
        """
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        return f"{base_url}{relative_path}"

local_storage = LocalStorage()
