from app.core.database import engine
from sqlalchemy import text

commands = [
    "ALTER TABLE progreso_calorias ADD COLUMN IF NOT EXISTS proteinas_consumidas FLOAT DEFAULT 0.0;",
    "ALTER TABLE progreso_calorias ADD COLUMN IF NOT EXISTS carbohidratos_consumidos FLOAT DEFAULT 0.0;",
    "ALTER TABLE progreso_calorias ADD COLUMN IF NOT EXISTS grasas_consumidas FLOAT DEFAULT 0.0;",
    "ALTER TABLE progreso_calorias ADD COLUMN IF NOT EXISTS deficit_superavit INTEGER;"
]

with engine.begin() as conn:
    for cmd in commands:
        try:
            conn.execute(text(cmd))
            print(f"✅ Executed: {cmd}")
        except Exception as e:
            print(f"❌ Failed to execute {cmd}: {e}")
