import streamlit as st
import pandas as pd
import plotly.express as px
import httpx
import os
import json
from datetime import datetime, timedelta
import sqlite3
from sqlmodel import Session, select, SQLModel, create_engine
from sqlalchemy import text, func
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://backend:8000")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../backend/sns_ai_saas.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

st.set_page_config(
    page_title="SNS AI SaaS Admin",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "jwt" not in st.session_state:
    st.session_state["jwt"] = None

with st.sidebar:
    st.title("SNS AI SaaS Admin")
    st.markdown("---")
    
    if st.session_state["jwt"] is None:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                try:
                    response = httpx.post(
                        f"{API_URL}/auth/login",
                        data={"username": username, "password": password}
                    )
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        st.session_state["jwt"] = token_data["access_token"]
                        st.experimental_rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
                except Exception as e:
                    st.error(f"Login error: {str(e)}")
    else:
        if st.button("Logout"):
            st.session_state["jwt"] = None
            st.experimental_rerun()
        
        st.success("Logged in successfully")
    
    st.markdown("---")
    
    menu = st.radio(
        "Navigation",
        ["Dashboard", "Clients", "Failed Jobs", "Usage Charts"]
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("Admin dashboard for SNS AI SaaS Platform")

def get_db_connection():
    """Get a direct database connection"""
    return Session(engine)

def format_datetime(dt):
    """Format datetime for display"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "N/A"

if menu == "Dashboard":
    st.title("Dashboard")
    
    try:
        with get_db_connection() as session:
            user_count = session.exec(text("SELECT COUNT(*) FROM user")).first()[0]
            
            client_count = session.exec(text("SELECT COUNT(*) FROM client")).first()[0]
            
            video_count = session.exec(text("SELECT COUNT(*) FROM video")).first()[0]
            processed_video_count = session.exec(text("SELECT COUNT(*) FROM video WHERE processed = 1")).first()[0]
            
            post_count = session.exec(text("SELECT COUNT(*) FROM post")).first()[0]
            posted_count = session.exec(text("SELECT COUNT(*) FROM post WHERE posted = 1")).first()[0]
            
            failed_job_count = session.exec(text("SELECT COUNT(*) FROM job_log WHERE status = 'failed'")).first()[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", user_count)
            st.metric("Total Clients", client_count)
        
        with col2:
            st.metric("Total Videos", video_count)
            st.metric("Processed Videos", f"{processed_video_count} ({processed_video_count/video_count*100:.1f}%)" if video_count > 0 else "0 (0.0%)")
        
        with col3:
            st.metric("Total Posts", post_count)
            st.metric("Posted", f"{posted_count} ({posted_count/post_count*100:.1f}%)" if post_count > 0 else "0 (0.0%)")
            st.metric("Failed Jobs", failed_job_count, delta=failed_job_count, delta_color="inverse")
        
        st.subheader("Recent Activity")
        
        with get_db_connection() as session:
            recent_logs = session.exec(text("""
                SELECT job_type, status, error_message, created_at 
                FROM job_log 
                ORDER BY created_at DESC 
                LIMIT 5
            """)).all()
            
            if recent_logs:
                log_data = []
                for log in recent_logs:
                    log_data.append({
                        "Job Type": log[0],
                        "Status": log[1],
                        "Error": log[2] if log[2] else "N/A",
                        "Created At": format_datetime(log[3])
                    })
                
                st.dataframe(pd.DataFrame(log_data), use_container_width=True)
            else:
                st.info("No recent activity found")
    
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")

elif menu == "Clients":
    st.title("Clients")
    
    client_tabs = st.tabs(["List Clients", "Add Client", "Edit Client", "Delete Client"])
    
    try:
        with get_db_connection() as session:
            users = session.exec(text("SELECT id, username FROM user ORDER BY username")).all()
            user_options = {user[0]: user[1] for user in users}
            
            if st.session_state["jwt"] is None:
                st.warning("Please login to view clients")
                clients = []
                client_data = []
            else:
                headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                response = httpx.get(f"{API_URL}/client/", headers=headers)
                if response.status_code != 200:
                    raise Exception(f"API error: {response.text}")
                
                clients_data = response.json()
                clients = []
                
                for client_item in clients_data:
                    user = session.exec(text(f"SELECT username FROM user WHERE id = {client_item['user_id']}")).first()
                    username = user[0] if user else "Unknown"
                    clients.append((
                        client_item["id"], 
                        client_item["name"], 
                        client_item.get("industry"), 
                        username,
                        client_item["created_at"]
                    ))
            
            if st.session_state["jwt"] is not None and clients_data:
                for client_data in clients_data:
                    user = session.exec(text(f"SELECT username FROM user WHERE id = {client_data['user_id']}")).first()
                    username = user[0] if user else "Unknown"
                    clients.append((
                        client_data["id"], 
                        client_data["name"], 
                        client_data.get("industry"), 
                        username,
                        client_data["created_at"]
                    ))
            
            client_data = []
            if clients:
                for client in clients:
                    client_data.append({
                        "ID": client[0],
                        "Name": client[1],
                        "Industry": client[2] if client[2] else "N/A",
                        "Owner": client[3],
                        "Created At": format_datetime(client[4])
                    })
            
            with client_tabs[0]:
                if client_data:
                    st.dataframe(pd.DataFrame(client_data), use_container_width=True)
                    
                    st.subheader("Client Details")
                    selected_client_id = st.selectbox("Select Client", [c["ID"] for c in client_data], key="list_client_select")
                    
                    if selected_client_id:
                        headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                        response = httpx.get(
                            f"{API_URL}/client/{selected_client_id}", 
                            headers=headers
                        )
                        if response.status_code != 200:
                            raise Exception(f"API error: {response.text}")
                            
                        client_data = response.json()
                        user = session.exec(text(f"SELECT username FROM user WHERE id = {client_data['user_id']}")).first()
                        username = user[0] if user else "Unknown"
                        
                        client = (
                            client_data["id"],
                            client_data["name"],
                            client_data.get("industry"),
                            json.dumps(client_data.get("target_audience", {})),
                            client_data["created_at"],
                            username
                        )
                        
                        if client:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Name:** {client[1]}")
                                st.write(f"**Industry:** {client[2] if client[2] else 'N/A'}")
                                st.write(f"**Owner:** {client[5]}")
                                st.write(f"**Created At:** {format_datetime(client[4])}")
                            
                            with col2:
                                try:
                                    target_audience = json.loads(client[3]) if client[3] else {}
                                    st.write("**Target Audience:**")
                                    st.json(target_audience)
                                except:
                                    st.write("**Target Audience:** Invalid format")
                            
                            st.subheader("Client Statistics")
                            
                            videos = session.exec(text(f"""
                                SELECT COUNT(*), SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END)
                                FROM video
                                WHERE client_id = {selected_client_id}
                            """)).first()
                            
                            posts = session.exec(text(f"""
                                SELECT COUNT(*), SUM(CASE WHEN posted = 1 THEN 1 ELSE 0 END)
                                FROM post
                                WHERE client_id = {selected_client_id}
                            """)).first()
                            
                            failed_jobs = session.exec(text(f"""
                                SELECT COUNT(*)
                                FROM job_log
                                WHERE client_id = {selected_client_id} AND status = 'failed'
                            """)).first()
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Videos", videos[0])
                                st.metric("Processed Videos", f"{videos[1]} ({videos[1]/videos[0]*100:.1f}%)" if videos[0] > 0 else "0 (0.0%)")
                            
                            with col2:
                                st.metric("Total Posts", posts[0])
                                st.metric("Posted", f"{posts[1]} ({posts[1]/posts[0]*100:.1f}%)" if posts[0] > 0 else "0 (0.0%)")
                            
                            with col3:
                                st.metric("Failed Jobs", failed_jobs[0])
                else:
                    st.info("No clients found")
            
            with client_tabs[1]:
                st.subheader("Add New Client")
                
                with st.form("add_client_form"):
                    name = st.text_input("Client Name", key="add_name")
                    industry = st.text_input("Industry", key="add_industry")
                    
                    st.write("Target Audience (JSON format)")
                    target_audience_json = st.text_area(
                        "Enter target audience as JSON", 
                        value='{"age": "25-34", "interests": ["technology", "social media"]}',
                        key="add_target_audience"
                    )
                    
                    user_id = st.selectbox("Owner", options=list(user_options.keys()), format_func=lambda x: user_options[x], key="add_user")
                    
                    submit_button = st.form_submit_button("Add Client")
                    
                    if submit_button:
                        if not name:
                            st.error("Client name is required")
                        else:
                            try:
                                target_audience = json.loads(target_audience_json) if target_audience_json else {}
                                
                                headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                                response = httpx.post(
                                    f"{API_URL}/client/",
                                    json={
                                        "name": name,
                                        "industry": industry,
                                        "target_audience": target_audience,
                                    },
                                    headers=headers
                                )
                                
                                if response.status_code != 200:
                                    raise Exception(f"API error: {response.text}")
                                
                                st.success(f"Client '{name}' added successfully!")
                                st.experimental_rerun()
                            except json.JSONDecodeError:
                                st.error("Invalid JSON format for target audience")
                            except Exception as e:
                                st.error(f"Error adding client: {str(e)}")
            
            with client_tabs[2]:
                st.subheader("Edit Client")
                
                if client_data:
                    edit_client_id = st.selectbox("Select Client to Edit", 
                                                [c["ID"] for c in client_data], 
                                                format_func=lambda x: next((c["Name"] for c in client_data if c["ID"] == x), ""),
                                                key="edit_client_select")
                    
                    if edit_client_id:
                        headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                        response = httpx.get(
                            f"{API_URL}/client/{edit_client_id}", 
                            headers=headers
                        )
                        if response.status_code != 200:
                            raise Exception(f"API error: {response.text}")
                            
                        client_data = response.json()
                        
                        client = (
                            client_data["id"],
                            client_data["name"],
                            client_data.get("industry"),
                            json.dumps(client_data.get("target_audience", {})),
                            client_data["user_id"]
                        )
                        
                        if client:
                            with st.form("edit_client_form"):
                                edit_name = st.text_input("Client Name", value=client[1], key="edit_name")
                                edit_industry = st.text_input("Industry", value=client[2] if client[2] else "", key="edit_industry")
                                
                                try:
                                    current_target_audience = json.loads(client[3]) if client[3] else {}
                                except:
                                    current_target_audience = {}
                                
                                edit_target_audience_json = st.text_area(
                                    "Target Audience (JSON format)", 
                                    value=json.dumps(current_target_audience, indent=2),
                                    key="edit_target_audience"
                                )
                                
                                edit_user_id = st.selectbox("Owner", 
                                                        options=list(user_options.keys()), 
                                                        index=list(user_options.keys()).index(client[4]) if client[4] in user_options else 0,
                                                        format_func=lambda x: user_options[x],
                                                        key="edit_user")
                                
                                update_button = st.form_submit_button("Update Client")
                                
                                if update_button:
                                    if not edit_name:
                                        st.error("Client name is required")
                                    else:
                                        try:
                                            target_audience = json.loads(edit_target_audience_json) if edit_target_audience_json else {}
                                            
                                            headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                                            response = httpx.put(
                                                f"{API_URL}/client/{edit_client_id}",
                                                json={
                                                    "name": edit_name,
                                                    "industry": edit_industry,
                                                    "target_audience": target_audience,
                                                },
                                                headers=headers
                                            )
                                            
                                            if response.status_code != 200:
                                                raise Exception(f"API error: {response.text}")
                                            
                                            st.success(f"Client '{edit_name}' updated successfully!")
                                            st.experimental_rerun()
                                        except json.JSONDecodeError:
                                            st.error("Invalid JSON format for target audience")
                                        except Exception as e:
                                            st.error(f"Error updating client: {str(e)}")
                else:
                    st.info("No clients found to edit")
            
            with client_tabs[3]:
                st.subheader("Delete Client")
                
                if client_data:
                    delete_client_id = st.selectbox("Select Client to Delete", 
                                                [c["ID"] for c in client_data], 
                                                format_func=lambda x: next((c["Name"] for c in client_data if c["ID"] == x), ""),
                                                key="delete_client_select")
                    
                    if delete_client_id:
                        client_name = next((c["Name"] for c in client_data if c["ID"] == delete_client_id), "")
                        
                        st.warning(f"Are you sure you want to delete client '{client_name}'? This action cannot be undone.")
                        
                        videos_count = session.exec(text(f"SELECT COUNT(*) FROM video WHERE client_id = {delete_client_id}")).first()[0]
                        posts_count = session.exec(text(f"SELECT COUNT(*) FROM post WHERE client_id = {delete_client_id}")).first()[0]
                        scripts_count = session.exec(text(f"SELECT COUNT(*) FROM script WHERE client_id = {delete_client_id}")).first()[0]
                        
                        if videos_count > 0 or posts_count > 0 or scripts_count > 0:
                            st.error(f"This client has related records: {videos_count} videos, {posts_count} posts, {scripts_count} scripts. Delete these records first.")
                        else:
                            if st.button("Confirm Delete", key="confirm_delete"):
                                try:
                                    headers = {"Authorization": f"Bearer {st.session_state['jwt']}"}
                                    response = httpx.delete(
                                        f"{API_URL}/client/{delete_client_id}",
                                        headers=headers
                                    )
                                    
                                    if response.status_code != 204:
                                        raise Exception(f"API error: {response.text}")
                                    
                                    st.success(f"Client '{client_name}' deleted successfully!")
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"Error deleting client: {str(e)}")
                else:
                    st.info("No clients found to delete")
    
    except Exception as e:
        st.error(f"Error loading client data: {str(e)}")

elif menu == "Failed Jobs":
    st.title("Failed Jobs")
    
    if st.session_state["jwt"] is None:
        st.warning("Please login to view failed jobs")
    else:
        try:
            with get_db_connection() as session:
                failed_jobs = session.exec(text("""
                    SELECT j.id, j.job_type, j.error_message, j.created_at, 
                           c.name as client_name, u.username as user_name
                    FROM job_log j
                    LEFT JOIN client c ON j.client_id = c.id
                    LEFT JOIN user u ON j.user_id = u.id
                    WHERE j.status = 'failed'
                    ORDER BY j.created_at DESC
                """)).all()
                
                if failed_jobs:
                    job_data = []
                    for job in failed_jobs:
                        job_data.append({
                            "ID": job[0],
                            "Job Type": job[1],
                            "Error Message": job[2],
                            "Created At": format_datetime(job[3]),
                            "Client": job[4] if job[4] else "N/A",
                            "User": job[5] if job[5] else "N/A"
                        })
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        job_types = ["All"] + list(set(j["Job Type"] for j in job_data))
                        selected_job_type = st.selectbox("Filter by Job Type", job_types)
                    
                    with col2:
                        clients = ["All"] + list(set(j["Client"] for j in job_data if j["Client"] != "N/A"))
                        selected_client = st.selectbox("Filter by Client", clients)
                    
                    filtered_data = job_data
                    if selected_job_type != "All":
                        filtered_data = [j for j in filtered_data if j["Job Type"] == selected_job_type]
                    
                    if selected_client != "All":
                        filtered_data = [j for j in filtered_data if j["Client"] == selected_client]
                    
                    st.dataframe(pd.DataFrame(filtered_data), use_container_width=True)
                    
                    if filtered_data:
                        st.subheader("Job Details")
                        selected_job_id = st.selectbox("Select Job", [j["ID"] for j in filtered_data])
                        
                        if selected_job_id:
                            selected_job = next((j for j in filtered_data if j["ID"] == selected_job_id), None)
                            
                            if selected_job:
                                st.write(f"**Job Type:** {selected_job['Job Type']}")
                                st.write(f"**Client:** {selected_job['Client']}")
                                st.write(f"**User:** {selected_job['User']}")
                                st.write(f"**Created At:** {selected_job['Created At']}")
                                
                                st.subheader("Error Message")
                                st.code(selected_job["Error Message"], language="text")
                else:
                    st.success("No failed jobs found")
        except Exception as e:
            st.error(f"Error loading failed jobs data: {str(e)}")

elif menu == "Usage Charts":
    st.title("Usage Charts")
    
    if st.session_state["jwt"] is None:
        st.warning("Please login to view usage charts")
    else:
        try:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
            
            with col2:
                end_date = st.date_input("End Date", datetime.now())
            
            if start_date > end_date:
                st.error("Start date must be before end date")
            else:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                with get_db_connection() as session:
                    videos_by_day = session.exec(text(f"""
                        SELECT date(created_at) as day, COUNT(*) as count
                        FROM video
                        WHERE created_at BETWEEN '{start_datetime.isoformat()}' AND '{end_datetime.isoformat()}'
                        GROUP BY day
                        ORDER BY day
                    """)).all()
                    
                    posts_by_day = session.exec(text(f"""
                        SELECT date(created_at) as day, COUNT(*) as count
                        FROM post
                        WHERE created_at BETWEEN '{start_datetime.isoformat()}' AND '{end_datetime.isoformat()}'
                        GROUP BY day
                        ORDER BY day
                    """)).all()
                    
                    jobs_by_day = session.exec(text(f"""
                        SELECT date(created_at) as day, status, COUNT(*) as count
                        FROM job_log
                        WHERE created_at BETWEEN '{start_datetime.isoformat()}' AND '{end_datetime.isoformat()}'
                        GROUP BY day, status
                        ORDER BY day
                    """)).all()
                    
                    if videos_by_day:
                        videos_df = pd.DataFrame(videos_by_day, columns=["day", "count"])
                        videos_df["day"] = pd.to_datetime(videos_df["day"])
                        
                        st.subheader("Videos by Day")
                        fig = px.line(videos_df, x="day", y="count", title="Videos Created by Day")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No video data available for the selected period")
                    
                    if posts_by_day:
                        posts_df = pd.DataFrame(posts_by_day, columns=["day", "count"])
                        posts_df["day"] = pd.to_datetime(posts_df["day"])
                        
                        st.subheader("Posts by Day")
                        fig = px.line(posts_df, x="day", y="count", title="Posts Created by Day")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No post data available for the selected period")
                    
                    if jobs_by_day:
                        jobs_df = pd.DataFrame(jobs_by_day, columns=["day", "status", "count"])
                        jobs_df["day"] = pd.to_datetime(jobs_df["day"])
                        
                        st.subheader("Jobs by Day and Status")
                        fig = px.line(jobs_df, x="day", y="count", color="status", title="Jobs by Day and Status")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No job data available for the selected period")
                    
                    job_types = session.exec(text(f"""
                        SELECT job_type, COUNT(*) as count
                        FROM job_log
                        WHERE created_at BETWEEN '{start_datetime.isoformat()}' AND '{end_datetime.isoformat()}'
                        GROUP BY job_type
                        ORDER BY count DESC
                    """)).all()
                    
                    if job_types:
                        job_types_df = pd.DataFrame(job_types, columns=["job_type", "count"])
                        
                        st.subheader("Job Types Distribution")
                        fig = px.pie(job_types_df, values="count", names="job_type", title="Job Types Distribution")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No job type data available for the selected period")
        except Exception as e:
            st.error(f"Error loading usage charts data: {str(e)}")
