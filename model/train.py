import pandas as pd
import numpy as np
import joblib # Use joblib to match model.joblib in inference.py
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def train_and_save_model():
    """
    Loads data, trains a RandomForest model, and saves the pipeline
    to 'model.joblib' in the current working directory.
    """
    print("Starting model training process...")

    # --- 1. Load Data ---
    # SageMaker typically mounts the input data to /opt/ml/input/data/training/
    # For local testing, we assume 'student_data.csv' is in the root directory.
    
    # Try to load data from the SageMaker training channel first, then locally.
    data_path = os.environ.get('SM_CHANNEL_TRAINING', '.')
    file_path = os.path.join(data_path, 'data/student_performance.csv')
    
    # Create mock data for testing completeness if the file is missing
    try:
        df = pd.read_csv(file_path)
    except Exception:
        print("student_data.csv not found in expected path.")
        # This mock data structure MUST match your actual dataset headers
        # data = {
        #     'Student_ID': [1, 2, 3, 4], 
        #     'Gender': ['Male', 'Female', 'Male', 'Female'],
        #     'Study_Hours_per_Week': [15.5, 22.0, 5.0, 18.2],
        #     'Attendance_Rate': [95.0, 99.0, 80.0, 92.5],
        #     'Midterm_Exam_Scores': [85.0, 92.0, 60.0, 78.0],
        #     'Parental_Education_Level': ['Bachelor', 'PhD', 'High School', 'Master'],
        #     'Internet_Access_at_Home': ['Yes', 'Yes', 'No', 'Yes'],
        #     'Extracurricular_Activities': ['Yes', 'No', 'Yes', 'No'],
        #     'Final_Exam_Score': [88.0, 95.0, 65.0, 80.0]
        # }
        # df = pd.DataFrame(data)

    # Define features and target
    X = df.drop(['Student_ID', 'Final_Exam_Score'], axis=1)
    y = df['Final_Exam_Score']

    # --- 2. Preprocessing Pipeline ---
    numerical_features = ['Study_Hours_per_Week', 'Attendance_Rate', 'Midterm_Exam_Scores']
    categorical_features = ['Gender', 'Parental_Education_Level', 'Internet_Access_at_Home', 'Extracurricular_Activities']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features), # Standardize numeric features
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features) # One-hot encode categorical features
        ],
        remainder='drop'
    )

    # --- 3. Model Pipeline ---
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    # --- 4. Training ---
    model_pipeline.fit(X, y)
    print("Model training complete.")

    # --- 5. Save Model Artifact ---
    # SageMaker requires the model artifact to be saved to /opt/ml/model/
    model_output_path = os.environ.get('SM_MODEL_DIR', '.') 
    
    # Save the trained model pipeline to 'model.joblib' 
    joblib.dump(model_pipeline, os.path.join(model_output_path, 'model.joblib'))
    
    print(f"Model saved to {os.path.join(model_output_path, 'model.joblib')}")

if __name__ == "__main__":
    train_and_save_model()