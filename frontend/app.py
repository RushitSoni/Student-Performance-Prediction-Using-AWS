import streamlit as st
import pandas as pd
import requests
import json
from typing import Dict, Any

# Streamlit app title
st.title("Student Performance CRUD Operations")

# Lambda endpoint URL - Move widget OUTSIDE cache (fixes CachedWidgetWarning)
lambda_url = st.text_input("Lambda Endpoint URL", value="https://your-lambda-endpoint.execute-api.region.amazonaws.com/prod", key="lambda_url")

# Define columns from student_performance.csv schema [file:1]
COLUMNS = [
    'StudentID', 'Gender', 'StudyHoursperWeek', 'AttendanceRate', 
    'MidtermExamScores', 'ParentalEducationLevel', 'InternetAccessatHome', 
    'ExtracurricularActivities', 'FinalExamScore', 'PassFail'
]

# Categorical columns for dropdowns
CATEGORICAL_COLS = {
    'Gender': ['Male', 'Female'],
    'ParentalEducationLevel': ['High School', 'Bachelors', 'Masters', 'PhD'],
    'InternetAccessatHome': ['Yes', 'No'],
    'ExtracurricularActivities': ['Yes', 'No'],
    'PassFail': ['Pass', 'Fail']
}

NUMERIC_COLS = ['StudyHoursperWeek', 'AttendanceRate', 'MidtermExamScores', 'FinalExamScore']

