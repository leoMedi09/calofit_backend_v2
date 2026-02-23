from app.core.database import SessionLocal
from app.models.client import Client
from app.models.user import User

def assign_client_to_nutri():
    db = SessionLocal()
    try:
        # Buscar al Nutricionista (nutri@calofit.com)
        nutri = db.query(User).filter(User.email == "nutri@calofit.com").first()
        if not nutri:
            print("❌ Nutricionista no encontrado")
            return

        # Buscar al primer cliente disponible
        client = db.query(Client).first()
        if not client:
            print("❌ No hay clientes registrados")
            return

        # Asignar
        client.assigned_nutri_id = nutri.id
        db.commit()
        print(f"✅ Cliente '{client.first_name}' asignado exitosamente al Nutricionista '{nutri.first_name}'")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    assign_client_to_nutri()
