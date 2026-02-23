"""
Servicio de caché Redis para CaloFit.
Flujo: 1) Redis (~0.001s) → 2) PostgreSQL → 3) APIs externas en paralelo → 4) LLM estimado.
También guarda consulta_id para consistencia: mismo resultado al confirmar registro.
"""
import json
from typing import Any, Optional
import os

from app.core.config import settings

_redis_client = None
_CACHE_PREFIX = "calofit"
_CONSULTA_TTL = 600  # 10 min para consulta_id (mismo resultado al confirmar)
_RECENT_MEALS_TTL = 3600  # 1 hora retención para fuzzy matching
_ALIMENTO_TTL = 86400 * 7  # 7 días para alimentos en caché
_EJERCICIO_TTL = 86400 * 7  # 7 días para ejercicios


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL") or settings.REDIS_URL
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        print(f"[Cache] Redis no disponible: {e}. Cache desactivado.")
        return None


def get_cached(key: str) -> Optional[Any]:
    """Obtiene valor desde Redis. key sin prefijo; se añade _CACHE_PREFIX."""
    r = _get_redis()
    if not r:
        return None
    full_key = f"{_CACHE_PREFIX}:{key}"
    try:
        raw = r.get(full_key)
        print(f"CACHE RECV [{full_key}]: {raw}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        print(f"CACHE GET EXCEPTION [{full_key}]: {e}")
        return None


def set_cached(key: str, value: Any, ttl_seconds: int = _ALIMENTO_TTL) -> bool:
    """Guarda en Redis con TTL. Retorna True si OK."""
    r = _get_redis()
    if not r:
        return False
    full_key = f"{_CACHE_PREFIX}:{key}"
    try:
        data_str = json.dumps(value, ensure_ascii=False)
        res = r.setex(full_key, ttl_seconds, data_str)
        print(f"CACHE SAVE [{full_key}] (TTL {ttl_seconds}): -> {res} | {data_str[:50]}...")
        return True
    except Exception as e:
        print(f"CACHE SET EXCEPTION [{full_key}]: {e}")
        return False


def get_consulta_cached(consulta_id: str) -> Optional[dict]:
    """Recupera resultado de una consulta (para consistencia al confirmar)."""
    return get_cached(f"consulta:{consulta_id}")


def set_consulta_cached(consulta_id: str, payload: dict) -> bool:
    """Guarda resultado de consulta 10 min para usar los MISMOS valores al registrar."""
    return set_cached(f"consulta:{consulta_id}", payload, ttl_seconds=_CONSULTA_TTL)


def cache_key_alimento(nombre_normalizado: str) -> str:
    return f"alimento:{nombre_normalizado.lower().strip()}"


def cache_key_ejercicio(nombre_normalizado: str) -> str:
    return f"ejercicio:{nombre_normalizado.lower().strip()}"


def get_user_recent_meals(user_id: int) -> list:
    """Obtiene la lista de comidas sugeridas recientemente al usuario (para fuzzy matching)."""
    val = get_cached(f"recent_meals:{user_id}")
    print(f"CACHE DEBUG: get_user_recent_meals({user_id}) -> {val}")
    return val if val else []


def add_user_recent_meal(user_id: int, payload: dict) -> bool:
    """Agrega una comida sugerida a la lista reciente del usuario. Retiene máximo 10 comidas."""
    meals = get_user_recent_meals(user_id)
    # Evitar duplicados exactos (mismo nombre)
    meals = [m for m in meals if m.get("nombre", "").lower() != payload.get("nombre", "").lower()]
    meals.insert(0, payload)  # Insertar al inicio
    if len(meals) > 10:
        meals = meals[:10]    # Limitar a las últimas 10 opciones
    res = set_cached(f"recent_meals:{user_id}", meals, ttl_seconds=_RECENT_MEALS_TTL)
    print(f"CACHE DEBUG: add_user_recent_meal({user_id}) -> {res} (Length: {len(meals)})")
    return res
