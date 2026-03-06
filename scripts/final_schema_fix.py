from app.core.database import engine
from sqlalchemy import text

commands = [
    # 1. Clean up potential wrong columns in Alimentos 
    "ALTER TABLE preferencias_alimentos DROP COLUMN IF EXISTS calorias_quemadas;",
    
    # 2. Add correct columns to Alimentos (Food)
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS calorias FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS proteinas FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS carbohidratos FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS grasas FLOAT DEFAULT 0.0;",
    
    # 3. Add correct column to Ejercicios (Exercise)
    "ALTER TABLE preferencias_ejercicios ADD COLUMN IF NOT EXISTS calorias_quemadas FLOAT DEFAULT 0.0;",
    
    # 4. Clean up Alimento column if it mistakenly exists in Ejercicios (sanity check)
    "ALTER TABLE preferencias_ejercicios DROP COLUMN IF EXISTS calorias;",
    "ALTER TABLE preferencias_ejercicios DROP COLUMN IF EXISTS proteinas;",
    "ALTER TABLE preferencias_ejercicios DROP COLUMN IF EXISTS carbohidratos;",
    "ALTER TABLE preferencias_ejercicios DROP COLUMN IF EXISTS grasas;"
]

print("🛠️ Executing final schema fix...")
with engine.begin() as conn:
    for cmd in commands:
        try:
            conn.execute(text(cmd))
            print(f"✅ Success: {cmd}")
        except Exception as e:
            print(f"❌ Error: {cmd} -> {e}")

print("✅ Schema fix complete.")
