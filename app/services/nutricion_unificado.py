"""
Flujo unificado de búsqueda de alimentos:
  1. Redis (caché) ~0.001s
  2. PostgreSQL (alimentos)
  3. APIs en PARALELO (Open Food Facts, USDA) → guardar en Redis + PG
  4. Si no hay dato: LLM estima → marcar "estimado" → guardar en Redis + PG

Siempre que se calcula/obtiene un resultado, se guarda con consulta_id en Redis 10 min
para que al confirmar el usuario se usen los MISMOS valores (anti-inconsistencia).
"""
import asyncio
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.cache import (
    get_cached,
    set_cached,
    set_consulta_cached,
    get_consulta_cached,
    cache_key_alimento,
)
from app.models.alimento import Alimento


def _normalizar_nombre(nombre: str) -> str:
    if not nombre:
        return ""
    n = nombre.lower().strip()
    n = re.sub(r"\s+", " ", n)
    return n


def _dict_from_alimento(row: Alimento) -> dict:
    """Convierte fila Alimento a dict estándar de macros."""
    return {
        "nombre": row.nombre,
        "alimento": row.nombre,
        "marca": row.marca or "Genérico",
        "origen": row.origen or "PostgreSQL",
        "calorias": float(row.calorias),
        "proteinas": float(row.proteinas_g),
        "carbohidratos": float(row.carbohidratos_g),
        "grasas": float(row.grasas_g),
        "fibra": float(row.fibra_g) if row.fibra_g is not None else None,
        "azucares": float(row.azucares_g) if row.azucares_g is not None else None,
        "grasas_saturadas": float(row.grasas_saturadas_g) if row.grasas_saturadas_g is not None else None,
        "sodio_mg": float(row.sodio_mg) if row.sodio_mg is not None else None,
        "colesterol_mg": float(row.colesterol_mg) if row.colesterol_mg is not None else None,
        "calcio_mg": float(row.calcio_mg) if row.calcio_mg is not None else None,
        "hierro_mg": float(row.hierro_mg) if row.hierro_mg is not None else None,
        "vitamina_c_mg": float(row.vitamina_c_mg) if row.vitamina_c_mg is not None else None,
        "vitamina_d_ug": float(row.vitamina_d_ug) if row.vitamina_d_ug is not None else None,
        "potasio_mg": float(row.potasio_mg) if row.potasio_mg is not None else None,
        "es_estimado": bool(row.es_estimado),
    }


async def _fetch_open_food_facts(nombre: str) -> Optional[dict]:
    """Open Food Facts (productos, Perú). Retorna dict estándar o None."""
    try:
        import httpx
        query = nombre.replace(" ", "%20")[:80]
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&countries=Peru&page_size=1"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            products = data.get("products") or []
            if not products:
                return None
            p = products[0]
            nutriments = p.get("nutriments") or {}
            # Por 100g
            cal = nutriments.get("energy-kcal_100g") or nutriments.get("energy_100g")
            if cal is None and nutriments.get("energy-kcal"):
                cal = nutriments.get("energy-kcal")
            if cal is None:
                return None
            return {
                "nombre": p.get("product_name") or nombre,
                "marca": p.get("brands") or "Genérico",
                "origen": "open_food_facts",
                "calorias": float(cal),
                "proteinas_g": float(nutriments.get("proteins_100g") or 0),
                "carbohidratos_g": float(nutriments.get("carbohydrates_100g") or 0),
                "grasas_g": float(nutriments.get("fat_100g") or 0),
                "fibra_g": nutriments.get("fiber_100g"),
                "azucares_g": nutriments.get("sugars_100g"),
                "grasas_saturadas_g": nutriments.get("saturated-fat_100g"),
                "sodio_mg": (nutriments.get("sodium_100g") or 0) * 1000 if nutriments.get("sodium_100g") is not None else None,
                "colesterol_mg": None,
                "calcio_mg": (nutriments.get("calcium_100g") or 0) * 1000 if nutriments.get("calcium_100g") is not None else None,
                "hierro_mg": (nutriments.get("iron_100g") or 0) * 1000 if nutriments.get("iron_100g") is not None else None,
                "vitamina_c_mg": None,
                "vitamina_d_ug": None,
                "potasio_mg": (nutriments.get("potassium_100g") or 0) * 1000 if nutriments.get("potassium_100g") is not None else None,
                "es_estimado": False,
            }
    except Exception:
        return None


