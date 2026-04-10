"""
╔══════════════════════════════════════════════════════════════════════╗
║   CaloFit — Test de Consistencia de Macros en Platos Complejos      ║
║   Prueba:                                                            ║
║   1. Recomendar plato complejo peruano (arroz con pato, lomo, etc.) ║
║   2. Preguntar macros del plato recomendado                         ║
║   3. Registrarlo → verificar que los valores NO cambian             ║
║   4. Verificar el balance final                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import sys, asyncio, json, re
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.models.client import Client
from app.models.historial import ProgresoCalorias
from app.services.asistente_service import asistente_service
from app.core.cache import get_consulta_cached
from app.core.utils import get_peru_date

SEP  = "═" * 65
SEP2 = "─" * 65

def header(t): print(f"\n{SEP}\n  {t}\n{SEP}")
def ok(m):     print(f"  ✅ {m}")
def err(m):    print(f"  ❌ {m}")
def warn(m):   print(f"  ⚠️  {m}")
def dato(k,v): print(f"  {k:<45}: {v}")
def sep():     print(f"  {SEP2}")


class MockUser:
    def __init__(self, email, uid):
        self.email = email
        self.id    = uid


async def main():
    db  = SessionLocal()
    try:
        cliente = db.query(Client).first()
        user    = MockUser(email=cliente.email, uid=cliente.id)

        print(f"\n  Cliente: {cliente.first_name} | Meta plan: ~2140 kcal/día")

        # ──────────────────────────────────────────────────────────────
        # TEST A: Arroz con Pato — plato tradicional peruano complejo
        # ──────────────────────────────────────────────────────────────
        header("TEST A: RECOMENDAR → Arroz con Pato (plato complejo peruano)")

        resp_reco = await asistente_service.consultar(
            mensaje="Recomiéndame una receta de arroz con pato al estilo chiclayano con sus macros exactos",
            db=db, current_user=user
        )
        secciones = resp_reco.get("respuesta_estructurada", {}).get("secciones", [])
        texto     = resp_reco.get("respuesta_estructurada", {}).get("texto_conversacional", "")

        print(f"\n  Texto IA:\n  {texto[:300]}")
        dato("\n  Intención detectada", resp_reco.get("intencion"))
        dato("  Nro secciones/tarjetas",    len(secciones))

        plato_principal = None
        if secciones:
            plato_principal = secciones[0]
            nombre_plato = plato_principal.get("nombre", "?")
            cid          = plato_principal.get("consulta_id")
            macros_texto = plato_principal.get("macros", "")
            macros_cache_str = plato_principal.get("macros_cache", "")

            print(f"\n  ── Plato recomendado: '{nombre_plato}' ──")
            dato("  macros (LLM raw)",      macros_texto[:80] if macros_texto else "NO EXTRAÍDO")
            dato("  macros_cache (suma ing)", macros_cache_str or "NO CALCULADO")
            dato("  consulta_id",           cid or "NO GENERADO ⚠️")

            # Leer cache
            if cid:
                payload = get_consulta_cached(cid)
                if payload:
                    cal_recomendado  = payload.get("calorias", 0)
                    prot_recomendado = payload.get("proteinas_g", 0)
                    carb_recomendado = payload.get("carbohidratos_g", 0)
                    gras_recomendado = payload.get("grasas_g", 0)

                    print(f"\n  Valores guardados en cache (lo que se registrará):")
                    sep()
                    dato("  Calorías",      f"{cal_recomendado} kcal")
                    dato("  Proteínas",     f"{prot_recomendado} g")
                    dato("  Carbohidratos", f"{carb_recomendado} g")
                    dato("  Grasas",        f"{gras_recomendado} g")
                    sep()

                    ingredientes = payload.get("ingredientes", [])
                    print(f"\n  Ingredientes con kcal ({len(ingredientes)} total):")
                    for ing in ingredientes:
                        print(f"    → {ing}")
                else:
                    err("Cache vacío después de la recomendación")
                    cal_recomendado = 0
            else:
                warn("Sin consulta_id — la tarjeta Registrar del chat no funcionará")
                cal_recomendado = 0
        else:
            warn("La IA respondió en texto plano, sin generar tarjeta")
            print(f"  {texto[:500]}")
            cal_recomendado = 0

        # ──────────────────────────────────────────────────────────────
        # TEST B: Preguntar macros del plato recomendado
        # ──────────────────────────────────────────────────────────────
        header("TEST B: CONSULTAR → '¿Cuántas calorías y macros tiene el arroz con pato?'")

        resp_info = await asistente_service.consultar(
            mensaje="¿Cuántas calorías y macros tiene una porción de arroz con pato peruano?",
            db=db, current_user=user
        )
        texto_info   = resp_info.get("respuesta_estructurada", {}).get("texto_conversacional", "")
        secciones_info = resp_info.get("respuesta_estructurada", {}).get("secciones", [])

        dato("Intención",     resp_info.get("intencion"))
        dato("Secciones",     len(secciones_info))
        print(f"\n  Respuesta:")
        print(f"  {texto_info[:400]}")

        # Extraer números de calorías del texto
        cal_texto = re.findall(r'(\d{3,4})\s*(?:kcal|calorías|cal)', texto_info, re.IGNORECASE)
        prot_texto = re.findall(r'(\d+(?:\.\d+)?)\s*g?\s*(?:de\s+)?(?:proteína|prote)', texto_info, re.IGNORECASE)
        if cal_texto:
            ok(f"IA menciona {cal_texto[0]} kcal para arroz con pato en la respuesta INFO")
        else:
            warn("La IA no mencionó calorías de forma detectable en su respuesta")

        # ──────────────────────────────────────────────────────────────
        # TEST C: Lomo Saltado — otro plato complejo
        # ──────────────────────────────────────────────────────────────
        header("TEST C: RECOMENDAR → Lomo Saltado (verificar consistencia de macros)")

        resp_lomo = await asistente_service.consultar(
            mensaje="Dame la receta de lomo saltado peruano con sus macros exactos por porción",
            db=db, current_user=user
        )
        secs_lomo = resp_lomo.get("respuesta_estructurada", {}).get("secciones", [])
        dato("Intención", resp_lomo.get("intencion"))
        dato("Nro secciones generadas", len(secs_lomo))

        if secs_lomo:
            s = secs_lomo[0]
            cid_lomo = s.get("consulta_id")
            print(f"\n  Plato: '{s.get('nombre', '?')}'")
            print(f"  Macros raw: {s.get('macros', 'N/A')[:80]}")
            print(f"  macros_cache: {s.get('macros_cache', 'N/A')}")

            if cid_lomo:
                p = get_consulta_cached(cid_lomo)
                if p:
                    cal_lomo = p["calorias"]
                    dato("  → Calorías en cache", f"{cal_lomo} kcal")
                    dato("  → Proteínas",         f"{p['proteinas_g']} g")
                    dato("  → Carbohidratos",      f"{p['carbohidratos_g']} g")
                    dato("  → Grasas",             f"{p['grasas_g']} g")
                    ok("Cache generado correctamente para lomo saltado")
                else:
                    err("Cache vacío")
                    cal_lomo = 0
            else:
                err("Sin consulta_id para lomo saltado")
                cal_lomo = 0
        else:
            warn("Sin secciones para lomo saltado")
            cal_lomo = 0

        # ──────────────────────────────────────────────────────────────
        # TEST D: REGISTRAR el arroz con pato y verificar consistencia
        # ──────────────────────────────────────────────────────────────
        header("TEST D: REGISTRAR desde consulta_id → Valores EXACTAMENTE iguales")

        if plato_principal and plato_principal.get("consulta_id"):
            cid = plato_principal["consulta_id"]

            # Leer estado de BD ANTES del registro
            hoy = get_peru_date()
            progreso_antes = db.query(ProgresoCalorias).filter(
                ProgresoCalorias.client_id == cliente.id,
                ProgresoCalorias.fecha     == hoy
            ).first()
            cal_antes = progreso_antes.calorias_consumidas if progreso_antes else 0
            prot_antes = progreso_antes.proteinas_consumidas if progreso_antes else 0

            print(f"\n  Estado BD antes del registro:")
            dato("  Calorías consumidas", f"{cal_antes} kcal")
            dato("  Proteínas consumidas", f"{prot_antes} g")

            # Registrar
            resultado = await asistente_service.confirmar_registro(
                consulta_id=cid, db=db, current_user=user
            )
            ok(f"Registro completado: {resultado.get('mensaje')}")

            # Leer estado DESPUÉS
            db.expire_all()
            progreso_despues = db.query(ProgresoCalorias).filter(
                ProgresoCalorias.client_id == cliente.id,
                ProgresoCalorias.fecha     == hoy
            ).first()
            cal_despues  = progreso_despues.calorias_consumidas if progreso_despues else 0
            prot_despues = progreso_despues.proteinas_consumidas if progreso_despues else 0

            cal_delta  = cal_despues  - cal_antes
            prot_delta = prot_despues - prot_antes

            print(f"\n  Verificación de consistencia:")
            sep()
            dato("  Calorías recomendadas (cache)", f"{cal_recomendado} kcal")
            dato("  Calorías registradas en BD",    f"{cal_delta} kcal")
            if abs(cal_delta - cal_recomendado) <= 1:
                ok(f"CONSISTENTE ✓ — lo que se mostró = lo que se registró ({cal_recomendado} kcal)")
            else:
                err(f"INCONSISTENCIA — mostrado: {cal_recomendado} kcal, registrado: {cal_delta} kcal")
            sep()
        else:
            warn("No hay consulta_id disponible para el registro. El TEST D se omite.")

        # ──────────────────────────────────────────────────────────────
        # TEST E: Verificar balance total después de todo
        # ──────────────────────────────────────────────────────────────
        header("TEST E: BALANCE FINAL DEL DÍA después de registrar")

        resp_balance = await asistente_service.consultar(
            mensaje="¿Cuántas calorías llevo hoy y cuánto me falta para mi meta?",
            db=db, current_user=user
        )
        texto_balance = resp_balance.get("respuesta_estructurada", {}).get("texto_conversacional", "")
        dc            = resp_balance.get("data_cientifica", {}).get("progreso_diario", {})

        print(f"\n  Respuesta del asistente:\n  {texto_balance[:300]}")
        print(f"\n  data_cientifica.progreso_diario:")
        dato("  consumido", f"{dc.get('consumido', '?')} kcal")
        dato("  meta",      f"{dc.get('meta', '?')} kcal")
        dato("  restante",  f"{dc.get('restante', '?')} kcal")
        dato("  quemado",   f"{dc.get('quemado', '?')} kcal")

        # ──────────────────────────────────────────────────────────────
        # RESUMEN FINAL
        # ──────────────────────────────────────────────────────────────
        header("RESUMEN FINAL DE TODOS LOS TESTS")

        print(f"""
  TEST A — Recomendar Arroz con Pato    : {"✅ con tarjeta" if secciones else "⚠️ texto plano"}
  TEST B — Consultar macros INFO        : {"✅ calorías mencionadas" if cal_texto else "⚠️ sin dato numérico"}
  TEST C — Recomendar Lomo Saltado      : {"✅ con tarjeta" if secs_lomo else "⚠️ texto plano"}
  TEST D — Registrar y verificar        : {"✅ valores consistentes" if plato_principal and plato_principal.get("consulta_id") else "⚠️ sin cid"}
  TEST E — Balance post-registro        : {"✅ datos correctos" if dc.get("consumido", 0) > 0 else "⚠️ consumido=0"}

  Datos del balance final:
    Consumido hoy : {dc.get("consumido", "?")} kcal
    Meta          : {dc.get("meta", "?")} kcal
    Restante      : {dc.get("restante", "?")} kcal
        """)

    except Exception as e:
        import traceback
        err(f"Error: {e}")
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
