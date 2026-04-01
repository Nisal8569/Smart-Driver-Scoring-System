"""
FYP: Smart Driver Scoring System — Final Training Pipeline

Dataset : Combined — Kaggle OBD-II + Car-Specific Synthetic + Real Trips
Labels  : Rule-based (Balanced v2): RPM/throttle/load thresholds + speed change (Thr > 30)
Features: 7 OBD-II signals + engineered deltas, rolling stats, ratios = 31
Split   : 70% train / 15% validation / 15% test  (stratified)
Balance : SMOTE applied to training fold ONLY
Experiments:
  1. Baseline comparison    — LR vs DT vs RF vs HistGradBoost
  2. Feature ablation       — raw -> +deltas -> +rolling -> +ratios
  3. Cross-driver LOO       — leave-one-driver-out generalisation (Kaggle drivers)
  4. Learning curve         — overfitting check
Output  : src/models/fyp_model.pkl  +  src/models/fyp_scaler.pkl
"""

import pandas as pd
import numpy as np
import joblib
import os
import json
import warnings
from datetime import datetime

import matplotlib
matplotlib.use('Agg')   # non-interactive backend (works on Pi / headless)
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import (
    train_test_split, StratifiedKFold,
    cross_val_score, learning_curve
)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report,
    ConfusionMatrixDisplay
)
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')
os.makedirs('src/models', exist_ok=True)
os.makedirs('docs/figures', exist_ok=True)

# FYP — SMART DRIVER SCORING | FINAL TRAINING PIPELINE

# STAGE 1: LOAD & COMBINE DATASETS
#   A) Kaggle OBD-II data
#   B) Car-specific synthetic data
#   C) Real trip CSVs
print("\n[1/7] Loading and combining datasets...")

SIGNAL_COLS = [
    'speed', 'rpm', 'throttle', 'engine_load',
    'relative_throttle', 'steering_angle', 'steering_speed'
]

# A: Kaggle data
RAW_PATH = "data/Kaggle/OBD-II Driving Data - Classified.csv"
df_raw = pd.read_csv(RAW_PATH, encoding='latin-1')

col_map = {
    df_raw.columns[1]:  'engine_load',
    df_raw.columns[6]:  'rpm',
    df_raw.columns[7]:  'speed',
    df_raw.columns[10]: 'throttle',
    df_raw.columns[24]: 'relative_throttle',
    df_raw.columns[31]: 'steering_angle',
    df_raw.columns[32]: 'steering_speed',
    df_raw.columns[34]: 'driver_id',
}
df_kaggle = df_raw.rename(columns=col_map)[SIGNAL_COLS + ['driver_id']].copy()
for c in SIGNAL_COLS:
    df_kaggle[c] = pd.to_numeric(df_kaggle[c], errors='coerce')
df_kaggle['driver_id'] = pd.to_numeric(df_kaggle['driver_id'], errors='coerce')
df_kaggle = df_kaggle.dropna()

# Balanced-v2 rule-based labelling on raw (unscaled) Kaggle signals
df_kaggle = df_kaggle.sort_values('driver_id').reset_index(drop=True)
df_kaggle['speed_diff'] = df_kaggle.groupby('driver_id')['speed'].diff().fillna(0)
df_kaggle['label'] = 0
agg_mask = (
    ((df_kaggle['rpm'] > 2500) & (df_kaggle['throttle'] > 30)) |
    ((df_kaggle['engine_load'] > 92) & (df_kaggle['throttle'] > 30)) |
    (df_kaggle['speed_diff'] > 12) |    # harsh acceleration: >12 km/h gain per step
    (df_kaggle['speed_diff'] < -10)     # harsh braking:      >10 km/h drop per step
)
df_kaggle.loc[agg_mask, 'label'] = 1
df_kaggle = df_kaggle.drop(columns=['speed_diff'])
print(f"  [A] Kaggle rows   : {len(df_kaggle):,}  "
      f"(Safe={( df_kaggle['label']==0).sum():,}  Agg={(df_kaggle['label']==1).sum():,})")

# B: Car-specific synthetic data
np.random.seed(42)
N_SYN = 20000

