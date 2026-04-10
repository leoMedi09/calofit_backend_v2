"""Auditoría completa de métodos y código muerto en CaloFit Backend."""
import sys, glob, ast, inspect
sys.path.insert(0, "/app")

py_files = [
    f for f in glob.glob("/app/**/*.py", recursive=True)
    if "__pycache__" not in f and "test_" not in f and "script" not in f
]

def buscar_usos(metodo, excluir_archivo=None):
    """Retorna lista de archivos donde se usa el método."""
    usos = []
    for f in py_files:
        if excluir_archivo and excluir_archivo in f:
            continue
        try:
            txt = open(f).read()
            if metodo in txt:
                usos.append(f.replace("/app/", ""))
        except:
            pass
    return usos

SEP = "─" * 70

print("\n" + "=" * 70)
print("  AUDITORÍA DE MÉTODOS — CaloFit Backend")
print("=" * 70)

# ── IA SERVICE ─────────────────────────────────────────────────────────
print(f"\n{'IA SERVICE (ia_service.py)':}")
print(SEP)

from app.services.ia_service import ia_engine

metodos_ia = [name for name in dir(ia_engine)
              if not name.startswith("__") and callable(getattr(ia_engine, name))]

for nombre in sorted(metodos_ia):
    m = getattr(ia_engine, nombre)
    try:
        src = inspect.getsource(m)
        lines = len(src.strip().split("\n"))
    except:
        lines = 0

    usos_externos = buscar_usos(nombre, excluir_archivo="ia_service.py")
    usos_internos = nombre in open("/app/app/services/ia_service.py").read()

    if not usos_externos and nombre.startswith("_"):
        tag = "🔒 PRIVADO"
    elif not usos_externos and not nombre.startswith("_"):
        tag = "❌ SIN USO EXT"
    else:
        tag = "✅ USADO"

    callers = ", ".join(usos_externos) if usos_externos else "—"
    print(f"  {tag:<16} {nombre:<42} {lines:>3} lín.  {callers}")

# ── ML SERVICE ─────────────────────────────────────────────────────────
print(f"\n{'ML SERVICE (ml_service.py)':}")
print(SEP)

from app.services.ml_service import ml_perfil, ml_recomendador

for obj_name, obj in [("ClasificadorPerfil", ml_perfil), ("RecomendadorKNN", ml_recomendador)]:
    print(f"\n  [{obj_name}]")
    for nombre in sorted(dir(obj)):
        if nombre.startswith("__"):
            continue
        m = getattr(obj, nombre)
        if not callable(m):
            continue
        usos = buscar_usos(nombre, excluir_archivo="ml_service.py")
        tag = "✅ USADO" if usos else ("🔒 PRIVADO" if nombre.startswith("_") else "❌ SIN USO EXT")
        callers = ", ".join(usos) if usos else "—"
        print(f"    {tag:<16} {nombre:<40} {callers}")

# ── ASISTENTE SERVICE ──────────────────────────────────────────────────
print(f"\n{'ASISTENTE SERVICE (asistente_service.py)':}")
print(SEP)

with open("/app/app/services/asistente_service.py") as f:
    src = f.read()
    tree = ast.parse(src)

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "AsistenteService":
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nombre = item.name
                usos = buscar_usos(nombre, excluir_archivo="asistente_service.py")
                lines = item.end_lineno - item.lineno + 1 if hasattr(item, "end_lineno") else 0
                if not usos and nombre.startswith("_"):
                    tag = "🔒 PRIVADO"
                elif not usos:
                    tag = "❌ SIN USO EXT"
                else:
                    tag = "✅ USADO"
                callers = ", ".join(usos) if usos else "—"
                print(f"  {tag:<16} {nombre:<45} {lines:>3} lín.  {callers}")

# ── ROUTES: buscar endpoints sin usar ─────────────────────────────────
print(f"\n{'ROUTES — Endpoints registrados':}")
print(SEP)

route_files = [f for f in py_files if "/routes/" in f]
for rf in sorted(route_files):
    with open(rf) as f: txt = f.read()
    rutas = []
    tree2 = ast.parse(txt)
    for node in ast.walk(tree2):
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(d, ast.Call) and hasattr(d.func, "attr")
            and d.func.attr in ("get", "post", "put", "delete", "patch")
            for d in node.decorator_list
        ):
            rutas.append(f"    {node.name}")
    if rutas:
        print(f"\n  {rf.replace('/app/', '')}")
        print("\n".join(rutas))

print("\n" + "=" * 70)
print("  FIN DE AUDITORÍA")
print("=" * 70)
