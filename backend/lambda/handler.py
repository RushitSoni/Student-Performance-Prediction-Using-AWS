import json
import boto3
from decimal import Decimal

# ----------------------
# AWS Clients
# ----------------------
dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
table = dynamodb.Table("StudentPerformancePredictions")

runtime = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")
sagemaker_endpoint = "student-performance-model-6-endpoint"  # Replace with your endpoint

# Helper: Convert floats to Decimal for DynamoDB
def convert_to_decimal(item):
    for k, v in item.items():
        if isinstance(v, float):
            item[k] = Decimal(str(v))
    return item

# Lambda handler
def lambda_handler(event, context):
    try:
        operation = event.get("operation")
        data = event.get("data")

        if operation not in ["CREATE", "READ", "UPDATE", "DELETE"]:
            return {"success": False, "error": f"Unsupported operation: {operation}"}

        # ----------------------
        # CREATE
        # ----------------------
        if operation == "CREATE":
            # Call SageMaker for prediction
            payload = json.dumps([data])  # list of dicts
            sm_response = runtime.invoke_endpoint(
                EndpointName=sagemaker_endpoint,
                ContentType="application/json",
                Body=payload
            )
            sm_result = json.loads(sm_response["Body"].read().decode("utf-8"))
            prediction = sm_result.get("prediction", [None])[0]

            # Save to DynamoDB
            item = data.copy()
            if prediction is not None:
                item["Predicted_Final_Score"] = Decimal(str(prediction))
            item = convert_to_decimal(item)
            table.put_item(Item=item)

            return {"success": True, "message": "Student created", "prediction": [prediction]}

        # ----------------------
        # READ
        # ----------------------
        elif operation == "READ":
            if "StudentID" in data:
                response = table.get_item(Key={"StudentID": data["StudentID"]})
                items = [response["Item"]] if "Item" in response else []
            else:
                response = table.scan()
                items = response.get("Items", [])

            # Convert Decimals to float for JSON serialization
            for item in items:
                for k, v in item.items():
                    if isinstance(v, Decimal):
                        item[k] = float(v)
            return {"success": True, "data": items}

        # ----------------------
        # UPDATE
        # ----------------------
        elif operation == "UPDATE":
            student_id = data.get("StudentID")
            if not student_id:
                return {"success": False, "error": "StudentID is required for update"}

            # Call SageMaker for prediction
            payload = json.dumps([data])
            sm_response = runtime.invoke_endpoint(
                EndpointName=sagemaker_endpoint,
                ContentType="application/json",
                Body=payload
            )
            sm_result = json.loads(sm_response["Body"].read().decode("utf-8"))
            prediction = sm_result.get("prediction", [None])[0]

            # Update DynamoDB
            update_expr = "SET " + ", ".join([f"{k}=:{k}" for k in data if k != "StudentID"])
            expr_values = {f":{k}": Decimal(str(v)) if isinstance(v, float) else v
                           for k, v in data.items() if k != "StudentID"}
            if prediction is not None:
                update_expr += ", Predicted_Final_Score=:Predicted_Final_Score"
                expr_values[":Predicted_Final_Score"] = Decimal(str(prediction))

            table.update_item(
                Key={"StudentID": student_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )

            return {"success": True, "message": "Student updated", "prediction": [prediction]}

        # -----------------
        # DELETE
        # ----------------------
        elif operation == "DELETE":
            student_id = data.get("StudentID")
            if not student_id:
                return {"success": False, "error": "StudentID is required for delete"}

            table.delete_item(Key={"StudentID": student_id})
            return {"success": True, "message": "Student deleted"}

    except Exception as e:
        return {"success": False, "error": str(e), "prediction": [None]}
