import boto3
from decimal import Decimal
from datetime import datetime
import uuid
import json

# SageMaker runtime
sm_client = boto3.client("sagemaker-runtime", region_name='ap-southeast-1')

def invoke_sagemaker(data):
    payload = json.dumps([data])
    response = sm_client.invoke_endpoint(
        EndpointName='student-performance-model-6-endpoint',
        ContentType='application/json',
        Body=payload
    )
    result = json.loads(response['Body'].read().decode())
    return result["prediction"]

def convert_floats(obj):
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

def store_in_dynamodb(table, input_data, prediction):
    item = {
        'id': str(uuid.uuid4()),
        'input': convert_floats(input_data),
        'prediction': convert_floats(prediction),
        'timestamp': datetime.utcnow().isoformat()
    }
    table.put_item(Item=item)
