import pandas as pd
import joblib
import boto3
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
import os

def train_and_save_model():
    print("🚀 Starting model training")

    # --- 1. Load CSV from local repo ---
    local_csv_path = "ml_model/data/student_performance.csv"
    if not os.path.exists(local_csv_path):
        raise FileNotFoundError(f"{local_csv_path} not found!")
    
    df = pd.read_csv(local_csv_path)
    print("✅ Data loaded from local CSV")

    # --- 2. Prepare data ---
    X = df.drop(['Student_ID', 'Final_Exam_Score'], axis=1)
    y = df['Final_Exam_Score']

    numerical_features = ['Study_Hours_per_Week', 'Attendance_Rate', 'Midterm_Exam_Scores']
    categorical_features = [
        'Gender', 'Parental_Education_Level',
        'Internet_Access_at_Home', 'Extracurricular_Activities'
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )

    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    # --- 3. Train the model ---
    print("📚 Training model...")
    model_pipeline.fit(X, y)
    print("✅ Model training complete")

    # --- 4. Save model locally ---
    local_model_path = "ml_model/model/model.joblib"
    os.makedirs(os.path.dirname(local_model_path), exist_ok=True)
    joblib.dump(model_pipeline, local_model_path)
    print(f"💾 Model saved locally at {local_model_path}")

    # --- 5. Upload model to S3 ---
    bucket_name = "g30-student-performance-analysis"         # Replace with your bucket
    s3_key = "model-artifacts/model.joblib"        # Path inside bucket

    #s3 = boto3.client("s3")
    s3 = boto3.client("s3")

    print(f"📤 Uploading model to s3://{bucket_name}/{s3_key} ...")
    s3.upload_file(local_model_path, bucket_name, s3_key)
    print(f"🎉 Model uploaded successfully to s3://{bucket_name}/{s3_key}")

if __name__ == "__main__":
    train_and_save_model()