# Lambda API calls - FIXED: No widgets inside cached function
@st.cache_data
def call_lambda(_lambda_url: str, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
    if not _lambda_url or _lambda_url == "https://your-lambda-endpoint.execute-api.region.amazonaws.com/prod":
        return {'error': 'Please configure your Lambda endpoint URL'}
    
    payload = {"operation": operation, "data": data}
    try:
        response = requests.post(_lambda_url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lambda call failed: {str(e)}")
        return {'error': str(e)}

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

# Load data button
if st.button("🔄 Load Data from Lambda"):
    with st.spinner("Loading data..."):
        result = call_lambda(lambda_url, "READ", {})
        if 'error' not in result:
            if result.get('data'):
                st.session_state.data = pd.DataFrame(result['data'])
                st.success(f"Loaded {len(st.session_state.data)} records!")
            else:
                st.warning("No data returned from Lambda")
        else:
            st.error(result['error'])

# Display data table
st.subheader("📊 Student Data")
st.dataframe(st.session_state.data, use_container_width=True)

# CRUD Operations Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Create", "🔍 Read", "✏️ Update", "🗑️ Delete"])

with tab1:  # CREATE
    st.subheader("Create New Student")
    with st.form("create_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            student_id = st.text_input("StudentID", help="Unique student ID (e.g., S001)")
            gender = st.selectbox("Gender", CATEGORICAL_COLS['Gender'])
        with col2:
            study_hours = st.number_input("Study Hours/Week", min_value=0.0, max_value=168.0, step=1.0, format="%.1f")
            attendance = st.slider("Attendance Rate (%)", 0.0, 100.0, 80.0, 0.1)
        
        col3, col4 = st.columns(2)
        with col3:
            midterm = st.number_input("Midterm Score", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
            parental_edu = st.selectbox("Parental Education", CATEGORICAL_COLS['ParentalEducationLevel'])
        with col4:
            internet = st.selectbox("Internet Access", CATEGORICAL_COLS['InternetAccessatHome'])
            extracurricular = st.selectbox("Extracurricular", CATEGORICAL_COLS['ExtracurricularActivities'])
        
        col5, col6 = st.columns(2)
        with col5:
            final_score = st.number_input("Final Exam Score", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        with col6:
            pass_fail = st.selectbox("Pass/Fail", CATEGORICAL_COLS['PassFail'])
        
        submitted = st.form_submit_button("✅ Create Student", use_container_width=True)
        if submitted and student_id:
            new_student = {
                'StudentID': student_id, 'Gender': gender, 'StudyHoursperWeek': float(study_hours),
                'AttendanceRate': float(attendance), 'MidtermExamScores': float(midterm),
                'ParentalEducationLevel': parental_edu, 'InternetAccessatHome': internet,
                'ExtracurricularActivities': extracurricular, 'FinalExamScore': float(final_score),
                'PassFail': pass_fail
            }
            with st.spinner("Creating student..."):
                result = call_lambda(lambda_url, "CREATE", new_student)
                if 'error' not in result and result.get('success'):
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_student])], ignore_index=True)
                    st.success("🎉 Student created successfully!")
                    st.rerun()
                else:
                    st.error(result.get('error', result.get('message', 'Create failed')))

with tab2:  # READ
    st.subheader("Search Students")
    col1, col2 = st.columns(2)
    with col1:
        search_id = st.text_input("Search by StudentID", placeholder="e.g., S147")
    with col2:
        search_gender = st.selectbox("Filter by Gender", ["All"] + CATEGORICAL_COLS['Gender'])
    
    if st.button("🔍 Search", use_container_width=True):
        search_data = {}
        if search_id:
            search_data['StudentID'] = search_id
        if search_gender != "All":
            search_data['Gender'] = search_gender
        
        with st.spinner("Searching..."):
            result = call_lambda(lambda_url, "READ", search_data)
            if 'error' not in result and result.get('data'):
                st.dataframe(pd.DataFrame(result['data']), use_container_width=True)
            else:
                st.warning("No students found matching criteria")

with tab3:  # UPDATE
    st.subheader("Update Student")
    update_id = st.text_input("StudentID to Update", placeholder="e.g., S147")
    
    if update_id and not st.session_state.data.empty:
        student_data = st.session_state.data[st.session_state.data['StudentID'] == update_id]
        if not student_data.empty:
            row = student_data.iloc[0]
            st.info(f"Editing: {row['StudentID']} ({row['Gender']})")
            
            with st.form("update_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    gender = st.selectbox("Gender", CATEGORICAL_COLS['Gender'], 
                                        index=CATEGORICAL_COLS['Gender'].index(row['Gender']))
                    study_hours = st.number_input("Study Hours/Week", value=float(row['StudyHoursperWeek']), step=1.0)
                with col2:
                    attendance = st.number_input("Attendance Rate (%)", value=float(row['AttendanceRate']), step=0.1)
                    midterm = st.number_input("Midterm Score", value=float(row['MidtermExamScores']), step=0.1)
                
                col3, col4 = st.columns(2)
                with col3:
                    parental_edu = st.selectbox("Parental Education", CATEGORICAL_COLS['ParentalEducationLevel'], 
                                              index=list(CATEGORICAL_COLS['ParentalEducationLevel']).index(row['ParentalEducationLevel']))
                    final_score = st.number_input("Final Score", value=float(row['FinalExamScore']), step=0.1)
                with col4:
                    internet = st.selectbox("Internet Access", CATEGORICAL_COLS['InternetAccessatHome'], 
                                          index=CATEGORICAL_COLS['InternetAccessatHome'].index(row['InternetAccessatHome']))
                    extracurricular = st.selectbox("Extracurricular", CATEGORICAL_COLS['ExtracurricularActivities'], 
                                                 index=CATEGORICAL_COLS['ExtracurricularActivities'].index(row['ExtracurricularActivities']))
                    pass_fail = st.selectbox("Pass/Fail", CATEGORICAL_COLS['PassFail'], 
                                           index=CATEGORICAL_COLS['PassFail'].index(row['PassFail']))
                
                submitted = st.form_submit_button("💾 Update Student", use_container_width=True)
                if submitted:
                    updated_student = {
                        'StudentID': update_id, 'Gender': gender, 'StudyHoursperWeek': float(study_hours),
                        'AttendanceRate': float(attendance), 'MidtermExamScores': float(midterm),
                        'ParentalEducationLevel': parental_edu, 'InternetAccessatHome': internet,
                        'ExtracurricularActivities': extracurricular, 'FinalExamScore': float(final_score),
                        'PassFail': pass_fail
                    }
                    with st.spinner("Updating..."):
                        result = call_lambda(lambda_url, "UPDATE", updated_student)
                        if 'error' not in result and result.get('success'):
                            # Update local dataframe
                            for idx, col in enumerate(COLUMNS):
                                st.session_state.data.loc[st.session_state.data['StudentID'] == update_id, col] = updated_student[col]
                            st.success("✅ Student updated successfully!")
                            st.rerun()
                        else:
                            st.error(result.get('error', 'Update failed'))
        else:
            st.warning("❌ Student not found. Load data first.")

with tab4:  # DELETE
    st.subheader("Delete Student")
    col1, col2 = st.columns([3,1])
    with col1:
        delete_id = st.text_input("StudentID to Delete", placeholder="e.g., S147")
    with col2:
        if st.button("🗑️ Delete", type="secondary"):
            pass
    
    if delete_id:
        col1, col2, col3 = st.columns([1,3,1])
        with col2:
            if st.button("⚠️ CONFIRM DELETE", type="primary", use_container_width=True, 
                        help="This will permanently delete the student record"):
                with st.spinner("Deleting..."):
                    result = call_lambda(lambda_url, "DELETE", {'StudentID': delete_id})
                    if 'error' not in result and result.get('success'):
                        st.session_state.data = st.session_state.data[st.session_state.data['StudentID'] != delete_id]
                        st.success("🗑️ Student deleted successfully!")
                        st.rerun()
                    else:
                        st.error(result.get('error', 'Delete failed'))

# Lambda Handler Template
with st.expander("🔧 Lambda Handler Template (Copy-Paste Ready)"):
    st.code("""
import json
import boto3
import pandas as pd
from io import StringIO

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('StudentPerformance')

def lambda_handler(event, context):
    operation = event['operation']
    data = event['data']
    
    try:
        if operation == 'CREATE':
            table.put_item(Item=data)
            return {'success': True, 'message': 'Student created'}
        elif operation == 'READ':
            if 'StudentID' in data:
                response = table.get_item(Key={'StudentID': data['StudentID']})
                return {'success': True, 'data': [response['Item']] if 'Item' in response else []}
            else:
                response = table.scan()
                return {'success': True, 'data': response['Items']}
        elif operation == 'UPDATE':
            table.update_item(
                Key={'StudentID': data['StudentID']},
                UpdateExpression='SET ' + ', '.join([f"{k} = :{k}" for k in data if k != 'StudentID']),
                ExpressionAttributeValues={f":{k}": v for k, v in data.items() if k != 'StudentID'}
            )
            return {'success': True, 'message': 'Student updated'}
        elif operation == 'DELETE':
            table.delete_item(Key={'StudentID': data['StudentID']})
            return {'success': True, 'message': 'Student deleted'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    """, language="python")

st.caption("✅ Fixed CachedWidgetWarning | Matches student_performance.csv schema [file:1] | Ready for AWS Lambda + DynamoDB")
