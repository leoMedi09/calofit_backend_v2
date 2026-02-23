"""
Modelo de alimentos en PostgreSQL.
Macros: principales siempre; secundarios y micronutrientes cuando la API los tiene (NULL si no).
No inventar valores nunca.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Alimento(Base):
    __tablename__ = "alimentos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    nombre_normalizado = Column(String(255), nullable=False, index=True)  # lower, sin acentos para búsqueda
    marca = Column(String(255), nullable=True)
    origen = Column(String(64), nullable=True)  # "open_food_facts", "usda", "ins", "estimado_llm"

    # Macros principales (siempre presentes)
    calorias = Column(Float, nullable=False)
    proteinas_g = Column(Float, nullable=False)
    carbohidratos_g = Column(Float, nullable=False)
    grasas_g = Column(Float, nullable=False)

    # Macros secundarios (NULL si la API no los tiene)
    fibra_g = Column(Float, nullable=True)
    azucares_g = Column(Float, nullable=True)
    grasas_saturadas_g = Column(Float, nullable=True)
    sodio_mg = Column(Float, nullable=True)
    colesterol_mg = Column(Float, nullable=True)

    # Micronutrientes (NULL si no disponibles)
    calcio_mg = Column(Float, nullable=True)
    hierro_mg = Column(Float, nullable=True)
    vitamina_c_mg = Column(Float, nullable=True)
    vitamina_d_ug = Column(Float, nullable=True)
    potasio_mg = Column(Float, nullable=True)

    # Si fue estimado por LLM (no inventar; marcar para transparencia)
    es_estimado = Column(Boolean, default=False)
    porcion_por_defecto_g = Column(Float, nullable=True)  # ej. 100

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
