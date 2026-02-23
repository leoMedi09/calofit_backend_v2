from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).filter(User.type == 'client').limit(10).all()
print("Clientes en la base de datos (Tabla User):")
for u in users:
    print(f"ID: {u.id} | Email: {u.email} | Tipo: {u.type} | Nombre sugerido: {u.name} {u.last_name}")
db.close()