# Urban safe profile — matches real car's sensor ranges
syn_speed     = np.concatenate([
    np.zeros(N_SYN // 5),                            # idle
    np.random.uniform(5, 55, N_SYN * 4 // 5)         # moving
])
np.random.shuffle(syn_speed)
syn_rpm = np.where(syn_speed < 3,
                   np.random.uniform(700, 1100, N_SYN),
                   np.random.uniform(800, 2800, N_SYN))
syn_throttle   = np.random.uniform(13, 42, N_SYN)
syn_load       = np.where(syn_speed < 3,
                          np.random.uniform(0, 35, N_SYN),
                          np.random.uniform(45, 100, N_SYN))
syn_rel_thr    = np.random.uniform(0, 20, N_SYN)
syn_steer      = np.zeros(N_SYN)
syn_steer_spd  = np.zeros(N_SYN)

# Compute speed_change for synthetic (sequential within driver 4)
syn_speed_diff = np.diff(syn_speed, prepend=syn_speed[0])

# Apply same Balanced-v2 rules to label synthetic data
syn_label = (
    ((syn_rpm > 2500) & (syn_throttle > 30)) |
    ((syn_load > 92)  & (syn_throttle > 30)) |
    (syn_speed_diff > 12) |    # harsh acceleration
    (syn_speed_diff < -10)     # harsh braking
).astype(int)

df_syn = pd.DataFrame({
    'speed': syn_speed, 'rpm': syn_rpm, 'throttle': syn_throttle,
    'engine_load': syn_load, 'relative_throttle': syn_rel_thr,
    'steering_angle': syn_steer, 'steering_speed': syn_steer_spd,
    'label': syn_label, 'driver_id': 4
})
print(f"  [B] Synthetic rows: {len(df_syn):,}  "
      f"(Safe={(df_syn['label']==0).sum():,}  Agg={(df_syn['label']==1).sum():,})")

# C: Real trip CSVs
TRIP_PATHS = [
    'data/trips/trip_20260329_172609.csv',
    'data/trips/trip_20260330_095440.csv',
    'data/trips/trip_20260331_190000.csv',   # real aggressive trip
]
trip_frames = []
for p in TRIP_PATHS:
    t = pd.read_csv(p)
    # Use relative_throttle if present, else default to 0
    rel_thr = t['relative_throttle'] if 'relative_throttle' in t.columns else 0.0
    t = t[['speed', 'rpm', 'throttle', 'engine_load']].copy()
    t['relative_throttle'] = rel_thr
    t['steering_angle']    = 0.0
    t['steering_speed']    = 0.0
    t['speed_diff'] = t['speed'].diff().fillna(0)
    t['label'] = 0
    agg_t = (
        ((t['rpm'] > 2700) & (t['throttle'] > 30)) |
        ((t['engine_load'] > 92) & (t['throttle'] > 30)) |
        (t['speed_diff'] > 12) |
        (t['speed_diff'] < -10)
    )
    t.loc[agg_t, 'label'] = 1
    t = t.drop(columns=['speed_diff'])
    t['driver_id'] = 5
    trip_frames.append(t)
df_trips = pd.concat(trip_frames, ignore_index=True)
print(f"  [C] Real trip rows: {len(df_trips):,}  "
      f"(Safe={(df_trips['label']==0).sum():,}  Agg={(df_trips['label']==1).sum():,})")

# Combine all sources
USE_COLS = SIGNAL_COLS + ['label', 'driver_id']
df = pd.concat([
    df_kaggle[USE_COLS],
    df_syn[USE_COLS],
    df_trips[USE_COLS],
], ignore_index=True)

before = len(df)
df = df.dropna().drop_duplicates(subset=SIGNAL_COLS + ['label'])
print(f"\n  Combined rows     : {len(df):,}  (removed {before - len(df):,} dupes/nulls)")
print(f"  Drivers           : {sorted(df['driver_id'].unique().astype(int).tolist())}")
print(f"  Label 0 (Safe)    : {(df['label']==0).sum():,}")
print(f"  Label 1 (Agg)     : {(df['label']==1).sum():,}")

# STAGE 2: PREPROCESSING
print("\n[2/7] Preprocessing...")

# Clip outliers at 1st / 99th percentile
for c in SIGNAL_COLS:
    lo, hi = df[c].quantile(0.01), df[c].quantile(0.99)
    df[c] = df[c].clip(lo, hi)

# MinMax scale signals to [0, 1]
scaler = MinMaxScaler()
df[SIGNAL_COLS] = scaler.fit_transform(df[SIGNAL_COLS])
print("  Scaling complete.")

# STAGE 3: FEATURE ENGINEERING
print("\n[3/7] Feature engineering...")

df = df.sort_values('driver_id').reset_index(drop=True)

# --- Group A: Raw signals (already in SIGNAL_COLS) ---

# --- Group B: Delta (rate-of-change, signed) ---
DELTA_PAIRS = ['speed', 'rpm', 'throttle', 'engine_load', 'steering_angle']
for c in DELTA_PAIRS:
    df[f'{c}_delta'] = df.groupby('driver_id')[c].diff().fillna(0)

# --- Group C: Rolling mean + std (windows 5, 10, 15) ---
ROLL_COLS = ['speed', 'rpm', 'throttle', 'engine_load']
WINDOWS   = [5, 10, 15]
for w in WINDOWS:
    for c in ROLL_COLS:
        df[f'{c}_mean_{w}'] = df.groupby('driver_id')[c].transform(
            lambda x: x.rolling(w, min_periods=w).mean()
        )
        df[f'{c}_std_{w}'] = df.groupby('driver_id')[c].transform(
            lambda x: x.rolling(w, min_periods=w).std().fillna(0)
        )

# --- Group D: Ratio features ---
df['rpm_speed_ratio']      = df['rpm']      / df['speed'].clip(lower=0.01)
df['throttle_load_ratio']  = df['throttle'] / df['engine_load'].clip(lower=0.01)
df['steering_activity']    = df['steering_angle'].abs() + df['steering_speed'].abs()
df['throttle_rpm_ratio']   = df['throttle'] / df['rpm'].clip(lower=0.01)
df['load_speed_ratio']     = df['engine_load'] / df['speed'].clip(lower=0.01)

df = df.dropna()

# Build feature group lists (for ablation study)
GROUP_A = SIGNAL_COLS                                              # 7
GROUP_B = [f'{c}_delta' for c in DELTA_PAIRS]                     # 5
GROUP_C = [f'{c}_{s}_{w}' for w in WINDOWS
           for c in ROLL_COLS for s in ['mean','std']]             # 24
GROUP_D = ['rpm_speed_ratio', 'throttle_load_ratio', 'steering_activity',
           'throttle_rpm_ratio', 'load_speed_ratio']               # 5

ALL_FEATURES = GROUP_A + GROUP_B + GROUP_C + GROUP_D              # 41

print(f"  Feature groups: A(raw)={len(GROUP_A)}, B(delta)={len(GROUP_B)}, "
      f"C(rolling)={len(GROUP_C)}, D(ratio)={len(GROUP_D)}")
print(f"  Total features: {len(ALL_FEATURES)}")
print(f"  Samples after feature engineering: {len(df):,}")

# STAGE 4: DATA SPLIT (70/15/15)
print("\n[4/7] Splitting data (70/15/15 stratified)...")

X_all = df[ALL_FEATURES].values
y_all = df['label'].values.astype(int)

X_temp, X_test, y_temp, y_test = train_test_split(
    X_all, y_all, test_size=0.15, random_state=42, stratify=y_all
)
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=0.176, random_state=42, stratify=y_temp
    # 0.176 of 0.85 ≈ 0.15 of total -> gives 70/15/15
)

print(f"  Train : {len(X_train):,}  |  Val : {len(X_val):,}  |  Test : {len(X_test):,}")

# SMOTE only on training fold
smote = SMOTE(random_state=42)
X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
print(f"  After SMOTE — Train: {len(X_train_sm):,}  "
      f"(Safe: {(y_train_sm==0).sum():,} | Aggressive: {(y_train_sm==1).sum():,})")

# STAGE 5: EXPERIMENT 1 — BASELINE COMPARISON
print("\n[5/7] Experiment 1: Baseline model comparison...")

MODELS = {
    'Logistic Regression': LogisticRegression(
        max_iter=1000, class_weight='balanced', random_state=42),
    'Decision Tree':       DecisionTreeClassifier(
        max_depth=10, class_weight='balanced', random_state=42),
    'Random Forest':       RandomForestClassifier(
        n_estimators=100, max_depth=15, class_weight='balanced',
        n_jobs=-1, random_state=42),
    'HistGradientBoosting': HistGradientBoostingClassifier(
        learning_rate=0.05, max_iter=500, max_depth=8,
        class_weight='balanced', random_state=42),
}

comparison_results = []
trained_models = {}

for name, mdl in MODELS.items():
    mdl.fit(X_train_sm, y_train_sm)
    trained_models[name] = mdl

    # Evaluate on validation set
    yv_pred = mdl.predict(X_val)
    if hasattr(mdl, 'predict_proba'):
        yv_prob = mdl.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, yv_prob)
    else:
        auc = float('nan')

    acc = accuracy_score(y_val, yv_pred)
    f1  = f1_score(y_val, yv_pred)
    pre = precision_score(y_val, yv_pred)
    rec = recall_score(y_val, yv_pred)

    comparison_results.append({
        'Model': name, 'Accuracy': acc, 'F1': f1,
        'Precision': pre, 'Recall': rec, 'ROC-AUC': auc
    })
    print(f"  {name:25s}  Acc={acc:.4f}  F1={f1:.4f}  AUC={auc:.4f}")

