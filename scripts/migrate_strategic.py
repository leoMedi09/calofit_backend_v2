from app.core.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Agregando columnas estratégicas...")
        conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS ai_strategic_focus TEXT;"))
        conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS recommended_foods TEXT[];"))
        conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS forbidden_foods TEXT[];"))
        conn.commit()
    print("Migración completada exitosamente.")

if __name__ == "__main__":
    migrate()
