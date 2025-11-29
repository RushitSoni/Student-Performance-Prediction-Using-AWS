import streamlit as st
import boto3
import uuid
import json

# AWS Clients
dynamo = boto3.resource("dynamodb", region_name="ap-southeast-1")
lambda_client = boto3.client("lambda", region_name="ap-southeast-1")

TABLE_NAME = "StudentPredictions"
table = dynamo.Table(TABLE_NAME)

st.title("🎓 Student Performance Prediction System")


# ----------------------
# 1️⃣ Create / Update Form
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
    # Generate new ID if creating
    if student_id.strip() == "":
        student_id = str(uuid.uuid4())

    # Prepare input data
    input_data = {
        "Gender": gender,
        "Study_Hours_per_Week": int(study_hours),
        "Attendance_Rate": int(attendance),
        "Midterm_Exam_Scores": int(midterm),
        "Parental_Education_Level": parent_edu,
        "Internet_Access_at_Home": internet,
        "Extracurricular_Activities": extra
    }

    # Invoke Lambda for prediction
    response = lambda_client.invoke(
        FunctionName="StudentPredictionLambda",
        InvocationType="RequestResponse",
        Payload=json.dumps({"body": input_data})
    )

    result = json.loads(response["Payload"].read())

    if "body" in result:
        body = json.loads(result["body"])
        prediction_value = body.get("prediction", [None])[0]

        # Save/update DynamoDB row
        table.put_item(
            Item={
                "StudentId": student_id,
                "Gender": gender,
                "Study_Hours_per_Week": int(study_hours),
                "Attendance_Rate": int(attendance),
                "Midterm_Exam_Scores": int(midterm),
                "Parental_Education_Level": parent_edu,
                "Internet_Access_at_Home": internet,
                "Extracurricular_Activities": extra,
                "Predicted_Final_Score": float(prediction_value)
            }
        )

        st.success(f"Student saved! Predicted Final Score = {prediction_value}")
    else:
        st.error("Lambda error: " + str(result))


# ----------------------
# 2️⃣ View Students
# ----------------------
st.header("📋 All Students")

students = table.scan().get("Items", [])

if students:
    st.table(students)
else:
    st.info("No students found.")


# ----------------------
# 3️⃣ Update Prediction Manually
# ----------------------
st.header("🔄 Refresh Prediction for a Student")

all_ids = [s["StudentId"] for s in students]
if all_ids:
    selected_id = st.selectbox("Choose Student ID", all_ids)
    if st.button("Recalculate Prediction"):
        # Fetch student data
        student = table.get_item(Key={"StudentId": selected_id}).get("Item")

        if student:
            input_data = {
                "Gender": student["Gender"],
                "Study_Hours_per_Week": student["Study_Hours_per_Week"],
                "Attendance_Rate": student["Attendance_Rate"],
                "Midterm_Exam_Scores": student["Midterm_Exam_Scores"],
                "Parental_Education_Level": student["Parental_Education_Level"],
                "Internet_Access_at_Home": student["Internet_Access_at_Home"],
                "Extracurricular_Activities": student["Extracurricular_Activities"]
            }

            # Lambda call
            response = lambda_client.invoke(
                FunctionName="StudentPredictionLambda",
                InvocationType="RequestResponse",
                Payload=json.dumps({"body": input_data})
            )
            result = json.loads(response["Payload"].read())
            body = json.loads(result["body"])
            prediction_value = body["prediction"][0]

            # Save updated prediction
            student["Predicted_Final_Score"] = float(prediction_value)
            table.put_item(Item=student)

            st.success(f"Prediction Updated: {prediction_value}")


# ----------------------
# 4️⃣ Delete Student
# ----------------------
st.header("❌ Delete Student")

if all_ids:
    delete_id = st.selectbox("Select Student to Delete", all_ids, key="delete")

    if st.button("Delete Student"):
        table.delete_item(Key={"StudentId": delete_id})
        st.warning("Student deleted successfully.")
