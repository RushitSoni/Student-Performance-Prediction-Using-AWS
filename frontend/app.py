import streamlit as st
import boto3
import pandas as pd
from decimal import Decimal
import json

# Page config
st.set_page_config(page_title="Student Performance CRUD", layout="wide")

# AWS Clients (same as your Lambda)
@st.cache_resource
def get_aws_clients():
    dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
    table = dynamodb.Table("StudentPerformancePredictions")
    runtime = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")
    return table, runtime

table, runtime = get_aws_clients()
sagemaker_endpoint = "student-performance-model-6-endpoint"

# ----------------------
# Helper Functions (same as Lambda)
# ----------------------
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

# ----------------------
# Get SageMaker Prediction
# ----------------------
@st.cache_data(ttl=60)
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

# ----------------------
# CRUD Operations
# ----------------------
@st.cache_data(ttl=300)
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

# ----------------------
# Streamlit UI
# ----------------------
def main():
    st.title("🎓 Student Performance CRUD")
    st.markdown("**Full CRUD operations with SageMaker predictions**")
    
    # Sidebar for operations
    st.sidebar.title("Operations")
    operation = st.sidebar.selectbox("Choose operation:", ["View All", "Create", "Update", "Delete"])
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 View All", "➕ Create", "✏️ Update", "🗑️ Delete"])
    
    with tab1:
        st.subheader("All Student Records")
        try:
            df = read_all()
            if df.empty:
                st.warning("No data found.")
            else:
                st.success(f"Loaded {len(df)} records")
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "Predicted_Final_Score": st.column_config.NumberColumn("Predicted Score", format="%.2f"),
                        "Attendance_Rate": st.column_config.NumberColumn("Attendance %", format="%.1f"),
                        "Midterm_Exam_Scores": st.column_config.NumberColumn("Midterm", format="%.0f"),
                        "Study_Hours_per_Week": st.column_config.NumberColumn("Study Hours", format="%.0f")
                    }
                )
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Total Students", len(df))
                with col2: st.metric("Avg Predicted", f"{df['Predicted_Final_Score'].mean():.1f}")
                with col3: st.metric("Avg Attendance", f"{df['Attendance_Rate'].mean():.1f}%")
                with col4: st.metric("High Performers", len(df[df["Predicted_Final_Score"] >= 60]))
        except Exception as e:
            st.error(f"Read error: {str(e)}")
    
    with tab2:
        st.subheader("Create New Student")
        with st.form("create_form"):
            col1, col2 = st.columns(2)
            with col1:
                student_id = st.text_input("StudentID *", key="create_id")
                gender = st.selectbox("Gender", ["Male", "Female"])
                study_hours = st.number_input("Study Hours/Week", min_value=0, max_value=168, value=10)
                attendance = st.number_input("Attendance Rate %", min_value=0, max_value=100, value=80)
            with col2:
                midterm = st.number_input("Midterm Score", min_value=0, max_value=100, value=70)
                parental_edu = st.selectbox("Parental Education", ["High School", "Bachelor", "Master", "PhD"])
                internet = st.selectbox("Internet Access", ["Yes", "No"])
                activities = st.selectbox("Activities", ["Sports", "Music", "None", "Debate"])
            
            submitted = st.form_submit_button("Create Student")
            if submitted and student_id:
                data = {
                    "StudentID": student_id,
                    "Gender": gender,
                    "Study_Hours_per_Week": study_hours,
                    "Attendance_Rate": attendance,
                    "Midterm_Exam_Scores": midterm,
                    "Parental_Education_Level": parental_edu,
                    "Internet_Access_at_Home": internet,
                    "Extracurricular_Activities": activities
                }
                with st.spinner("Creating + Predicting..."):
                    prediction = create_student(data)
                if prediction:
                    st.success(f"Student {student_id} created! Predicted Score: {prediction:.2f}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to create student")
            elif submitted:
                st.error("StudentID is required")
    
    with tab3:
        st.subheader("Update Student")
        try:
            df = read_all()
            student_id = st.selectbox("Select Student", df["StudentID"].tolist() if not df.empty else [])
            
            if student_id and not df.empty:
                student_data = df[df["StudentID"] == student_id].iloc[0].to_dict()
                
                with st.form("update_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        gender = st.selectbox("Gender", ["Male", "Female"], index=0 if student_data["Gender"] == "Male" else 1, key="up_gender")
                        study_hours = st.number_input("Study Hours", value=float(student_data["Study_Hours_per_Week"]), key="up_study")
                        attendance = st.number_input("Attendance %", value=float(student_data["Attendance_Rate"]), key="up_att")
                    with col2:
                        midterm = st.number_input("Midterm Score", value=float(student_data["Midterm_Exam_Scores"]), key="up_midterm")
                        parental_edu = st.selectbox("Parental Education", ["High School", "Bachelor", "Master", "PhD"], 
                                                  index=["High School", "Bachelor", "Master", "PhD"].index(student_data["Parental_Education_Level"]), key="up_edu")
                        internet = st.selectbox("Internet", ["Yes", "No"], index=0 if student_data["Internet_Access_at_Home"] == "Yes" else 1, key="up_int")
                        activities = st.selectbox("Activities", ["Sports", "Music", "None", "Debate"], 
                                                index=["Sports", "Music", "None", "Debate"].index(student_data["Extracurricular_Activities"]), key="up_act")
                    
                    submitted = st.form_submit_button("Update Student")
                    if submitted:
                        data = {
                            "StudentID": student_id,
                            "Gender": gender,
                            "Study_Hours_per_Week": study_hours,
                            "Attendance_Rate": attendance,
                            "Midterm_Exam_Scores": midterm,
                            "Parental_Education_Level": parental_edu,
                            "Internet_Access_at_Home": internet,
                            "Extracurricular_Activities": activities
                        }
                        with st.spinner("Updating + Re-predicting..."):
                            prediction = update_student(student_id, data)
                        if prediction:
                            st.success(f"Student {student_id} updated! New Prediction: {prediction:.2f}")
                            st.rerun()
                        else:
                            st.error("Update failed")
        except Exception as e:
            st.error(f"Update error: {str(e)}")
    
    with tab4:
        st.subheader("Delete Student")
        try:
            df = read_all()
            student_id = st.selectbox("Select Student to Delete", df["StudentID"].tolist() if not df.empty else [])
            
            col1, col2 = st.columns([3,1])
            with col1:
                if student_id and not df.empty:
                    student = df[df["StudentID"] == student_id].iloc[0]
                    st.info(f"**{student_id}** - Predicted: {student['Predicted_Final_Score']:.1f}, Attendance: {student['Attendance_Rate']}%")
            with col2:
                if st.button("🗑️ Delete", type="primary", disabled=not student_id):
                    delete_student(student_id)
                    st.success(f"Deleted {student_id}")
                    st.rerun()
        except Exception as e:
            st.error(f"Delete error: {str(e)}")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("**Uses same logic as your Lambda** ✅\n- SageMaker predictions\n- Decimal handling\n- ap-southeast-1 region")

if __name__ == "__main__":
    main()