comp_df = pd.DataFrame(comparison_results).sort_values('ROC-AUC', ascending=False)
print("\n  === Baseline Comparison (Validation Set) ===")
print(comp_df.to_string(index=False, float_format='{:.4f}'.format))

# Plot comparison bar chart
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(comp_df))
width = 0.2
metrics = ['Accuracy', 'F1', 'Precision', 'ROC-AUC']
colors  = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
for i, (metric, color) in enumerate(zip(metrics, colors)):
    ax.bar(x + i * width, comp_df[metric], width, label=metric, color=color)
ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(comp_df['Model'], rotation=15, ha='right')
ax.set_ylim(0.5, 1.05)
ax.set_ylabel('Score')
ax.set_title('Experiment 1: Model Comparison (Validation Set)')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('docs/figures/exp1_model_comparison.png', dpi=150)
plt.close()
print("  Saved -> docs/figures/exp1_model_comparison.png")

# STAGE 5b: EXPERIMENT 2 — FEATURE ABLATION
print("\n  Experiment 2: Feature ablation study...")

ABLATION_SETS = {
    'A: Raw signals only':         GROUP_A,
    'A+B: + Deltas':               GROUP_A + GROUP_B,
    'A+B+C: + Rolling stats':      GROUP_A + GROUP_B + GROUP_C,
    'A+B+C+D: + Ratio (full set)': ALL_FEATURES,
}

