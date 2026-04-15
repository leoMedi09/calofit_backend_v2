from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Intento de URL fallback si no está en env
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/calofit"

print(f"Connecting to {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Adding 'dni' column to 'clients' table...")
    try:
        conn.execute(text("ALTER TABLE clients ADD COLUMN dni VARCHAR UNIQUE;"))
        conn.commit()
        print("✅ Column 'dni' added successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
        if "already exists" in str(e):
            print("The column might already exist.")
