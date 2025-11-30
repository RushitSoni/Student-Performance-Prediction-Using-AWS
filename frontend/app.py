import streamlit as st
import boto3
import pandas as pd
from decimal import Decimal
import json
import time
import uuid

# Page config
st.set_page_config(page_title="Student Performance Prediction", layout="wide", initial_sidebar_state="collapsed")

# AWS Clients 
def get_aws_clients():
    dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
    table = dynamodb.Table("StudentPerformancePredictions")
    runtime = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")
    return table, runtime

table, runtime = get_aws_clients()
sagemaker_endpoint = "student-performance-model-endpoint"

# Helper Functions 
def convert_to_decimal(item):
    for k, v in item.items():
        if isinstance(v, float):
            item[k] = Decimal(str(v))
    return item

def decimal_to_float(items):
    for item in items:
        for k, v in item.items():
            if isinstance(v, Decimal):
                item[k] = float(v)
    return items

#SageMaker call
def get_prediction(data):
    try:
        payload = json.dumps([data])
        sm_response = runtime.invoke_endpoint(
            EndpointName=sagemaker_endpoint,
            ContentType="application/json",
            Body=payload
        )
        sm_result = json.loads(sm_response["Body"].read().decode("utf-8"))
        return sm_result.get("prediction", [None])[0]
    except Exception as e:
        st.error(f"Prediction error: {str(e)}")
        return None

# DynamoDB scan
def read_all():
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    return pd.DataFrame(decimal_to_float(items))

def create_student(data):
    prediction = get_prediction(data)
    item = data.copy()
    if prediction is not None:
        item["Predicted_Final_Score"] = Decimal(str(prediction))
    item = convert_to_decimal(item)
    table.put_item(Item=item)
    return prediction

def student_exists(student_id):
    """Check if student ID already exists"""
    try:
        response = table.get_item(Key={"StudentID": student_id})
        return "Item" in response
    except:
        return False

def update_student(student_id, data):
    prediction = get_prediction(data)
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
    return prediction

def delete_student(student_id):
    table.delete_item(Key={"StudentID": student_id})

def generate_student_id():
    return f"S{uuid.uuid4().hex[:3].upper()}"

desired_order = [
    "StudentID",
    "Gender",
    "Study_Hours_per_Week",
    "Attendance_Rate",
    "Midterm_Exam_Scores",
    "Parental_Education_Level",
    "Internet_Access_at_Home",
    "Extracurricular_Activities",
    "Predicted_Final_Score"
]




