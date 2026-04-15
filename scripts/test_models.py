import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv("scripts/data/gym_members_exercise_tracking.csv")
df["BMI"] = df["Weight (kg)"] / ((df["Height (m)"]) ** 2)
df["Gender_Enc"] = df["Gender"].apply(lambda x: 1 if x == "Male" else 0)

features = ["Age", "Gender_Enc", "Weight (kg)", "Height (m)", "BMI", "Workout_Frequency (days/week)"]
X = df[features]
y = df["Experience_Level"]

# Scaler para ANN y SVC
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

models_unscaled = {
    "RandomForest": RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42),
    "GradientBoosting": GradientBoostingClassifier(n_estimators=300, learning_rate=0.05, max_depth=4, random_state=42),
}

models_scaled = {
    "MLP_ANN": MLPClassifier(hidden_layer_sizes=(128, 64, 32), max_iter=2000, random_state=42),
    "SVC": SVC(class_weight='balanced', random_state=42)
}

print("--- Unscaled Data Models ---")
for name, model in models_unscaled.items():
    scores = cross_val_score(model, X, y, cv=5)
    print(f"{name}: {scores.mean()*100:.2f}%")

print("\n--- Scaled Data Models ---")
for name, model in models_scaled.items():
    scores = cross_val_score(model, X_scaled, y, cv=5)
    print(f"{name}: {scores.mean()*100:.2f}%")
