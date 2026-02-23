from app.core.database import engine, Base
from app.models.historial import ProgresoCalorias, HistorialPeso, HistorialIMC, AlertaSalud

print("Iniciando creacion de tablas...")
Base.metadata.create_all(bind=engine)
print("Tablas creadas exitosamente!")
