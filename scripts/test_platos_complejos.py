"""Test limpio de consistencia: Lomo Saltado y Arroz con Pato."""
import sys, asyncio
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.models.client import Client
from app.models.historial import ProgresoCalorias
from app.services.asistente_service import asistente_service
from app.core.cache import get_consulta_cached
from app.core.utils import get_peru_date

class MockUser:
    def __init__(self, e, i): self.email = e; self.id = i

SEP = "=" * 55

def h(t): print(f"\n{SEP}\n  {t}\n{SEP}")

async def probar_plato(nombre_plato, mensaje, db, user, registrar=True):
    h(f"PLATO: {nombre_plato}")

    r = await asistente_service.consultar(mensaje=mensaje, db=db, current_user=user)
    secs = r.get("respuesta_estructurada", {}).get("secciones", [])
    intencion = r.get("intencion", "?")
    print(f"  Intención: {intencion} | Secciones: {len(secs)}")

    cache_ok = False
    for idx, s in enumerate(secs[:3]):
        nombre = s.get("nombre", "?")
        cid    = s.get("consulta_id")
        macros_raw  = s.get("macros", "")
        macros_cache = s.get("macros_cache", "")

        print(f"\n  ── Opción {idx+1}: {nombre}")
        print(f"      macros raw   : {macros_raw}")
        print(f"      macros_cache : {macros_cache}")

        if cid:
            p = get_consulta_cached(cid)
            if p:
                cal = p["calorias"]
                prot = p["proteinas_g"]
                carb = p["carbohidratos_g"]
                gras = p["grasas_g"]
                print(f"      cache        : {cal} kcal | P:{prot}g C:{carb}g G:{gras}g")
                cache_ok = True
            else:
                print(f"      cache        : ❌ vacío")
        else:
            print(f"      consulta_id  : ❌ no generado")

    # Registrar primera opción
    if registrar and secs and secs[0].get("consulta_id"):
        cid = secs[0]["consulta_id"]
        payload = get_consulta_cached(cid)
        if payload:
            cal_esperado = payload["calorias"]
            prot_esperado = payload["proteinas_g"]

            hoy = get_peru_date()
            prog_antes = db.query(ProgresoCalorias).filter(
                ProgresoCalorias.client_id == user.id,
                ProgresoCalorias.fecha == hoy
            ).first()
            cal_antes  = prog_antes.calorias_consumidas  if prog_antes else 0
            prot_antes = prog_antes.proteinas_consumidas if prog_antes else 0

            res = await asistente_service.confirmar_registro(consulta_id=cid, db=db, current_user=user)
            print(f"\n  ✅ Registro: {res.get('mensaje')}")

            db.expire_all()
            prog_despues = db.query(ProgresoCalorias).filter(
                ProgresoCalorias.client_id == user.id,
                ProgresoCalorias.fecha == hoy
            ).first()
            cal_despues  = prog_despues.calorias_consumidas  if prog_despues else 0
            prot_despues = prog_despues.proteinas_consumidas if prog_despues else 0

            delta_cal  = cal_despues  - cal_antes
            delta_prot = prot_despues - prot_antes

            print(f"\n  VERIFICACIÓN DE CONSISTENCIA:")
            print(f"    Recomendado  : {cal_esperado} kcal | P:{prot_esperado}g")
            print(f"    Registrado   : {delta_cal} kcal | P:{delta_prot}g")

            if abs(delta_cal - cal_esperado) <= 1:
                print(f"    CALORÍAS     : ✅ CONSISTENTES")
            else:
                print(f"    CALORÍAS     : ❌ DIFERENCIA de {abs(delta_cal-cal_esperado):.1f} kcal")

            if abs(delta_prot - prot_esperado) <= 1:
                print(f"    PROTEÍNAS    : ✅ CONSISTENTES")
            else:
                print(f"    PROTEÍNAS    : ❌ DIFERENCIA de {abs(delta_prot-prot_esperado):.1f}g")

            return delta_cal
    return 0


async def main():
    db   = SessionLocal()
    client = db.query(Client).first()
    user   = MockUser(client.email, client.id)

    resultados = []

    # ── Prueba 1: Arroz con Pato
    cal1 = await probar_plato(
        "Arroz con Pato Chiclayano",
        "Recomiéndame arroz con pato al estilo chiclayano con sus macros exactos",
        db, user
    )
    resultados.append(("Arroz con Pato", cal1 > 0))

    # ── Prueba 2: Lomo Saltado
    cal2 = await probar_plato(
        "Lomo Saltado",
        "Dame la receta de lomo saltado peruano tradicional con sus macros por porción",
        db, user
    )
    resultados.append(("Lomo Saltado", cal2 > 0))

    # ── Prueba 3: Ceviche
    cal3 = await probar_plato(
        "Ceviche",
        "Quiero hacer ceviche peruano de pescado. Dame la receta con ingredientes, calorías y macros",
        db, user, registrar=False
    )
    resultados.append(("Ceviche", cal3 >= 0))

    # ── Prueba 4: Consultar macros del plato que recomendé (INFO)
    h("CONSULTA INFO: Cuántas calorías tiene el lomo saltado")
    r_info = await asistente_service.consultar(
        mensaje="¿Cuántas calorías y macros tiene un lomo saltado peruano?",
        db=db, current_user=user
    )
    texto = r_info.get("respuesta_estructurada", {}).get("texto_conversacional", "")
    print(f"  Intención: {r_info.get('intencion')}")
    print(f"  Respuesta:\n  {texto[:400]}")

    # ── Balance final
    h("BALANCE FINAL DEL DÍA")
    hoy = get_peru_date()
    prog = db.query(ProgresoCalorias).filter(
        ProgresoCalorias.client_id == client.id,
        ProgresoCalorias.fecha == hoy
    ).first()
    if prog:
        print(f"  Consumido hoy   : {prog.calorias_consumidas} kcal")
        print(f"  Proteínas hoy   : {prog.proteinas_consumidas} g")
        print(f"  Carbohidratos   : {prog.carbohidratos_consumidos} g")
        print(f"  Grasas          : {prog.grasas_consumidas} g")

    # ── Resumen
    h("RESUMEN")
    for nombre, ok in resultados:
        estado = "✅" if ok else "⚠️"
        print(f"  {estado} {nombre}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
