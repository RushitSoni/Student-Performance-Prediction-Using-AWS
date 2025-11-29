import json
import boto3
from decimal import Decimal

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
table = dynamodb.Table('StudentPerformancePredictions')

# SageMaker runtime client
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name='ap-southeast-1')
SAGEMAKER_ENDPOINT = "student-performance-model-6-endpoint"  # replace with your actual endpoint


def predict_final_score_sagemaker(student_data):
    # Convert data to JSON string
    payload = json.dumps(student_data)
    
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=payload
    )
    
    result = json.loads(response['Body'].read().decode())
    
    # Expecting result like: {"prediction": [63.41]}
    prediction = result.get('prediction', [None])[0]
    if prediction is None:
        raise ValueError("SageMaker did not return a prediction")
    
    return float(prediction)


def lambda_handler(event, context):
    try:
        operation = event.get('operation')
        data = event.get('data', {})

        if not operation or not isinstance(data, dict):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid input'})
            }

        # CREATE
        if operation == 'CREATE':
            predicted_score = predict_final_score_sagemaker(data)

            item = {
                'StudentID': data['StudentID'],
                'Gender': data['Gender'],
                'Study_Hours_per_Week': Decimal(str(data['Study_Hours_per_Week'])),
                'Attendance_Rate': Decimal(str(data['Attendance_Rate'])),
                'Midterm_Exam_Scores': Decimal(str(data['Midterm_Exam_Scores'])),
                'Parental_Education_Level': data['Parental_Education_Level'],
                'Internet_Access_at_Home': data['Internet_Access_at_Home'],
                'Extracurricular_Activities': data['Extracurricular_Activities'],
                'Predicted_Final_Score': Decimal(str(predicted_score))
            }

            table.put_item(Item=item)

            return {
                'statusCode': 200,
                'body': json.dumps({'success': True, 'prediction': [predicted_score]})
            }

        # READ
        elif operation == 'READ':
            if 'StudentID' in data:
                response = table.get_item(Key={'StudentID': data['StudentID']})
                items = [response['Item']] if 'Item' in response else []
            else:
                response = table.scan()
                items = response.get('Items', [])

            for item in items:
                for k, v in item.items():
                    if isinstance(v, Decimal):
                        item[k] = float(v)

            return {
                'statusCode': 200,
                'body': json.dumps({'success': True, 'data': items})
            }

        # UPDATE
        elif operation == 'UPDATE':
            predicted_score = predict_final_score_sagemaker(data)

            update_expression = "SET " + ", ".join(
                [f"{k}=:{k}" for k in data if k != 'StudentID'] + ["Predicted_Final_Score=:Predicted_Final_Score"]
            )

            expression_values = {f":{k}": Decimal(str(v)) if isinstance(v, (int, float)) else v
                                 for k, v in data.items() if k != 'StudentID'}
            expression_values[":Predicted_Final_Score"] = Decimal(str(predicted_score))

            table.update_item(
                Key={'StudentID': data['StudentID']},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )

            return {
                'statusCode': 200,
                'body': json.dumps({'success': True, 'prediction': [predicted_score]})
            }

        # DELETE
        elif operation == 'DELETE':
            table.delete_item(Key={'StudentID': data['StudentID']})
            return {
                'statusCode': 200,
                'body': json.dumps({'success': True, 'message': 'Student deleted'})
            }

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown operation {operation}'})
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'prediction': [None]})
        }
