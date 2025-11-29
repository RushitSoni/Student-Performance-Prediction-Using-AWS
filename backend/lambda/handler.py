import json
from utils import invoke_sagemaker, store_in_dynamodb
import boto3

# DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
table = dynamodb.Table('StudentPerformancePredictions')

def lambda_handler(event, context):
    try:
        data = json.loads(event.get('body', '{}'))
        prediction = invoke_sagemaker(data)
        store_in_dynamodb(table, data, prediction)
        return {
            "statusCode": 200,
            "body": json.dumps({"input": data, "prediction": prediction})
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


###################
