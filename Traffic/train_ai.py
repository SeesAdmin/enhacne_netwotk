#!/usr/bin/env python3
"""
train_ai.py — Обучение Random Forest модели для AI-IPS.

Вход:  network_data.csv (генерируется generate_dataset.py)
Выход: brain.pkl (модель), metrics.txt (метрики для диплома)
"""

import pandas as pd
import joblib
import os
import sys
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, accuracy_score,
    confusion_matrix, roc_auc_score
)

# ─── Пути ─────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(__file__)
CSV_PATH  = os.path.join(BASE, 'network_data.csv')
PKL_PATH  = os.path.join(BASE, 'brain.pkl')
METRICS   = os.path.join(BASE, 'model_metrics.txt')

# ─── 1. Загрузка данных ───────────────────────────────────────────────────────
try:
    df = pd.read_csv(CSV_PATH)
    print(f"[*] Датасет загружен: {len(df)} строк")
    print(f"    Норма(0): {(df.label==0).sum()} | Атака(1): {(df.label==1).sum()}")
except FileNotFoundError:
    print(f"[!] Файл {CSV_PATH} не найден.")
    print(f"    Запусти сначала: python3 generate_dataset.py")
    sys.exit(1)

# ─── 2. Обработка данных ──────────────────────────────────────────────────────
FEATURES = ['user5_kbps', 'router_kbps']
X = df[FEATURES]
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

print(f"[*] Обучающая выборка: {len(X_train)} | Тестовая: {len(X_test)}")

# ─── 3. Обучение модели ───────────────────────────────────────────────────────
print("[*] Обучение Random Forest (100 деревьев)...")
clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)

# ─── 4. Оценка качества ───────────────────────────────────────────────────────
y_pred = clf.predict(X_test)
acc    = accuracy_score(y_test, y_pred)
auc    = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
cm     = confusion_matrix(y_test, y_pred)
report = classification_report(y_test, y_pred, target_names=["Норма", "Атака"])

# Cross-validation (5-fold)
cv_scores = cross_val_score(clf, X, y, cv=5, scoring='accuracy')

# Важность признаков
feat_imp = dict(zip(FEATURES, clf.feature_importances_))

# ─── 5. Вывод результатов ─────────────────────────────────────────────────────
separator = "=" * 52

print(f"\n{separator}")
print("   РЕЗУЛЬТАТЫ ОБУЧЕНИЯ МОДЕЛИ (для диплома)")
print(separator)
print(f"  Accuracy (точность):    {acc * 100:.2f}%")
print(f"  ROC-AUC:                {auc:.4f}")
print(f"  Cross-val (5-fold):     {cv_scores.mean() * 100:.2f}% ± {cv_scores.std() * 100:.2f}%")
print(f"\n  Матрица ошибок:")
print(f"                Predicted 0  Predicted 1")
print(f"  Actual 0   {cm[0][0]:>10}   {cm[0][1]:>10}   ← Норма")
print(f"  Actual 1   {cm[1][0]:>10}   {cm[1][1]:>10}   ← Атака")
print(f"\n  Важность признаков:")
for feat, imp in sorted(feat_imp.items(), key=lambda x: -x[1]):
    bar = "█" * int(imp * 40)
    print(f"    {feat:<20} {imp:.4f}  {bar}")
print(f"\n  Детальный отчёт:")
print(report)
print(separator)

# ─── 6. Тесты на конкретных значениях (для демо) ─────────────────────────────
test_cases = [
    ([5.0, 30.0],   "Нормальный офисный трафик"),
    ([750.0, 600.0],"DoS-атака (ping flood 750 kbps)"),
    ([90.0, 120.0], "Медленная атака (~90 kbps)"),
    ([35.0, 50.0],  "Всплеск нормы (скачивание)"),
    ([0.0, 0.0],    "Нулевой трафик (тихо)"),
]

print("  Тесты на известных сценариях:")
for vals, desc in test_cases:
    df_test = pd.DataFrame([vals], columns=FEATURES)
    pred    = clf.predict(df_test)[0]
    proba   = clf.predict_proba(df_test)[0][1]
    result  = "🚨 АТАКА" if pred == 1 else "✅ НОРМА"
    print(f"    {desc:<42} → {result} (prob={proba:.2f})")

# ─── 7. Сохранение модели и метрик ───────────────────────────────────────────
joblib.dump(clf, PKL_PATH)
print(f"\n[+] Модель сохранена: {PKL_PATH}")

metrics_text = f"""=== МЕТРИКИ МОДЕЛИ AI-IPS (Random Forest) ===
Датасет:        {len(df)} записей ({(df.label==0).sum()} норма / {(df.label==1).sum()} атаки)
Признаки:       {FEATURES}
Алгоритм:       RandomForestClassifier (n_estimators=100)

Accuracy:       {acc * 100:.2f}%
ROC-AUC:        {auc:.4f}
Cross-val (5):  {cv_scores.mean() * 100:.2f}% ± {cv_scores.std() * 100:.2f}%

Матрица ошибок:
  TN={cm[0][0]}  FP={cm[0][1]}
  FN={cm[1][0]}  TP={cm[1][1]}

{report}
"""
with open(METRICS, 'w') as f:
    f.write(metrics_text)
print(f"[+] Метрики для диплома: {METRICS}")
