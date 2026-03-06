from app.core.database import engine
from sqlalchemy import text

def check_table(table_name):
    print(f"\n[ SCHEMA FOR: {table_name} ]")
    with engine.connect() as conn:
        try:
            # Query columns directly
            sql = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
            """
            result = conn.execute(text(sql))
            rows = result.fetchall()
            if not rows:
                print(f"  ❌ No columns found for table '{table_name}'")
            else:
                for row in rows:
                    print(f"  - {row[0]} ({row[1]}): Nullable={row[2]}, Default={row[3]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    check_table("preferencias_alimentos")
    check_table("preferencias_ejercicios")
