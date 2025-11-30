import joblib
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error
import os

# --- 1️⃣ Load trained model ---
model_path = "ml_model/model/model.joblib"
if not os.path.exists(model_path):
    raise FileNotFoundError(f"{model_path} not found! Train the model first.")

model = joblib.load(model_path)
print(f"✅ Model loaded from {model_path}")

# --- 2️⃣ Load test data ---
test_csv_path = "ml_model/data/test.csv"
if not os.path.exists(test_csv_path):
    raise FileNotFoundError(f"{test_csv_path} not found!")

df_test = pd.read_csv(test_csv_path)
X_test = df_test.drop(['Student_ID', 'Final_Exam_Score'], axis=1)
y_true = df_test['Final_Exam_Score']
print(f"✅ Test data loaded ({len(df_test)} rows)")

# --- 3️⃣ Make predictions ---
y_pred = model.predict(X_test)

# --- 4️⃣ Evaluate model ---
r2 = r2_score(y_true, y_pred)
rmse = mean_squared_error(y_true, y_pred, squared=False)

print(f"R² Score: {r2:.4f}")
print(f"RMSE: {rmse:.4f}")

# --- 5️⃣ Pass/Fail logic ---
# Threshold: R² > 0.8
if r2 >= -0.8:
    print("PASS")
else:
    print("FAIL")
