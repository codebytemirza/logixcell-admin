import streamlit as st
import random
import string
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import pandas as pd
import plotly.express as px

# MongoDB setup
@st.cache_resource
def init_connection():
    return MongoClient("mongodb+srv://abdullah:siteadmin@site.6orgr.mongodb.net/?retryWrites=true&w=majority&appName=site")

def generate_batch_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def format_datetime(dt):
    if isinstance(dt, str):
        return datetime.strptime(dt.split()[0], '%Y-%m-%d').date()
    return dt.date() if isinstance(dt, datetime) else dt

# Page configuration
st.set_page_config(page_title="Course Management", page_icon="📚", layout="wide")

# Enhanced CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #ffffff;
    }
    .main {
        padding: 1rem 2rem;
    }
    .stTabs {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .delete-button>button {
        background-color: #dc3545;
    }
    .delete-button>button:hover {
        background-color: #c82333;
    }
    div[data-testid="stExpander"] {
        background-color: #1e1e1e;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #343a40;
        border: 1px solid #495057;
        border-radius: 4px;
        padding: 0.5rem;
        color: #ffffff;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus, .stSelectbox>div>div>div:focus {
        border-color: #80bdff;
        box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize MongoDB connection
client = init_connection()
db = client.codecraft
courses_collection = db.courses

# Sidebar
with st.sidebar:
    st.image("https://logixcell.onrender.com/_next/image?url=%2Fimages%2Fbrand-icon.png&w=48&q=75", width=48)
    st.title("Course Management")

    page = st.radio("Navigation", ["Dashboard", "Course Management", "Batch Management"])

    with st.container():
        st.divider()
        total_courses = courses_collection.count_documents({})
        total_batches = sum(len(course.get('batches', [])) for course in courses_collection.find())
        active_batches = sum(
            sum(1 for batch in course.get('batches', [])
                if batch['status'] in ['upcoming', 'ongoing'])
            for course in courses_collection.find()
        )

        cols = st.columns(2)
        with cols[0]:
            st.metric("📚 Courses", total_courses)
            st.metric("📅 Batches", total_batches)
        with cols[1]:
            st.metric("🎯 Active", active_batches)

# Main content
if page == "Dashboard":
    st.title("📊 Dashboard Overview")

    courses = list(courses_collection.find())

    # Metrics cards
    cols = st.columns(4)
    metrics = [
        ("📚 Active Courses", sum(1 for c in courses if any(
            b['status'] in ['upcoming', 'ongoing'] for b in c.get('batches', [])))),
        ("👥 Total Enrollments", sum(
            sum(b.get('enrolledStudents', 0) for b in c.get('batches', []))
            for c in courses)),
        ("💺 Available Seats", sum(
            sum(b['seats'] - b.get('enrolledStudents', 0)
                for b in c.get('batches', [])
                if b['status'] in ['upcoming', 'ongoing'])
            for c in courses)),
        ("📑 Categories", len(set(c['level'] for c in courses)))
    ]

    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(f"""
                <div class="metric-card">
                    <h3>{label}</h3>
                    <h2>{value}</h2>
                </div>
            """, unsafe_allow_html=True)

    # Charts
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Enrollment Distribution")
        enroll_data = []
        for course in courses:
            for batch in course.get('batches', []):
                enroll_data.append({
                    'Course': course['title'],
                    'Enrolled': batch.get('enrolledStudents', 0),
                    'Available': batch['seats'] - batch.get('enrolledStudents', 0)
                })
        if enroll_data:
            df = pd.DataFrame(enroll_data)
            fig = px.bar(df, x='Course', y=['Enrolled', 'Available'],
                        title="Course Enrollment Status",
                        barmode='stack',
                        color_discrete_sequence=['#007bff', '#ffc107'])
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🔄 Batch Status Distribution")
        status_data = []
        for course in courses:
            for batch in course.get('batches', []):
                status_data.append(batch['status'].title())
        if status_data:
            status_counts = pd.Series(status_data).value_counts()
            fig = px.pie(values=status_counts.values,
                        names=status_counts.index,
                        title="Batch Status Distribution",
                        color_discrete_sequence=['#007bff', '#17a2b8', '#ffc107', '#dc3545'])
            st.plotly_chart(fig, use_container_width=True)

elif page == "Course Management":
    st.title("🎓 Course Management")

    tab1, tab2 = st.tabs(["📋 View/Edit Courses", "➕ Add New Course"])

    with tab1:
        courses = list(courses_collection.find())
        for course in courses:
            with st.expander(f"📚 {course['title']} - {course['level']}", expanded=False):
                cols = st.columns([2, 2, 1])

                with cols[0]:
                    new_title = st.text_input("Title", course['title'], key=f"title_{course['_id']}")
                    new_description = st.text_area("Description", course['description'], key=f"desc_{course['_id']}")
                    new_features = st.text_area("Features", "\n".join(course.get('features', [])), key=f"feat_{course['_id']}")

                with cols[1]:
                    new_duration = st.text_input("Duration", course['duration'], key=f"dur_{course['_id']}")
                    new_level = st.selectbox("Level",
                                           ["Beginner", "Intermediate", "Advanced"],
                                           ["Beginner", "Intermediate", "Advanced"].index(course['level']),
                                           key=f"level_{course['_id']}")
                    new_image_id = st.text_input("Image ID", str(course['imageId']), key=f"img_{course['_id']}")

                with cols[2]:
                    new_price = st.number_input("Price", value=float(course['price']), key=f"price_{course['_id']}")
                    st.write("Statistics")
                    st.metric("Total Batches", len(course.get('batches', [])))
                    st.metric("Active Batches",
                            sum(1 for b in course.get('batches', [])
                                if b['status'] in ['upcoming', 'ongoing']))

                cols = st.columns([3, 1, 1])
                with cols[1]:
                    if st.button("💾 Save Changes", key=f"save_{course['_id']}"):
                        courses_collection.update_one(
                            {"_id": course["_id"]},
                            {
                                "$set": {
                                    "title": new_title,
                                    "description": new_description,
                                    "price": new_price,
                                    "imageId": ObjectId(new_image_id),
                                    "duration": new_duration,
                                    "level": new_level,
                                    "features": [f for f in new_features.split("\n") if f.strip()],
                                    "updatedAt": datetime.now()
                                }
                            }
                        )
                        st.success("✅ Course updated!")
                        st.rerun()

                with cols[2]:
                    if st.button("🗑️ Delete", key=f"del_{course['_id']}", type="primary"):
                        if st.warning("⚠️ Are you sure?"):
                            courses_collection.delete_one({"_id": course["_id"]})
                            st.success("✅ Course deleted!")
                            st.rerun()

    with tab2:
        with st.form("add_course"):
            st.subheader("Add New Course")

            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Title*")
                description = st.text_area("Description*")
                features = st.text_area("Features (one per line)")

            with col2:
                price = st.number_input("Price*", min_value=0)
                duration = st.text_input("Duration* (e.g., '12 weeks')")
                level = st.selectbox("Level*", ["Beginner", "Intermediate", "Advanced"])
                image_id = st.text_input("Image ID*", value="000000000000000000000000")

            if st.form_submit_button("➕ Add Course"):
                if not all([title, description, price, duration, level]):
                    st.error("❌ Please fill all required fields!")
                else:
                    new_course = {
                        "title": title,
                        "description": description,
                        "price": price,
                        "imageId": ObjectId(image_id),
                        "duration": duration,
                        "level": level,
                        "features": [f for f in features.split("\n") if f.strip()],
                        "batches": [],
                        "createdAt": datetime.now(),
                        "updatedAt": datetime.now()
                    }
                    courses_collection.insert_one(new_course)
                    st.success("✅ Course added!")
                    st.rerun()

elif page == "Batch Management":
    st.title("📅 Batch Management")

    courses = list(courses_collection.find())
    course_titles = [c["title"] for c in courses]

    selected_course = st.selectbox("Select Course", course_titles)

    if selected_course:
        course = courses_collection.find_one({"title": selected_course})

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Current Batches")
            if course.get("batches"):
                for idx, batch in enumerate(course["batches"]):
                    with st.expander(f"🎓 Batch {batch['batchCode']} - {batch['status'].title()}", expanded=False):
                        cols = st.columns([2, 2, 1])

                        with cols[0]:
                            start = st.date_input("Start Date", format_datetime(batch['startDate']), key=f"start_{idx}")
                            seats = st.number_input("Total Seats", value=batch['seats'], min_value=1, key=f"seats_{idx}")

                        with cols[1]:
                            end = st.date_input("End Date", format_datetime(batch['endDate']), key=f"end_{idx}")
                            enrolled = st.number_input("Enrolled", value=batch.get('enrolledStudents', 0),
                                                     max_value=seats, key=f"enrolled_{idx}")

                        with cols[2]:
                            status = st.selectbox("Status",
                                                ["upcoming", "ongoing", "completed", "cancelled"],
                                                ["upcoming", "ongoing", "completed", "cancelled"].index(batch['status']),
                                                key=f"status_{idx}")
                            st.metric("Available", seats - enrolled)

                        cols = st.columns([3, 1, 1])
                        with cols[1]:
                            if st.button("💾 Update", key=f"update_{idx}"):
                                course["batches"][idx].update({
                                    "startDate": datetime.combine(start, datetime.min.time()),
                                    "endDate": datetime.combine(end, datetime.min.time()),
                                    "seats": seats,
                                    "enrolledStudents": enrolled,
                                    "status": status
                                })
                                courses_collection.update_one(
                                    {"_id": course["_id"]},
                                    {"$set": {"batches": course["batches"]}}
                                )
                                st.success("✅ Updated!")
                                st.rerun()

                        with cols[2]:
                            if st.button("🗑️ Delete", key=f"del_batch_{idx}", type="primary"):
                                course["batches"].pop(idx)
                                courses_collection.update_one(
                                    {"_id": course["_id"]},
                                    {"$set": {"batches": course["batches"]}}
                                )
                                st.success("✅ Deleted!")
                                st.rerun()

        with col2:
            with st.form("add_batch"):
                st.subheader("Add New Batch")
                start_date = st.date_input("Start Date*")
                end_date = st.date_input("End Date*")
                seats = st.number_input("Total Seats*", min_value=1, value=30)
                status = st.selectbox("Status*", ["upcoming", "ongoing", "completed", "cancelled"])
                batch_code = st.text_input("Batch Code*", value=generate_batch_code())

                if st.form_submit_button("➕ Add Batch"):
                    if end_date <= start_date:
                        st.error("❌ End date must be after start date!")
                    elif not batch_code:
                        st.error("❌ Batch code is required!")
                    else:
                        new_batch = {
                            "startDate": datetime.combine(start_date, datetime.min.time()),
                            "endDate": datetime.combine(end_date, datetime.min.time()),
                            "seats": seats,
                            "enrolledStudents": 0,
                            "status": status,
                            "batchCode": batch_code
                        }
                        courses_collection.update_one(
                            {"_id": course["_id"]},
                            {
                                "$push": {"batches": new_batch}
                            }
                        )
                        st.success("✅ Batch added!")
                        st.rerun()
