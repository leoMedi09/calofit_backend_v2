from app.core.database import SessionLocal
from app.models.client import Client

db = SessionLocal()
clients = db.query(Client).filter(Client.first_name == "Paciente").all()
for c in clients:
    db.delete(c)
db.commit()
print(f"Borrados {len(clients)} pacientes de prueba.")