# Use HistGradBoost for ablation (best model)
ablation_results = []
best_model_ref = MODELS['HistGradientBoosting']

for label_ab, feat_cols in ABLATION_SETS.items():
    idx = [ALL_FEATURES.index(f) for f in feat_cols]
    Xtr_ab = X_train_sm[:, idx]
    Xvl_ab = X_val[:, idx]

    mdl_ab = HistGradientBoostingClassifier(
        learning_rate=0.05, max_iter=500, max_depth=8,
        class_weight='balanced', random_state=42
    )
    mdl_ab.fit(Xtr_ab, y_train_sm)
    yv_ab   = mdl_ab.predict(Xvl_ab)
    yv_prob = mdl_ab.predict_proba(Xvl_ab)[:, 1]

    ablation_results.append({
        'Feature Set': label_ab,
        'Num Features': len(feat_cols),
        'Accuracy': accuracy_score(y_val, yv_ab),
        'F1':       f1_score(y_val, yv_ab),
        'ROC-AUC':  roc_auc_score(y_val, yv_prob),
    })
    print(f"  {label_ab:35s}  "
          f"F1={ablation_results[-1]['F1']:.4f}  "
          f"AUC={ablation_results[-1]['ROC-AUC']:.4f}")

abl_df = pd.DataFrame(ablation_results)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, metric in zip(axes, ['F1', 'ROC-AUC']):
    ax.barh(abl_df['Feature Set'], abl_df[metric],
            color=['#E3F2FD','#90CAF9','#42A5F5','#1565C0'])
    ax.set_xlim(0.5, 1.0)
    ax.set_xlabel(metric)
    ax.set_title(f'Experiment 2: Ablation — {metric}')
    ax.grid(axis='x', alpha=0.3)
    for i, v in enumerate(abl_df[metric]):
        ax.text(v + 0.005, i, f'{v:.4f}', va='center', fontsize=9)
plt.tight_layout()
plt.savefig('docs/figures/exp2_ablation.png', dpi=150)
plt.close()
print("  Saved -> docs/figures/exp2_ablation.png")

