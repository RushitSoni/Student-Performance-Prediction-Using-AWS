import json
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("StudentPerformancePredictions")

runtime = boto3.client("sagemaker-runtime")
SAGEMAKER_ENDPOINT = "student-performance-model-6-endpoint"


def predict_mark(data):
    """Calls SageMaker endpoint for prediction"""
    response = runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps([data])  # SageMaker expects a list
    )
    result = json.loads(response["Body"].read().decode("utf-8"))
    return result["prediction"][0]


def lambda_handler(event, context):
    print("EVENT:", event)

    operation = event.get("operation")
    data = event.get("data")

    try:
        # -----------------------------
        # CREATE
        # -----------------------------
        if operation == "CREATE":
            prediction = predict_mark(data)
            data["PredictedFinalScore"] = float(prediction)

            table.put_item(Item=data)
            return {"success": True, "message": "Student created", "prediction": prediction}

        # -----------------------------
        # READ
        # -----------------------------
        if operation == "READ":
            if "StudentID" in data:
                response = table.get_item(Key={"StudentID": data["StudentID"]})
                return {"success": True, "data": [response.get("Item", {})]}
            else:
                response = table.scan()
                return {"success": True, "data": response["Items"]}

        # -----------------------------
        # UPDATE
        # -----------------------------
        if operation == "UPDATE":
            prediction = predict_mark(data)
            data["PredictedFinalScore"] = float(prediction)

            update_expr = "SET " + ", ".join([f"{k}= :{k}" for k in data if k != "StudentID"])
            expr_vals = {f":{k}": v for k, v in data.items() if k != "StudentID"}

            table.update_item(
                Key={"StudentID": data["StudentID"]},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_vals
            )

            return {"success": True, "message": "Student updated", "prediction": prediction}

        # -----------------------------
        # DELETE
        # -----------------------------
        if operation == "DELETE":
            table.delete_item(Key={"StudentID": data["StudentID"]})
            return {"success": True, "message": "Student deleted"}

        return {"success": False, "error": "Invalid operation"}

    except Exception as e:
        return {"success": False, "error": str(e)}
