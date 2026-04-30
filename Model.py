import numpy as np, pandas as pd
from sklearn.metrics import roc_curve
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.callbacks import EarlyStopping # type: ignore
from tensorflow.keras.layers import Dense, Dropout, Input # type: ignore
from tensorflow.keras.models import Sequential # type: ignore

# Load training and test datasets from CSV files
train_data = pd.read_csv('ddos_train.csv')
test_data = pd.read_csv('ddos_test_with_labels.csv')

# Separate features and labels from training data
features, labels = train_data.drop(columns='label').values, train_data['label'].values

# Split training data into train/validation sets (85/15), preserving class balance
X_train, X_val, y_train, y_val = train_test_split(features, labels, test_size=0.15, random_state=42, stratify=labels)

# Fit scaler on training data only, then apply to both splits
scaler = StandardScaler().fit(X_train)
X_train, X_val = scaler.transform(X_train), scaler.transform(X_val)

# Compute class weights to penalize missed DDoS attacks more than false alarms
class_weights = {0: 1.0, 1: (y_train == 0).sum() / (y_train == 1).sum()}

# Build a fully-connected neural network with dropout regularization
model = Sequential([Input(shape=(features.shape[1],)), Dense(64,'relu'), Dropout(.3), Dense(32,'relu'), Dropout(.2), Dense(16,'relu'), Dense(1,'sigmoid')])

model.compile(optimizer='adam', loss='binary_crossentropy')

# Train with early stopping to avoid overfitting
model.fit(X_train, y_train, epochs=40, batch_size=128, validation_data=(X_val, y_val), class_weight=class_weights, callbacks=[EarlyStopping(patience=5, restore_best_weights=True)], verbose=0)

# Find the decision threshold that keeps false positive rate near 2%
false_pos_rates, _, thresholds = roc_curve(y_val, model.predict(X_val, verbose=0).flatten())
best_threshold = thresholds[np.argmin(np.abs(false_pos_rates - 0.02))]

# Scale test features using the same scaler fitted on training data
X_test = scaler.transform(test_data.drop(columns='label').values)
y_test = test_data['label'].values

# Apply tuned threshold to get final binary predictions
predictions = (model.predict(X_test, verbose=0).flatten() > best_threshold).astype(int)

# Count true positives, false positives, and false negatives
detected = ((predictions==1) & (y_test==1)).sum()
false_alarms = ((predictions==1) & (y_test==0)).sum()
missed = ((predictions==0) & (y_test==1)).sum()

# Print evaluation summary
print(f"\n=== Final Summary (Tuned Threshold {best_threshold:.4f}) ===")
print(f"Actual DDoS: {(y_test==1).sum()} | Actual Normal: {(y_test==0).sum()}")
print(f"Detected: {detected} ({detected/max((y_test==1).sum(),1):.1%} recall) | False Alarms: {false_alarms} ({false_alarms/max((y_test==0).sum(),1):.1%} FPR) | Missed: {missed}")