# STAGE 5c: EXPERIMENT 3 — CROSS-DRIVER LOO
print("\n  Experiment 3: Cross-driver leave-one-out validation...")

# LOO only on original Kaggle drivers (1,2,3) — synthetic/trip data stays in train
drivers = sorted(df_kaggle['driver_id'].unique().astype(int).tolist())
loo_results = []

for test_driver in drivers:
    mask_test  = df['driver_id'] == test_driver
    mask_train = ~mask_test

    X_loo_train = df.loc[mask_train, ALL_FEATURES].values
    y_loo_train = df.loc[mask_train, 'label'].values.astype(int)
    X_loo_test  = df.loc[mask_test,  ALL_FEATURES].values
    y_loo_test  = df.loc[mask_test,  'label'].values.astype(int)

    sm = SMOTE(random_state=42)
    Xlt, ylt = sm.fit_resample(X_loo_train, y_loo_train)

    mdl_loo = HistGradientBoostingClassifier(
        learning_rate=0.05, max_iter=500, max_depth=8,
        class_weight='balanced', random_state=42
    )
    mdl_loo.fit(Xlt, ylt)
    yp = mdl_loo.predict(X_loo_test)
    yp_prob = mdl_loo.predict_proba(X_loo_test)[:, 1]

    loo_results.append({
        'Test Driver': int(test_driver),
        'Train Drivers': [d for d in drivers if d != test_driver],
        'Accuracy': accuracy_score(y_loo_test, yp),
        'F1':       f1_score(y_loo_test, yp),
        'ROC-AUC':  roc_auc_score(y_loo_test, yp_prob),
    })
    print(f"  Driver {test_driver} held out -> "
          f"Acc={loo_results[-1]['Accuracy']:.4f}  "
          f"F1={loo_results[-1]['F1']:.4f}  "
          f"AUC={loo_results[-1]['ROC-AUC']:.4f}")

loo_df = pd.DataFrame(loo_results)
print(f"\n  LOO Mean  -> F1={loo_df['F1'].mean():.4f} +/- {loo_df['F1'].std():.4f}  "
      f"AUC={loo_df['ROC-AUC'].mean():.4f} +/- {loo_df['ROC-AUC'].std():.4f}")

fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(loo_df))
ax.bar(x - 0.2, loo_df['F1'],       0.4, label='F1',      color='#42A5F5')
ax.bar(x + 0.2, loo_df['ROC-AUC'],  0.4, label='ROC-AUC', color='#66BB6A')
ax.set_xticks(x)
ax.set_xticklabels([f'Driver {d} (test)' for d in loo_df['Test Driver']])
ax.set_ylim(0.5, 1.05)
ax.set_ylabel('Score')
ax.set_title('Experiment 3: Cross-Driver LOO Generalisation')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('docs/figures/exp3_cross_driver_loo.png', dpi=150)
plt.close()
print("  Saved -> docs/figures/exp3_cross_driver_loo.png")

# STAGE 5d: EXPERIMENT 4 — LEARNING CURVE
print("\n  Experiment 4: Learning curve (overfitting check)...")

lc_model = HistGradientBoostingClassifier(
    learning_rate=0.05, max_iter=500, max_depth=8,
    class_weight='balanced', random_state=42
)
train_sizes_abs, train_scores, val_scores = learning_curve(
    lc_model, X_train_sm, y_train_sm,
    train_sizes=np.linspace(0.1, 1.0, 8),
    cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
    scoring='f1', n_jobs=1
)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(train_sizes_abs, train_scores.mean(axis=1), 'o-',
        color='#1565C0', label='Training F1')
ax.fill_between(train_sizes_abs,
                train_scores.mean(1) - train_scores.std(1),
                train_scores.mean(1) + train_scores.std(1),
                alpha=0.15, color='#1565C0')
ax.plot(train_sizes_abs, val_scores.mean(axis=1), 's--',
        color='#E53935', label='Cross-val F1')
ax.fill_between(train_sizes_abs,
                val_scores.mean(1) - val_scores.std(1),
                val_scores.mean(1) + val_scores.std(1),
                alpha=0.15, color='#E53935')
ax.set_xlabel('Training samples')
ax.set_ylabel('F1 Score')
ax.set_title('Experiment 4: Learning Curve')
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('docs/figures/exp4_learning_curve.png', dpi=150)
plt.close()
print("  Saved -> docs/figures/exp4_learning_curve.png")

