"""
Diagnóstico profundo del PERFIL_A con Accuracy 100%.
¿Separación real de clases o sobreajuste (overfitting)?
"""

import os
import sys
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, learning_curve
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.inspection import permutation_importance

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(SCRIPT_DIR, "data", "gym_members_exercise_tracking.csv")
LABEL_MAP   = {1: "PERFIL_C", 2: "PERFIL_B", 3: "PERFIL_A"}

df_raw = pd.read_csv(CSV_PATH)
df = df_raw.copy()

# ── Misma preparación del script original ──────────────────────────
df["Gender_Enc"]   = (df["Gender"] == "Male").astype(int)
workout_dummies    = pd.get_dummies(df["Workout_Type"], prefix="Workout")
df                 = pd.concat([df, workout_dummies], axis=1)
workout_cols       = list(workout_dummies.columns)
df["Cal_por_hora"] = df["Calories_Burned"] / df["Session_Duration (hours)"].replace(0, 1)
df["Height_cm"]    = df["Height (m)"] * 100
df["Perfil"]       = df["Experience_Level"].map(LABEL_MAP)

FEATURES = [
    "Age", "Gender_Enc", "Weight (kg)", "Height_cm", "BMI",
    "Workout_Frequency (days/week)", "Session_Duration (hours)",
    "Calories_Burned", "Cal_por_hora", "Fat_Percentage",
    "Water_Intake (liters)", "Avg_BPM", "Resting_BPM",
] + workout_cols

X = df[FEATURES].values
y = df["Experience_Level"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

modelo = RandomForestClassifier(
    n_estimators=200, max_depth=10, min_samples_split=5,
    min_samples_leaf=3, class_weight="balanced",
    random_state=42, n_jobs=-1
)
modelo.fit(X_train, y_train)

print("=" * 65)
print("  DIAGNÓSTICO: ¿Por qué PERFIL_A tiene Accuracy 100%?")
print("=" * 65)

# ── 1. ANÁLISIS ESTADÍSTICO de PERFIL_A vs las demás clases ─────────
print("\n[1] SEPARACIÓN REAL DE CLASES — Estadísticas clave por Perfil:")
stats = df.groupby("Perfil")[["Session_Duration (hours)", "Workout_Frequency (days/week)", "Fat_Percentage", "Calories_Burned"]].agg(["mean", "std"]).round(2)
print(stats.to_string())

print("\n  → Si PERFIL_A tiene valores muy diferentes a B y C,")
print("    el 100% de Accuracy ES VÁLIDO y se explica por separación natural.\n")

# ── 2. VERIFICAR TRAIN vs TEST accuracy (detectar overfitting) ──────
print("[2] TRAIN ACCURACY vs TEST ACCURACY:")
y_train_pred = modelo.predict(X_train)
y_test_pred  = modelo.predict(X_test)

train_acc = accuracy_score(y_train, y_train_pred)
test_acc  = accuracy_score(y_test, y_test_pred)

print(f"  Train Accuracy: {train_acc*100:.2f}%")
print(f"  Test  Accuracy: {test_acc*100:.2f}%")
gap = train_acc - test_acc
if gap > 0.05:
    print(f"  ⚠️  GAP: {gap*100:.2f}% → POSIBLE OVERFITTING (gap > 5%)")
else:
    print(f"  ✅ GAP: {gap*100:.2f}% → MODELO SALUDABLE (gap ≤ 5%)")

# ── 3. CROSS-VALIDATION POR CLASE (lo más revelador) ────────────────
print("\n[3] CROSS-VALIDATION ESTRATIFICADO — Perfecto para detectar suerte:")
skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)  # 10-fold más estricto
cv_scores = cross_val_score(modelo, X, y, cv=skf, scoring="accuracy")
print(f"  10-Fold CV Accuracy: {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")
print(f"  Scores: {[f'{s*100:.1f}%' for s in cv_scores]}")
if cv_scores.std() > 0.03:
    print("  ⚠️  Varianza alta → resultados inestables")
else:
    print("  ✅ Varianza baja → modelo estable en todos los folds")

# ── 4. TEST CON SEMILLAS RANDOM DIFERENTES (Solvencia estadística) ──
print("\n[4] ROBUSTEZ — Repetir con 5 semillas random distintas:")
semillas = [0, 7, 13, 42, 99]
accs_A = []

for seed in semillas:
    Xtr, Xts, ytr, yts = train_test_split(X, y, test_size=0.20, random_state=seed, stratify=y)
    m = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_split=5,
                               min_samples_leaf=3, class_weight="balanced",
                               random_state=seed, n_jobs=-1)
    m.fit(Xtr, ytr)
    yp = m.predict(Xts)
    # Accuracy solo para PERFIL_A (clase 3)
    mask_a = yts == 3
    if mask_a.sum() > 0:
        acc_a = accuracy_score(yts[mask_a], yp[mask_a])
        accs_A.append(acc_a)
        print(f"  Seed {seed:>2} → PERFIL_A Accuracy: {acc_a*100:.1f}%  ({mask_a.sum()} muestras en test)")

print(f"\n  Promedio PERFIL_A a través de seeds: {np.mean(accs_A)*100:.1f}% ± {np.std(accs_A)*100:.1f}%")
if np.mean(accs_A) > 0.95:
    print("  ✅ PERFIL_A está REAL y matemáticamente separado de B y C.")
    print("     El 100% en seed=42 NO es suerte. Es consistente.")
else:
    print("  ⚠️  El 100% en seed=42 fue suerte estadística.")

# ── 5. ¿POR QUÉ ES TAN SEPARABLE PERFIL_A? ─────────────────────────
print("\n[5] EXPLICACIÓN MATEMÁTICA — Rangos de PERFIL_A vs otras clases:")
for feat in ["Session_Duration (hours)", "Workout_Frequency (days/week)", "Fat_Percentage"]:
    a_mean  = df[df["Perfil"]=="PERFIL_A"][feat].mean()
    bc_mean = df[df["Perfil"]!="PERFIL_A"][feat].mean()
    a_std   = df[df["Perfil"]=="PERFIL_A"][feat].std()
    sep     = abs(a_mean - bc_mean) / a_std  # separación en desviaciones estándar
    print(f"  {feat:<40} PERFIL_A={a_mean:.2f}  vs B+C={bc_mean:.2f}  (sep: {sep:.1f}σ)")

print("\n  Regla: sep > 1.5σ = clases bien separadas en esa dimensión.")
print("\n" + "=" * 65)
print("  VEREDICTO FINAL:")
print("=" * 65)
