import boto3
import sagemaker
from sagemaker.model import Model
import os

# -------------------
# Config
s3_model_uri = "s3://g30-student-performance-analysis/model-artifacts/model.joblib"
endpoint_name = "student-performance-prod"
role = os.environ.get("SAGEMAKER_ROLE", "arn:aws:iam::123456789012:role/SageMakerExecutionRole")
instance_type = "ml.m5.large"
# ----------------------------

sess = sagemaker.Session(boto_session=boto3.Session())

# Create SageMaker model object
model = Model(
    model_data=s3_model_uri,
    image_uri="382416733822.dkr.ecr.us-east-1.amazonaws.com/sklearn-inference:0.24-1-cpu-py38",
    role=role,
    sagemaker_session=sess
)

# Deploy to production endpoint
print(f"Deploying model to production endpoint: {endpoint_name}")
predictor = model.deploy(
    initial_instance_count=1,
    instance_type=instance_type,
    endpoint_name=endpoint_name,
    update_endpoint=True
)

print("Production deployment successful!")