async def _fetch_usda(nombre: str) -> Optional[dict]:
    """USDA API (ingredientes base). Requiere API key en env USDA_API_KEY. Retorna dict estándar o None."""
    import os
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        return None
    try:
        import httpx
        query = nombre.replace(" ", "%20")[:80]
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}&query={query}&pageSize=1"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            foods = data.get("foods") or []
            if not foods:
                return None
            f = foods[0]
            nutrients = {n["nutrientName"]: n.get("value") for n in f.get("foodNutrients") or []}
            cal = nutrients.get("Energy") or 0
            return {
                "nombre": f.get("description") or nombre,
                "marca": "USDA",
                "origen": "usda",
                "calorias": float(cal),
                "proteinas_g": float(nutrients.get("Protein") or 0),
                "carbohidratos_g": float(nutrients.get("Carbohydrates") or 0),
                "grasas_g": float(nutrients.get("Total lipid (fat)") or 0),
                "fibra_g": nutrients.get("Fiber, total dietary"),
                "azucares_g": nutrients.get("Sugars, total"),
                "grasas_saturadas_g": nutrients.get("Fatty acids, total saturated"),
                "sodio_mg": nutrients.get("Sodium"),
                "colesterol_mg": nutrients.get("Cholesterol"),
                "calcio_mg": nutrients.get("Calcium, Ca"),
                "hierro_mg": nutrients.get("Iron, Fe"),
                "vitamina_c_mg": nutrients.get("Vitamin C, total ascorbic acid"),
                "vitamina_d_ug": None,
                "potasio_mg": nutrients.get("Potassium, K"),
                "es_estimado": False,
            }
    except Exception:
        return None


async def _apis_paralelo(nombre: str) -> Optional[dict]:
    """Llama Open Food Facts y USDA en paralelo; retorna el primero que tenga resultado."""
    off, usda = await asyncio.gather(
        _fetch_open_food_facts(nombre),
        _fetch_usda(nombre),
    )
    return off or usda


