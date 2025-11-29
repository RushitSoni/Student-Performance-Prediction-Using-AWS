import boto3
import time
import os
import sagemaker
print(sagemaker.__version__)

from sagemaker import image_uris
container=image_uris.retrieve(framework='sklearn',region='ap-southeast-1',version='0.23-1')
print(container)




# --- CONFIGURATION ---
s3_bucket = "g30-student-performance-analysis"       # Your S3 bucket
s3_model_key = "model-artifacts/model.tar.gz"                  # Path to your model in S3
model_name = "student-performance-model-1"            # SageMaker model name
endpoint_config_name = f"{model_name}-config"
endpoint_name = f"{model_name}-endpoint"
role_arn = os.environ.get("SAGEMAKER_ROLE_ARN")     # IAM role with SageMaker permissions
region = os.environ.get("AWS_REGION", "ap-southeast-1")  # AWS region

sm_client = boto3.client("sagemaker", region_name=region)

# --- 1️⃣ Create SageMaker model ---
print(f"Creating SageMaker model: {model_name}...")
try:
    sm_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            "Image": container,
            "ModelDataUrl": f"s3://{s3_bucket}/{s3_model_key}"
        },
        ExecutionRoleArn=role_arn
    )
    print("✅ Model created successfully.")
except sm_client.exceptions.ClientError as e:
    if "AlreadyExists" in str(e):
        print("⚠️ Model already exists, skipping creation.")
    else:
        raise e

# --- 2️⃣ Create endpoint configuration --
print(f"Creating endpoint configuration: {endpoint_config_name}...")
try:
    sm_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "InitialInstanceCount": 1,
                "InstanceType": "ml.t2.medium",
                "InitialVariantWeight": 1
            }
        ]
    )
    print("✅ Endpoint configuration created.")
except sm_client.exceptions.ClientError as e:
    if "AlreadyExists" in str(e):
        print("⚠️ Endpoint configuration already exists, skipping creation.")
    else:
        raise e

# --- 3️⃣ Deploy endpoint ---
print(f"Creating endpoint: {endpoint_name}...")
try:
    sm_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
    print("⏳ Endpoint creation started, this may take several minutes...")
except sm_client.exceptions.ClientError as e:
    if "AlreadyExists" in str(e):
        print("⚠️ Endpoint already exists, skipping creation.")
    else:
        raise e

# --- 4️⃣ Wait for endpoint to be in service ---
print(f"Waiting for endpoint {endpoint_name} to be InService...")
waiter = sm_client.get_waiter("endpoint_in_service")
waiter.wait(EndpointName=endpoint_name)
print(f"🎉 Endpoint {endpoint_name} is now InService and ready to use!")
