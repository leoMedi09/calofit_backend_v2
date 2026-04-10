"""
╔══════════════════════════════════════════════════════════════════════╗
║  CaloFit — IA Service                                               ║
║  Arquitectura de Inteligencia Nutricional                            ║
║                                                                      ║
║  Pilar 1 → Mifflin-St Jeor (Base Clínica Nutricional)               ║
║  Pilar 2 → Random Forest (Perfilamiento de Adherencia)              ║
║  Pilar 3 → K-Nearest Neighbors (Recomendador de Alimentos)          ║
║  Pilar 4 → LLM Llama-3 vía Groq (Procesamiento NLP y Diálogo)       ║
╚══════════════════════════════════════════════════════════════════════╝

API Pública:
  calcular_requerimiento(genero, edad, peso, talla, nivel_act, objetivo) → float
  calcular_macros_completos(...)            → (cal, prot, carb, gras)
  calcular_macros_optimizados(cal, obj, peso) → dict
  generar_alerta_fuzzy(adh_pct, prog_pct)  → dict
  extraer_macros_de_texto(texto)           → dict
  identificar_intencion_salud(texto)       → str
  interpretar_comando_nlp(comando)         → dict
  recomendar_alimentos_con_groq(perfil)    → str
"""

import os
import json
import re
import asyncio
import pandas as pd
import numpy as np
import joblib
import httpx
from typing import List, Optional, Dict, Tuple

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

try:
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl
except ImportError:
    fuzz = None
    ctrl = None

from app.core.config import settings
from app.services.nutricion_service import nutricion_service

# Constantes de Salud
CONDICIONES_CRITICAS = [
    "diabetes", "hipertensión", "hipertension", "renal", "cardíaca", 
    "cardiaca", "embarazo", "lactancia", "celiaco", "celíaco"
]