def _guardar_alimento_en_db(db: Session, data: dict, nombre_norm: str) -> Optional[Alimento]:
    """Persiste un alimento en PostgreSQL (evitar duplicados por nombre_normalizado)."""
    existing = db.query(Alimento).filter(Alimento.nombre_normalizado == nombre_norm).first()
    if existing:
        return existing
    a = Alimento(
        nombre=data.get("nombre") or data.get("alimento", "Desconocido"),
        nombre_normalizado=nombre_norm,
        marca=data.get("marca"),
        origen=data.get("origen", "api"),
        calorias=float(data["calorias"]),
        proteinas_g=float(data.get("proteinas_g") or data.get("proteinas", 0)),
        carbohidratos_g=float(data.get("carbohidratos_g") or data.get("carbohidratos", 0)),
        grasas_g=float(data.get("grasas_g") or data.get("grasas", 0)),
        fibra_g=data.get("fibra_g") or data.get("fibra"),
        azucares_g=data.get("azucares_g") or data.get("azucares"),
        grasas_saturadas_g=data.get("grasas_saturadas_g") or data.get("grasas_saturadas"),
        sodio_mg=data.get("sodio_mg") or data.get("sodio"),
        colesterol_mg=data.get("colesterol_mg") or data.get("colesterol"),
        calcio_mg=data.get("calcio_mg") or data.get("calcio"),
        hierro_mg=data.get("hierro_mg") or data.get("hierro"),
        vitamina_c_mg=data.get("vitamina_c_mg") or data.get("vitamina_c"),
        vitamina_d_ug=data.get("vitamina_d_ug") or data.get("vitamina_d"),
        potasio_mg=data.get("potasio_mg") or data.get("potasio"),
        es_estimado=bool(data.get("es_estimado", False)),
        porcion_por_defecto_g=100.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _alimento_to_respuesta(data: dict, consulta_id: Optional[str] = None) -> dict:
    """Formato de respuesta estándar para el frontend (incluye consulta_id para consistencia)."""
    out = {
        "nombre": data.get("nombre") or data.get("alimento"),
        "alimento": data.get("nombre") or data.get("alimento"),
        "marca": data.get("marca", "Genérico"),
        "origen": data.get("origen", "api"),
        "calorias": float(data.get("calorias", 0)),
        "proteinas": float(data.get("proteinas_g") or data.get("proteinas", 0)),
        "carbohidratos": float(data.get("carbohidratos_g") or data.get("carbohidratos", 0)),
        "grasas": float(data.get("grasas_g") or data.get("grasas", 0)),
        "azucares": data.get("azucares_g") or data.get("azucares"),
        "fibra": data.get("fibra_g") or data.get("fibra"),
        "sodio": data.get("sodio_mg") or data.get("sodio"),
        "grasas_saturadas": data.get("grasas_saturadas_g") or data.get("grasas_saturadas"),
        "es_estimado": bool(data.get("es_estimado", False)),
    }
    if consulta_id:
        out["consulta_id"] = consulta_id
    return out


async def buscar_alimento_unificado(
    nombre: str,
    db: Session,
    generar_consulta_id: bool = True,
) -> Optional[dict]:
    """
    Flujo: Redis → PG → APIs paralelo → (opcional) LLM estimado.
    Si se genera resultado nuevo, se guarda en Redis con consulta_id 10 min para consistencia al confirmar.
    Retorna dict con macros + consulta_id (si aplica), o None si no hay dato ni estimación.
    """
    nombre_norm = _normalizar_nombre(nombre)
    if not nombre_norm:
        return None

    # 1. Redis
    ck = cache_key_alimento(nombre_norm)
    cached = get_cached(ck)
    if cached:
        consulta_id = cached.pop("consulta_id", None)
        return _alimento_to_respuesta(cached, consulta_id)

    # 2. PostgreSQL
    row = db.query(Alimento).filter(Alimento.nombre_normalizado == nombre_norm).first()
    if not row:
        row = db.query(Alimento).filter(Alimento.nombre.ilike(f"%{nombre_norm}%")).first()
    if row:
        data = _dict_from_alimento(row)
        set_cached(ck, data)
        return _alimento_to_respuesta(data, None)

    # 3. APIs en paralelo
    api_result = await _apis_paralelo(nombre_norm)
    if api_result:
        api_result["nombre_normalizado"] = nombre_norm
        _guardar_alimento_en_db(db, api_result, nombre_norm)
        set_cached(ck, api_result)
        if generar_consulta_id:
            consulta_id = str(uuid.uuid4())
            payload = _alimento_to_respuesta(api_result, consulta_id)
            set_consulta_cached(consulta_id, payload)
            return payload
        return _alimento_to_respuesta(api_result, None)

    # 4. LLM estimado: delegar al NutricionService existente o ia_service (mantener compatibilidad)
    # Para no romper el flujo actual, aquí retornamos None y el caller puede usar el servicio legacy.
    # Cuando integres del todo, aquí llamarías al LLM, marcarías es_estimado=True y guardarías en PG+Redis.
    return None


def recuperar_por_consulta_id(consulta_id: str) -> Optional[dict]:
    """Para cuando el usuario confirma: recuperar los MISMOS valores de Redis (no recalcular)."""
    return get_consulta_cached(consulta_id)