# STAGE 6: FINAL MODEL TRAINING
print("\n[6/7] Training final model on train+val, evaluating on held-out test...")

X_tv = np.concatenate([X_train_sm, X_val])
y_tv = np.concatenate([y_train_sm, y_val])

final_model = HistGradientBoostingClassifier(
    learning_rate=0.05, max_iter=500, max_depth=8,
    class_weight='balanced', random_state=42
)
final_model.fit(X_tv, y_tv)

y_test_pred = final_model.predict(X_test)
y_test_prob = final_model.predict_proba(X_test)[:, 1]

acc  = accuracy_score(y_test, y_test_pred)
f1   = f1_score(y_test, y_test_pred)
pre  = precision_score(y_test, y_test_pred)
rec  = recall_score(y_test, y_test_pred)
auc  = roc_auc_score(y_test, y_test_prob)

print(f"\n  === FINAL TEST SET RESULTS ===")
print(f"  Accuracy  : {acc:.4f}  ({acc*100:.2f}%)")
print(f"  F1 Score  : {f1:.4f}")
print(f"  Precision : {pre:.4f}")
print(f"  Recall    : {rec:.4f}")
print(f"  ROC-AUC   : {auc:.4f}")
print(f"\n{classification_report(y_test, y_test_pred, target_names=['Safe','Aggressive'])}")

# Confusion matrix + ROC curve
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

cm = confusion_matrix(y_test, y_test_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=['Safe', 'Aggressive'])
disp.plot(ax=axes[0], cmap='Blues', colorbar=False)
axes[0].set_title('Confusion Matrix — Held-out Test Set')

fpr, tpr, _ = roc_curve(y_test, y_test_prob)
axes[1].plot(fpr, tpr, lw=2, color='#1565C0',
             label=f'HistGradBoost  AUC = {auc:.4f}')
axes[1].plot([0,1],[0,1],'k--', lw=1)
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('ROC Curve — Held-out Test Set')
axes[1].legend()
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('docs/figures/final_evaluation.png', dpi=150)
plt.close()
print("  Saved -> docs/figures/final_evaluation.png")

# STAGE 7: SAVE MODEL & SCALER
print("\n[7/7] Saving model and scaler...")

MODEL_PATH  = 'src/models/fyp_model.pkl'
SCALER_PATH = 'src/models/fyp_scaler.pkl'
META_PATH   = 'src/models/fyp_model_meta.json'

joblib.dump(final_model, MODEL_PATH)
joblib.dump(scaler,      SCALER_PATH)
print(f"  Model  saved -> {MODEL_PATH}")
print(f"  Scaler saved -> {SCALER_PATH}")

meta = {
    'trained_at':     datetime.now().isoformat(),
    'dataset':        'Combined: Kaggle OBD-II + Car-Specific Synthetic + Real Trip CSVs',
    'label_source':   'Balanced-v2 rules: RPM>2700&Thr>30 | Load>92&Thr>30 | SpeedChange>12',
    'features':       ALL_FEATURES,
    'signal_cols':    SIGNAL_COLS,
    'n_features':     len(ALL_FEATURES),
    'split':          '70/15/15 stratified',
    'smote':          'Applied to training fold only',
    'model':          'HistGradientBoostingClassifier',
    'hyperparams':    {'learning_rate': 0.05, 'max_iter': 500, 'max_depth': 8},
    'test_accuracy':  round(acc, 4),
    'test_f1':        round(f1,  4),
    'test_precision': round(pre, 4),
    'test_recall':    round(rec, 4),
    'test_roc_auc':   round(auc, 4),
    'loo_f1_mean':    round(float(loo_df['F1'].mean()), 4),
    'loo_f1_std':     round(float(loo_df['F1'].std()),  4),
}
with open(META_PATH, 'w') as mf:
    json.dump(meta, mf, indent=2)
print(f"  Metadata saved -> {META_PATH}")

# TRAINING COMPLETE
print(f"\n  Final Accuracy : {acc*100:.2f}%")
print(f"  Final F1       : {f1:.4f}")
print(f"  Final ROC-AUC  : {auc:.4f}")
print(f"  LOO F1 (gen.)  : {loo_df['F1'].mean():.4f} +/- {loo_df['F1'].std():.4f}")
print("\n  Figures saved in docs/figures/")
print("  Model + scaler saved in src/models/")
