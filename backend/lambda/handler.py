import json
import boto3

# SageMaker runtime client
runtime = boto3.client("sagemaker-runtime")

# DynamoDB table name
TABLE_NAME = "StudentPerformancePredictions"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# Your SageMaker endpoint name
ENDPOINT_NAME = "student-performance-model-6-endpoint"

def lambda_handler(event, context):
    try:
        # Get operation and data from event
        body = event.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        operation = event.get("operation", "CREATE").upper()
        data = body

        if operation == "CREATE" or operation == "UPDATE":
            # Call SageMaker endpoint for prediction
            payload = json.dumps([{
                "Gender": data["Gender"],
                "Study_Hours_per_Week": data["Study_Hours_per_Week"],
                "Attendance_Rate": data["Attendance_Rate"],
                "Midterm_Exam_Scores": data["Midterm_Exam_Scores"],
                "Parental_Education_Level": data["Parental_Education_Level"],
                "Internet_Access_at_Home": data["Internet_Access_at_Home"],
                "Extracurricular_Activities": data["Extracurricular_Activities"]
            }])

            response = runtime.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType="application/json",
                Body=payload
            )

            result = json.loads(response["Body"].read().decode("utf-8"))
            prediction = result.get("prediction", [None])[0]

            # Save/update in DynamoDB
            item = data.copy()
            item["Predicted_Final_Score"] = float(prediction) if prediction is not None else None
            table.put_item(Item=item)

            return {
                "statusCode": 200,
                "body": json.dumps({"success": True, "prediction": [prediction]})
            }

        elif operation == "READ":
            if "StudentID" in data:
                resp = table.get_item(Key={"StudentID": data["StudentID"]})
                items = [resp["Item"]] if "Item" in resp else []
            else:
                resp = table.scan()
                items = resp.get("Items", [])
            return {
                "statusCode": 200,
                "body": json.dumps({"success": True, "data": items})
            }

        elif operation == "DELETE":
            table.delete_item(Key={"StudentID": data["StudentID"]})
            return {
                "statusCode": 200,
                "body": json.dumps({"success": True, "message": "Deleted"})
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid operation"})
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "prediction": [None]})
        }
