"""
Seed inicial: poblar tablas alimentos y ejercicios desde JSONs locales.
Ejecutar desde raíz del backend: python -m scripts.seed_inicial
Requiere: DATABASE_URL, tablas creadas (alembic upgrade head).
"""
import os
import sys
import json
import unicodedata

# Raíz del proyecto backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.alimento import Alimento
from app.models.ejercicio import Ejercicio


def normalizar(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s


def seed_alimentos(db: Session, data_dir: str) -> int:
    count = 0
    # INS
    path_ins = os.path.join(data_dir, "alimentos_peru_ins.json")
    if os.path.exists(path_ins):
        with open(path_ins, "r", encoding="utf-8") as f:
            lista = json.load(f)
        for item in lista:
            nombre = item.get("alimento") or item.get("nombre")
            if not nombre:
                continue
            nombre_norm = normalizar(nombre)
            if db.query(Alimento).filter(Alimento.nombre_normalizado == nombre_norm).first():
                continue
            cal = item.get("calorias_100g") or item.get("calorias") or 0
            p = item.get("proteina_100g") or item.get("proteinas") or 0
            c = item.get("carbohindratos_100g") or item.get("carbohidratos") or 0
            g = item.get("grasas_100g") or item.get("grasas") or 0
            a = Alimento(
                nombre=nombre,
                nombre_normalizado=nombre_norm,
                marca="Genérico",
                origen="ins",
                calorias=float(cal),
                proteinas_g=float(p),
                carbohidratos_g=float(c),
                grasas_g=float(g),
                fibra_g=item.get("fibra_100g") or item.get("fibra"),
                azucares_g=item.get("azucar_100g") or item.get("azucares"),
                grasas_saturadas_g=None,
                sodio_mg=None,
                colesterol_mg=None,
                calcio_mg=None,
                hierro_mg=None,
                vitamina_c_mg=None,
                vitamina_d_ug=None,
                potasio_mg=None,
                es_estimado=False,
                porcion_por_defecto_g=100.0,
            )
            db.add(a)
            count += 1
        print(f"[Seed] Alimentos INS: {count} insertados")
    return count


def seed_ejercicios(db: Session, data_dir: str) -> int:
    path_ej = os.path.join(data_dir, "ejercicios.json")
    count = 0
    if not os.path.exists(path_ej):
        print("[Seed] No se encontró ejercicios.json")
        return 0
    with open(path_ej, "r", encoding="utf-8") as f:
        lista = json.load(f)
    for item in lista:
        nombre = item.get("nombre")
        if not nombre:
            continue
        nombre_norm = normalizar(nombre)
        if db.query(Ejercicio).filter(Ejercicio.nombre_normalizado == nombre_norm).first():
            continue
        alias = item.get("alias")
        alias_str = json.dumps(alias, ensure_ascii=False) if isinstance(alias, list) else (alias or "")
        grupo = item.get("grupo_muscular")
        grupo_str = ", ".join(grupo) if isinstance(grupo, list) else (grupo or "")
        e = Ejercicio(
            nombre=nombre,
            nombre_normalizado=nombre_norm,
            alias=alias_str,
            descripcion=item.get("tecnica"),
            met=float(item.get("met", 3.0)),
            grupo_muscular=grupo_str[:128] if grupo_str else None,
            origen=item.get("origen", "dataset_importado"),
        )
        db.add(e)
        count += 1
    print(f"[Seed] Ejercicios: {count} insertados")
    return count


def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "data")
    db = SessionLocal()
    try:
        a = seed_alimentos(db, data_dir)
        e = seed_ejercicios(db, data_dir)
        db.commit()
        print(f"[Seed] Total: {a} alimentos, {e} ejercicios")
    except Exception as ex:
        db.rollback()
        print(f"[Seed] Error: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
