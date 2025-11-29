import streamlit as st
import boto3
import uuid
import json
from decimal import Decimal

# ----------------------
# AWS Clients
# ----------------------
dynamo = boto3.resource("dynamodb", region_name="ap-southeast-1")
lambda_client = boto3.client("lambda", region_name="ap-southeast-1")

TABLE_NAME = "StudentPerformancePredictions"
table = dynamo.Table(TABLE_NAME)

st.title("🎓 Student Performance Prediction System")

# ----------------------
# Helper: Decimal -> float for JSON
# ----------------------
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# ----------------------
# 1️⃣ Create / Update Student
# ----------------------
st.header("📌 Add or Update Student")

with st.form("student_form"):
    student_id = st.text_input("Student ID (leave empty for create):", "")
    gender = st.selectbox("Gender", ["Male", "Female"])
    study_hours = st.number_input("Study Hours per Week", 1, 100)
    attendance = st.number_input("Attendance Rate (%)", 1, 100)
    midterm = st.number_input("Midterm Exam Score", 1, 100)
    parent_edu = st.selectbox("Parental Education Level", ["High School", "Bachelor", "Master"])
    internet = st.selectbox("Internet Access at Home", ["Yes", "No"])
    extra = st.selectbox("Extracurricular Activities", ["Sports", "Music", "Art", "None"])

    submitted = st.form_submit_button("Save & Predict")

if submitted:
    # Generate new StudentID if empty
    if student_id.strip() == "":
        student_id = str(uuid.uuid4())

    # Prepare input data
    input_data = {
        "StudentID": student_id,
        "Gender": gender,
        "Study_Hours_per_Week": int(study_hours),
        "Attendance_Rate": int(attendance),
        "Midterm_Exam_Scores": int(midterm),
        "Parental_Education_Level": parent_edu,
        "Internet_Access_at_Home": internet,
        "Extracurricular_Activities": extra
    }

    # Call Lambda for prediction
    try:
        response = lambda_client.invoke(
            FunctionName="StudentPredictionLambda",
            InvocationType="RequestResponse",
            Payload=json.dumps({"body": input_data}, default=decimal_default)
        )
        result = json.loads(response["Payload"].read())
        prediction_value = None
        if "body" in result:
            body = json.loads(result["body"])
            prediction_value = body.get("prediction", [None])[0]

        # Save to DynamoDB
        item = input_data.copy()
        item["Predicted_Final_Score"] = float(prediction_value) if prediction_value is not None else None

        table.put_item(Item=item)
        st.success(f"Student saved! Predicted Final Score = {prediction_value}")

    except Exception as e:
        st.error(f"Error calling Lambda or saving to DynamoDB: {str(e)}")

# ----------------------
# 2️⃣ View Students
# ----------------------
st.header("📋 All Students")
try:
    students = table.scan().get("Items", [])
    if students:
        st.dataframe(students)
    else:
        st.info("No students found.")
except Exception as e:
    st.error(f"Error fetching students: {str(e)}")

# ----------------------
# 3️⃣ Update Prediction Manually
# ----------------------
st.header("🔄 Refresh Prediction for a Student")
all_ids = [s["StudentID"] for s in students] if students else []
if all_ids:
    selected_id = st.selectbox("Choose Student ID", all_ids)
    if st.button("Recalculate Prediction"):
        try:
            student = table.get_item(Key={"StudentID": selected_id}).get("Item")
            if student:
                response = lambda_client.invoke(
                    FunctionName="StudentPredictionLambda",
                    InvocationType="RequestResponse",
                    Payload=json.dumps({"body": student}, default=decimal_default)
                )
                result = json.loads(response["Payload"].read())
                body = json.loads(result.get("body", "{}"))
                prediction_value = body.get("prediction", [None])[0]

                if prediction_value is None:
                    st.error("Lambda did not return a prediction.")
                else:
                    student["Predicted_Final_Score"] = float(prediction_value)
                    table.put_item(Item=student)
                    st.success(f"Prediction Updated: {prediction_value}")


                student["Predicted_Final_Score"] = float(prediction_value)
                table.put_item(Item=student)
                st.success(f"Prediction Updated: {prediction_value}")
        except Exception as e:
            st.error(f"Error updating prediction: {str(e)}")

# ----------------------
# 4️⃣ Delete Student
# ----------------------
st.header("❌ Delete Student")
if all_ids:
    delete_id = st.selectbox("Select Student to Delete", all_ids, key="delete")
    if st.button("Delete Student"):
        try:
            table.delete_item(Key={"StudentID": delete_id})
            st.warning("Student deleted successfully.")
        except Exception as e:
            st.error(f"Error deleting student: {str(e)}")