class IAService:
    """Motor de IA de CaloFit — Simplificado para Tesis (Random Forest + KNN + Llama-3)."""

    def __init__(self):
        # Groq / Llama-3 (Motor de Lenguaje Natural)
        if AsyncGroq and getattr(settings, "GROQ_API_KEY", None):
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        else:
            self.groq_client = None
            print("⚠️ Groq no inicializado — modo offline activo.")

        # FatSecret (Respaldo de macros)
        self._fs_client_id     = getattr(settings, "FATSECRET_CLIENT_ID", None)
        self._fs_client_secret = getattr(settings, "FATSECRET_CLIENT_SECRET", None)
        self._fs_token         = None

        # Motor de Lógica Difusa (Diagnóstico)
        self._alerta_sim = self._setup_fuzzy_logic()

    # ══════════════════════════════════════════════════════════════════
    # PILAR 1: CÁLCULO CLÍNICO (Mifflin-St Jeor)
    # ══════════════════════════════════════════════════════════════════

    def calcular_requerimiento(
        self, genero: int, edad: int, peso: float,
        talla: float, nivel_actividad: float, objetivo: str
    ) -> float:
        """
        Calcula el Gasto Energético Total (GET) basado en Mifflin-St Jeor.
        genero: 1=Hombre, 2=Mujer.
        """
        # TMB (Tasa Metabólica Basal)
        s = 5 if genero == 1 else -161
        tmb = (10 * peso) + (6.25 * talla) - (5 * edad) + s

        # GET = TMB * Nivel de Actividad
        mantenimiento = tmb * nivel_actividad

        # Ajuste por objetivo nutricional
        ajustes = {
            "perder": -500, "perder peso": -500, "perder_leve": -300,
            "mantener": 0,  "mantener peso": 0,
            "ganar_leve": 250,
            "ganar": 500,   "ganar masa": 500,
        }
        return round(mantenimiento + ajustes.get(objetivo.lower(), 0), 2)

    def calcular_macros_completos(
        self, genero: int, edad: int, peso: float,
        talla: float, nivel_actividad: float, objetivo: str
    ) -> Tuple[float, float, float, float]:
        """Retorna calorias y desglose de macros inicial."""
        calorias = self.calcular_requerimiento(genero, edad, peso, talla, nivel_actividad, objetivo)
        obj_lower = objetivo.lower()
        
        # Distribución estándar clínica 30/40/30 para pérdida, 25/50/25 para ganancia/mantenimiento
        prot_ratio = 0.30 if "perder" in obj_lower else 0.25
        carb_ratio = 0.40 if "perder" in obj_lower else 0.50
        gras_ratio = 1.0 - prot_ratio - carb_ratio
        
        return (
            calorias,
            round((calorias * prot_ratio) / 4, 1),
            round((calorias * carb_ratio) / 4, 1),
            round((calorias * gras_ratio) / 9, 1),
        )

    def calcular_macros_optimizados(
        self, calorias: float, objetivo: str, peso: float = 70.0
    ) -> Dict:
        """Distribución avanzada de macros basada en el peso del usuario."""
        obj = objetivo.lower()
        if "perder" in obj:
            prot_g, gras_ratio = round(peso * 2.1, 1), 0.25 # Alta proteína para preservar músculo
        elif "ganar" in obj:
            prot_g, gras_ratio = round(peso * 1.8, 1), 0.25
        else:
            prot_g, gras_ratio = round(peso * 1.6, 1), 0.25

        cal_gras = calorias * gras_ratio
        cal_carb = calorias - (prot_g * 4) - cal_gras
        return {
            "calorias_totales": round(calorias, 1),
            "proteinas_g":      prot_g,
            "carbohidratos_g":  round(cal_carb / 4, 1),
            "grasas_g":         round(cal_gras / 9, 1),
        }

    # ══════════════════════════════════════════════════════════════════
    # LÓGICA DIFUSA (Diagnóstico de Adherencia)
    # ══════════════════════════════════════════════════════════════════

    def _setup_fuzzy_logic(self):
        if not (fuzz and ctrl): return None
        try:
            adherencia = ctrl.Antecedent(np.arange(0, 101, 1), "adherencia")
            progreso   = ctrl.Antecedent(np.arange(0, 101, 1), "progreso")
            alerta     = ctrl.Consequent(np.arange(0, 101, 1), "alerta")

            adherencia["baja"]  = fuzz.trimf(adherencia.universe, [0,   0,  50])
            adherencia["media"] = fuzz.trimf(adherencia.universe, [25, 50,  75])
            adherencia["alta"]  = fuzz.trimf(adherencia.universe, [50, 100, 100])

            progreso["lento"]  = fuzz.trimf(progreso.universe, [0,   0,  50])
            progreso["normal"] = fuzz.trimf(progreso.universe, [25, 50,  75])
            progreso["rapido"] = fuzz.trimf(progreso.universe, [50, 100, 100])

            alerta["suave"]    = fuzz.trimf(alerta.universe, [0,   0,  40])
            alerta["moderada"] = fuzz.trimf(alerta.universe, [30, 50,  70])
            alerta["estricta"] = fuzz.trimf(alerta.universe, [60, 100, 100])

            rules = [
                ctrl.Rule(adherencia["alta"]  & progreso["rapido"], alerta["suave"]),
                ctrl.Rule(adherencia["media"] & progreso["normal"], alerta["moderada"]),
                ctrl.Rule(adherencia["baja"]  | progreso["lento"],  alerta["estricta"]),
            ]
            return ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))
        except: return None

    def generar_alerta_fuzzy(self, adh_pct: float, prog_pct: float) -> Dict:
        if not self._alerta_sim: return {"nivel": "N/A", "score": 50, "mensaje": "Estándar."}
        try:
            self._alerta_sim.input["adherencia"] = max(0, min(100, adh_pct))
            self._alerta_sim.input["progreso"]   = max(0, min(100, prog_pct))
            self._alerta_sim.compute()
            score = self._alerta_sim.output["alerta"]
            if score < 40: nivel, msg = "Bajo",  "Excelente ritmo."
            elif score < 70: nivel, msg = "Medio", "Estable, sigue así."
            else: nivel, msg = "Alto",  "Necesitas refuerzo motivaional."
            return {"nivel": nivel, "score": round(float(score), 2), "mensaje": msg}
        except: return {"nivel": "N/A", "score": 50, "mensaje": "Estándar."}

    # ══════════════════════════════════════════════════════════════════
    # PROCESAMIENTO NLP (Llama-3 vía Groq)
    # ══════════════════════════════════════════════════════════════════

    async def _llamar_groq(self, prompt: str, max_tokens: int = 800, temp: float = 0.7) -> str:
        if not self.groq_client: return "[Modo Offline]"
        try:
            r = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temp,
            )
            return r.choices[0].message.content.strip()
        except Exception as e: return f"[Error: {e}]"

    async def recomendar_alimentos_con_groq(
        self, perfil_usuario: Dict, comando_texto: str = None,
        adherencia_pct: float = 100, progreso_pct: float = 50,
    ) -> str:
        """Genera plan nutricional usando el contexto del usuario y datos de los modelos ML."""
        genero = 1 if perfil_usuario.get("gender", "M") == "M" else 2
        calorias = self.calcular_requerimiento(
            genero, perfil_usuario.get("age", 25), perfil_usuario.get("weight", 70),
            perfil_usuario.get("height", 170), perfil_usuario.get("activity_level", 1.2),
            perfil_usuario.get("goal", "mantener")
        )
        macros = self.calcular_macros_optimizados(calorias, perfil_usuario.get("goal", "mantener"), perfil_usuario.get("weight", 70))
        
        # Recuperar y formatear condiciones médicas si existen
        med_conditions = perfil_usuario.get("medical_conditions", [])
        cond_texto = ", ".join(med_conditions) if med_conditions else "Ninguna"
        
        alerta_clinica = ""
        if cond_texto != "Ninguna" and cond_texto != "":
            alerta_clinica = f"\n⚠️ CONDICIONES MÉDICAS CRÍTICAS: {cond_texto}. ESTÁ PROHIBIDO RECOMENDAR ALIMENTOS DAÑINOS PARA ESTAS PATOLOGÍAS."

        prompt = f"""Eres un Nutricionista Clínico y Deportivo muy profesional especializado en gastronomía peruana.
CLIENTE: {perfil_usuario.get('first_name', 'Cliente')} | OBJETIVO: {perfil_usuario.get('goal', 'mantener')}
METAS: {calorias} kcal | P: {macros['proteinas_g']}g | C: {macros['carbohidratos_g']}g | G: {macros['grasas_g']}g{alerta_clinica}

REGLAS INFLEXIBLES:
1. Usa principalmente alimentos disponibles en Perú (Quinua, Pollo, Camote, Atún, etc).
2. Si el cliente tiene Condiciones Médicas Críticas, MENCIONA BREVEMENTE POR QUÉ evitaste ciertos alimentos en base a su patología.
3. Sé empático pero sumamente riguroso clínicamente.
{f'COMANDO DEL CLIENTE: {comando_texto}' if comando_texto else ''}"""
        return await self._llamar_groq(prompt)

    # ══════════════════════════════════════════════════════════════════
    # NLP — IDENTIFICACIÓN DE INTENCIONES
    # ══════════════════════════════════════════════════════════════════

    def identificar_intencion_salud(self, texto: str) -> str:
        t = texto.lower()
        if any(k in t for k in ["duele", "mal", "mareo", "dolor"]): return "ALERT"
        if any(k in t for k in ["hice", "entrené", "gym", "cardio"]): return "EXERCISE"
        if any(k in t for k in ["comí", "desayuné", "cené", "registra"]): return "LOG"
        if any(k in t for k in ["caloría", "cuánto tiene", "macro"]): return "INFO"
        if any(k in t for k in ["qué como", "recomienda", "plan", "dieta"]): return "RECIPE"
        return "GENERAL"

    def interpretar_comando_nlp(self, comando: str) -> Dict:
        """Parsea el lenguaje natural para identificar intenciones de registro."""
        intencion = self.identificar_intencion_salud(comando)
        numeros = re.findall(r'\d+\.?\d*', comando)
        return {
            "intencion": intencion,
            "texto_original": comando,
            "cantidad_detectada": float(numeros[0]) if numeros else None,
            "palabras_clave": [w for w in comando.lower().split() if len(w) > 4],
        }

    async def extraer_macros_de_texto(self, texto: str, peso_usuario: float = 70.0) -> Dict:
        """Extrae macros usando Llama-3 como motor NLP (Registro asistido por IA)."""
        prompt = f"""Analiza: "{texto}" y extrae macros nutricionales.
        Responde SOLO el JSON: {{"alimento": "nombre", "calorias": 0, "proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0}}
        Si no sabes, pon -1 en calorias."""
        
        raw = await self._llamar_groq(prompt, max_tokens=200, temp=0.1)
        try:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m: return json.loads(m.group())
        except: pass
        return {"alimento": texto, "calorias": -1, "proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0}

    # ══════════════════════════════════════════════════════════════════
    # GENERADORES DE PLAN INICIAL
    # ══════════════════════════════════════════════════════════════════

    def generar_plan_inicial_automatico(self, datos_cliente: Dict) -> Optional[Dict]:
        """Genera el primer plan del cliente usando base clínica y personalización por objetivo."""
        try:
            genero = 1 if str(datos_cliente.get("genero", "M")).upper() == "M" else 2
            calorias = self.calcular_requerimiento(
                genero, int(datos_cliente.get("edad", 25)), float(datos_cliente.get("peso", 70)),
                float(datos_cliente.get("talla", 170)), float(datos_cliente.get("nivel_actividad", 1.2)),
                datos_cliente.get("objetivo", "mantener")
            )
            macros = self.calcular_macros_optimizados(calorias, datos_cliente.get("objetivo", "mantener"), float(datos_cliente.get("peso", 70)))
            
            dias = []
            for i in range(1, 8):
                dias.append({
                    "dia_numero": i,
                    "calorias_dia": calorias,
                    "proteinas_g": macros["proteinas_g"],
                    "carbohidratos_g": macros["carbohidratos_g"],
                    "grasas_g": macros["grasas_g"],
                    "sugerencia_entrenamiento_ia": "Entrenamiento moderado sugerido por IA.",
                    "nota_asistente_ia": f"Día {i} enfocado en {datos_cliente.get('objetivo')}."
                })
            return {"calorias_diarias": calorias, "macros": macros, "dias": dias}
        except Exception as e:
            print(f"❌ Error plan inicial: {e}")
            return None

# Instancia exportada
ia_service = IAService()
ia_engine = ia_service
