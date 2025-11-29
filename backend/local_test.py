import boto3
import json

# SageMaker runtime client
sm_client = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")

# Sample input matching your model
sample_input = [
    {
        "Gender": "Male",
        "Study_Hours_per_Week": 12,
        "Attendance_Rate": 95,
        "Midterm_Exam_Scores": 88,
        "Parental_Education_Level": "Bachelor",
        "Internet_Access_at_Home": "Yes",
        "Extracurricular_Activities": "Sports"
    },
    {
        "Gender": "Female",
        "Study_Hours_per_Week": 18,
        "Attendance_Rate": 50,
        "Midterm_Exam_Scores": 60,
        "Parental_Education_Level": "High School",
        "Internet_Access_at_Home": "No",
        "Extracurricular_Activities": "Music"
    }
]

# Convert to JSON (SageMaker expects a list of dicts)
payload = json.dumps(sample_input)

# Invoke endpoint
response = sm_client.invoke_endpoint(
    EndpointName='student-performance-model-6-endpoint',  # your SageMaker endpoint
    ContentType="application/json",
    Body=payload
)

# Read predictions
result = response["Body"].read().decode("utf-8")
predictions = json.loads(result)

print("Predictions:", predictions["prediction"])
