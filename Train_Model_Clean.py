# FYP: Driver Behavior Scoring - Training with Real Data
# Dataset Used: data/cleaned/all_drivers_combined.csv


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


# Step 1: Load Cleaned Dataset

# Load the preprocessed English dataset
df = pd.read_csv('data/cleaned/all_drivers_combined.csv')

print(f"Total rows: {len(df):,}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst 5 rows:")
df.head()


# Check data quality
print("Missing values:")
print(df.isnull().sum())

print("\nBasic statistics:")
df.describe()


# Step 2: Create Labels (Aggressive vs Safe)

# Create derived features
df['speed_change'] = df['speed'].diff().abs()
df['throttle_jerk'] = df['throttle'].diff().abs()

# Create labels using research-based thresholds
df['label'] = 0  # Default: Safe

aggressive_mask = (
    ((df['rpm'] > 3000) & (df['throttle'] > 70)) |
    (df['speed_change'] > 15)
)

df.loc[aggressive_mask, 'label'] = 1  # Aggressive

df = df.dropna()

print(f"Safe driving samples: {(df['label'] == 0).sum():,}")
print(f"Aggressive driving samples: {(df['label'] == 1).sum():,}")


# Step 3: Feature Engineering

# Rolling window features
window = 5
df['speed_mean'] = df['speed'].rolling(window=window).mean()
df['speed_std'] = df['speed'].rolling(window=window).std()
df['rpm_mean'] = df['rpm'].rolling(window=window).mean()

df = df.dropna()

print(f"Final dataset size: {len(df):,} rows")
df.head()


# Visualize patterns
sample = df.sample(min(1000, len(df)))

plt.figure(figsize=(14, 6))
plt.subplot(1, 2, 1)
sns.scatterplot(data=sample, x='speed', y='rpm', hue='label', palette={0: 'green', 1: 'red'}, alpha=0.6)
plt.title('Safe (Green) vs Aggressive (Red) Driving')

plt.subplot(1, 2, 2)
sns.histplot(data=df, x='throttle', hue='label', bins=30, multiple='stack')
plt.title('Throttle Distribution')

plt.tight_layout()
plt.show()


# Step 4: Train Model

# Prepare features
feature_cols = ['speed', 'rpm', 'throttle', 'speed_mean', 'speed_std', 'rpm_mean', 'throttle_jerk']
X = df[feature_cols]
y = df['label']

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"Training samples: {len(X_train):,}")
print(f"Test samples: {len(X_test):,}")


# Train Random Forest
clf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
clf.fit(X_train, y_train)

# Predict
y_pred = clf.predict(X_test)

# Evaluate
accuracy = accuracy_score(y_test, y_pred)
print(f"\nAccuracy: {accuracy * 100:.2f}%\n")
print(classification_report(y_test, y_pred, target_names=['Safe', 'Aggressive']))


# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Safe', 'Aggressive'], yticklabels=['Safe', 'Aggressive'])
plt.title('Confusion Matrix')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.show()


# Feature Importance
importances = pd.DataFrame({
    'feature': feature_cols,
    'importance': clf.feature_importances_
}).sort_values('importance', ascending=False)

plt.figure(figsize=(10, 5))
sns.barplot(data=importances, x='importance', y='feature', palette='viridis')
plt.title('Feature Importance')
plt.show()

importances


# Step 5: Save Model

# Save the trained model
os.makedirs('src/models', exist_ok=True)
joblib.dump(clf, 'src/models/driver_model.pkl')
print("Model saved to src/models/driver_model.pkl")
print("\nYou can now run: python main.py --mode simulation")

