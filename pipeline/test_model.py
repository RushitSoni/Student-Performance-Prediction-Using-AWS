import boto3
import joblib
import os
import numpy as np

# ----------------------------
# Config
s3_bucket = "g30-student-performance-analysis"
s3_model_path = "model-artifacts/model.joblib"
local_model_path = "/tmp/model.joblib"
sample_input = np.array([[15.5, 95.0, 85.0, 1, 0, 0, 1, 1, 0]])  # Example encoded input (adjust for your preprocessing)
# ----------------------------

# Download model from S3
s3 = boto3.client("s3")
print("Downloading model artifact from S3...")
s3.download_file(s3_bucket, s3_model_path, local_model_path)

# Load model
with open(local_model_path, "rb") as f:
    model = joblib.load(f)

# Run sample inference
print("Running sample inference...")
output = model.predict(sample_input)
print("Sample output:", output)

# Basic validation
if output is None or len(output) == 0:
    raise Exception("Model test failed! Output is empty.")
else:
    print("Model test passed successfully!")
