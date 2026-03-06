from app.core.database import engine
from sqlalchemy import text

# Correcting the previous mistake and adding missing ones
commands = [
    # Clean up the previous error (if it exists)
    "ALTER TABLE preferencias_alimentos DROP COLUMN IF EXISTS calorias_quemadas;",
    
    # Add correct columns to Alimentos
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS calorias FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS proteinas FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS carbohidratos FLOAT DEFAULT 0.0;",
    "ALTER TABLE preferencias_alimentos ADD COLUMN IF NOT EXISTS grasas FLOAT DEFAULT 0.0;",
    
    # Add correct columns to Ejercicios
    "ALTER TABLE preferencias_ejercicios ADD COLUMN IF NOT EXISTS calorias_quemadas FLOAT DEFAULT 0.0;"
]

print("🚀 Starting corrected database migration for macros...")
with engine.begin() as conn:
    for cmd in commands:
        try:
            conn.execute(text(cmd))
            print(f"✅ Executed: {cmd}")
        except Exception as e:
            print(f"❌ Failed to execute {cmd}: {e}")
print("🏁 Migration finished.")