# MAIN UI 
def main():
    st.title("🎓 Student Performance Prediction")
    
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown("**Predict student's final exam score using past performance data.** | " + time.strftime("%H:%M:%S"))
    # with col2:
    #     if st.button("🔄 Refresh Data"):
    #         st.success("🔄 Refreshed!")
    #         st.rerun()
    
    df = read_all()

    # Custom CSS for equal-width tabs (25% each)
    st.markdown("""
        <style>
        div[data-baseweb="tab-list"] > div {
            flex: 1 !important;
            max-width: 25% !important;
        }
        </style>
    """, unsafe_allow_html=True)

    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 View All", "➕ Create", "✏️ Update", "❌ Delete"])

    
    with tab1:
        st.subheader("📈 All Students")
        if df.empty:
            st.warning("👥 No students. Create first!")
        else:
            st.success(f"✅ {len(df)} students loaded")
            
            # METRICS
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("👥 Total", len(df))
            with col2: st.metric("📈 Avg Score", f"{df['Predicted_Final_Score'].mean():.1f}")
            with col3: st.metric("📊 Attendance", f"{df['Attendance_Rate'].mean():.1f}%")
            with col4: st.metric("⭐ Top Students", len(df[df["Predicted_Final_Score"] >= 60]))

            df = df[desired_order]   # Reorder the columns
            
            st.dataframe(df, height=400, use_container_width=True)
    
    with tab2:
        st.subheader("➕ Create Student")
        with st.form("create_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                student_id = st.text_input("**Student ID**", placeholder="202511111", help="Enter unique ID")
                gender = st.selectbox("Gender", ["Male", "Female"])
                study_hours = st.number_input("Study Hours/Week", min_value=0.0,max_value=168.0,step=1.0)
                if study_hours > 168.0:
                    st.warning("Maximum allowed is 168.")
                    study_hours = 168.0

                if study_hours < 0:
                    st.warning("Minimum allowed is 0.")
                    study_hours = 0.0

                attendance = st.number_input("Attendance %", min_value=0.0,max_value=100.0,step=1.0)
                if attendance > 100:
                    st.warning("Maximum allowed is 100.")
                    attendance = 100.0

                if attendance < 0:
                    st.warning("Minimum allowed is 0.")
                    attendance = 0.0

            with col2:
                midterm = st.number_input("Midterm Score", min_value=0.0,max_value=100.0,step=1.0)
                if midterm > 100:
                    st.warning("Maximum allowed is 100.")
                    midterm = 100

                if midterm < 0:
                    st.warning("Minimum allowed is 0.")
                    midterm = 0.0

                parental_edu = st.selectbox("Parental Education", ['High School', 'PhD', 'Bachelors', 'Masters'])
                internet = st.selectbox("Internet", ["Yes", "No"])
                activities = st.selectbox("Extracurricular_Activities", ["Yes", "No"])
            
            submitted = st.form_submit_button("Create New Student and Predict Final Exam Score",type="primary" ,use_container_width=True)
            
            if submitted:
                if not student_id:
                    st.error("❌ **Student ID required!**")
                else:
                    # ✅ CHECK IF ID EXISTS
                    existing_ids = df["StudentID"].tolist() if not df.empty else []
                    if student_id in existing_ids:
                        st.error(f"❌ **{student_id} already exists!** Choose different ID.")
                    else:
                        data = {
                            "StudentID": student_id, "Gender": gender,
                            "Study_Hours_per_Week": study_hours, "Attendance_Rate": attendance,
                            "Midterm_Exam_Scores": midterm, "Parental_Education_Level": parental_edu,
                            "Internet_Access_at_Home": internet, "Extracurricular_Activities": activities
                        }
                        with st.spinner("Predicting..."):
                            prediction = create_student(data)
                        if prediction:
                            #st.success(f"✅ **{student_id}** created! **{prediction:.1f}** 🎯")
                            st.toast(f"✅ **{student_id}** created! Predicted Final Exam Score : **{prediction:.1f}** ", icon="🎉")
                            st.balloons()
                            time.sleep(4)
                            st.rerun()
                        else:
                            st.error("❌ Prediction failed")

        
    with tab3:
        st.subheader("✏️ Update Student")
        if df.empty:
            st.warning("No students")
        else:
            student_id = st.selectbox("Select", df["StudentID"].tolist())
            if student_id:
                student = df[df["StudentID"] == student_id].iloc[0]
                
                with st.form("update_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        gender = st.selectbox("Gender", ["Male", "Female"], 
                                            index=0 if student["Gender"] == "Male" else 1)
                        study_hours = st.number_input("Study Hours", value=float(student["Study_Hours_per_Week"]),min_value=0.0,max_value=168.0,step=1.0)
                        if study_hours > 168:
                            st.warning("Maximum allowed is 168.")
                            study_hours = 168.0

                        if study_hours < 0:
                            st.warning("Minimum allowed is 0.")
                            study_hours = 0.0
                            
                        attendance = st.number_input("Attendance %", value=float(student["Attendance_Rate"]),min_value=0.0,max_value=100.0,step=1.0)
                        if attendance > 100:
                            st.warning("Maximum allowed is 100.")
                            attendance = 100.0

                        if attendance < 0:
                            st.warning("Minimum allowed is 0.")
                            attendance = 0.0

                    with col2:
                        midterm = st.number_input("Midterm", value=float(student["Midterm_Exam_Scores"]),min_value=0.0,max_value=100.0,step=1.0)
                        if midterm > 100:
                            st.warning("Maximum allowed is 100.")
                            midterm = 100.0

                        if midterm < 0:
                            st.warning("Minimum allowed is 0.")
                            midterm = 0.0
                        parental_edu = st.selectbox("Education", ['High School', 'PhD', 'Bachelors', 'Masters'], 
                                                  index=['High School', 'PhD', 'Bachelors', 'Masters'].index(student["Parental_Education_Level"]))
                        internet = st.selectbox("Internet", ["Yes", "No"], 
                                              index=0 if student["Internet_Access_at_Home"] == "Yes" else 1)
                        activities = st.selectbox("Extracurricular_Activities", ["Yes","No"], 
                                                index=["Yes","No"].index(student["Extracurricular_Activities"]))
                    
                    if st.form_submit_button("✏️ Update", type="primary"):
                        data = {
                            "StudentID": student_id, "Gender": gender,
                            "Study_Hours_per_Week": study_hours, "Attendance_Rate": attendance,
                            "Midterm_Exam_Scores": midterm, "Parental_Education_Level": parental_edu,
                            "Internet_Access_at_Home": internet, "Extracurricular_Activities": activities
                        }
                        with st.spinner("Updating..."):
                            prediction = update_student(student_id, data)
                        if prediction:
                            #st.success(f"✅ **{student_id}** updated! **{prediction:.1f}**")
                            st.toast(f"✅ **{student_id}** updated! Predicted Final Exam Score : **{prediction:.1f}** ", icon="🎉")
                            time.sleep(4)
                            st.rerun()
                        else:
                            st.error("❌ Update failed")
    
    with tab4:
        st.subheader("❌ Delete Student")
        if df.empty:
            st.warning("No students")
        else:
            student_id = st.selectbox("Delete", df["StudentID"].tolist())
            if student_id:
                student = df[df["StudentID"] == student_id].iloc[0]
                col1, col2 = st.columns([3,1])
                with col1:
                    st.info(f"**{student_id}** - {student['Predicted_Final_Score']:.1f} pts")
                with col2:
                    if st.button("❌ Delete", type="primary"):
                        delete_student(student_id)
                        #st.success(f"✅ Deleted **{student_id}**")
                        st.toast(f"✅ Deleted **{student_id}** ", icon="🎉")
                        time.sleep(4)
                        st.rerun()

if __name__ == "__main__":
    main()
