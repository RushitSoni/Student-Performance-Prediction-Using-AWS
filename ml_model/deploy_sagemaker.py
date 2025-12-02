import os
import sagemaker
import boto3
import time
from sagemaker.sklearn.model import SKLearnModel

# --- CONFIG ---
s3_bucket = "g30-student-performance-analysis"
s3_model_key = "model-artifacts/model.tar.gz"
model_s3_uri = f"s3://{s3_bucket}/{s3_model_key}"

# Fixed endpoint name
endpoint_name = "student-performance-model-endpoint"

# Unique model name for each deploy (timestamp-based)
timestamp = int(time.time())
model_name = f"student-performance-model-{timestamp}"



role_arn = os.environ.get("SAGEMAKER_ROLE_ARN")   
region = os.environ.get("AWS_REGION", "ap-southeast-1")

print("Using role:", role_arn)
print("Using region:", region)
print("Model S3 URI:", model_s3_uri)
print(f"Endpoint name (fixed): {endpoint_name}")
print(f"Model name (unique): {model_name}")
endpoint_config_name = f"{endpoint_name}-config-{int(time.time())}"

# INIT CLIENTS

sm_client = boto3.client("sagemaker", region_name=region)
sess = sagemaker.Session()


# --- Create SKLearn Model ---
print("\n📌 Creating SKLearnModel object...")

model = SKLearnModel(
    model_data=model_s3_uri,
    role=role_arn,
    entry_point="ml_model/inference.py",   # Required inference script
    framework_version="1.2-1",             # Must match sklearn version
    sagemaker_session=sess,
    name=model_name
)

print("✅ SKLearnModel created.")

# Create the model in SageMaker
try:
    model.create()
    print(f"✅ Model '{model_name}' created in SageMaker.")
except sm_client.exceptions.ClientError as e:
    if "AlreadyExists" in str(e):
        print(f"⚠️ Model '{model_name}' already exists, skipping creation.")
    else:
        raise e

# CHECK IF ENDPOINT EXISTS

try:
    sm_client.describe_endpoint(EndpointName=endpoint_name)
    endpoint_exists = True
    print(f"⚠️ Endpoint '{endpoint_name}' already exists. Will update it with new model...")
except sm_client.exceptions.ClientError as e:
    if "Could not find endpoint" in str(e) or "ValidationException" in str(e):
        endpoint_exists = False
        print(f"✅ Endpoint '{endpoint_name}' does not exist. Will create a new one.")
    else:
        raise e


# DEPLOY / UPDATE ENDPOINT

if not endpoint_exists:
    # Create new endpoint
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type="ml.t2.medium",
        endpoint_name=endpoint_name
    )
    print(f"🎉 New endpoint '{endpoint_name}' created with model '{model_name}'!")
else:
    # Update existing endpoint with new model
    sm_client.create_endpoint_config(
    EndpointConfigName=endpoint_config_name,
    ProductionVariants=[
        {
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium",
            "InitialVariantWeight": 1,
        }
    ],
    )

    response = sm_client.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
  
   
    print(response)
    
    print(f"🔄 Endpoint '{endpoint_name}' updated successfully with model '{model_name}'!")

    
