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

with st.sidebar:
    st.title("SNS AI SaaS Admin")
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
            from sqlmodel import select
            from sqlalchemy import func
            from app.models import User, Client, Video, Post, JobLog
            
            user_count = session.exec(select(func.count(User.id))).first()
            
            client_count = session.exec(select(func.count(Client.id))).first()
            
            video_count = session.exec(select(func.count(Video.id))).first()
            processed_video_count = session.exec(select(func.count(Video.id)).where(Video.processed == True)).first()
            
            post_count = session.exec(select(func.count(Post.id))).first()
            posted_count = session.exec(select(func.count(Post.id)).where(Post.posted == True)).first()
            
            failed_job_count = session.exec(select(func.count(JobLog.id)).where(JobLog.status == "failed")).first()
        
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
            from app.models import JobLog
            
            recent_logs_query = select(
                JobLog.job_type, 
                JobLog.status, 
                JobLog.error_message, 
                JobLog.created_at
            ).order_by(JobLog.created_at.desc()).limit(5)
            
            recent_logs = session.exec(recent_logs_query).all()
            
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
    
    try:
        with get_db_connection() as session:
            from app.models import Client, User
            
            clients_query = select(
                Client.id, 
                Client.name, 
                Client.industry, 
                User.username, 
                Client.created_at
            ).join(User).order_by(Client.created_at.desc())
            
            clients = session.exec(clients_query).all()
            
            if clients:
                client_data = []
                for client in clients:
                    client_data.append({
                        "ID": client[0],
                        "Name": client[1],
                        "Industry": client[2] if client[2] else "N/A",
                        "Owner": client[3],
                        "Created At": format_datetime(client[4])
                    })
                
                st.dataframe(pd.DataFrame(client_data), use_container_width=True)
                
                st.subheader("Client Details")
                selected_client_id = st.selectbox("Select Client", [c["ID"] for c in client_data])
                
                if selected_client_id:
                    client_detail_query = select(
                        Client.id, 
                        Client.name, 
                        Client.industry, 
                        Client.target_audience, 
                        Client.created_at, 
                        User.username
                    ).join(User).where(Client.id == selected_client_id)
                    
                    client = session.exec(client_detail_query).first()
                    
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
                        
                        from app.models import Video, Post, JobLog
                        
                        video_count_query = select(
                            func.count(Video.id),
                            func.sum(func.case((Video.processed == True, 1), else_=0))
                        ).where(Video.client_id == selected_client_id)
                        videos = session.exec(video_count_query).first()
                        
                        post_count_query = select(
                            func.count(Post.id),
                            func.sum(func.case((Post.posted == True, 1), else_=0))
                        ).where(Post.client_id == selected_client_id)
                        posts = session.exec(post_count_query).first()
                        
                        failed_jobs_query = select(
                            func.count(JobLog.id)
                        ).where(
                            JobLog.client_id == selected_client_id,
                            JobLog.status == "failed"
                        )
                        failed_jobs = session.exec(failed_jobs_query).first()
                        
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
    
    except Exception as e:
        st.error(f"Error loading client data: {str(e)}")

elif menu == "Failed Jobs":
    st.title("Failed Jobs")
    
    try:
        with get_db_connection() as session:
            from app.models import JobLog, Client, User
            
            failed_jobs_query = select(
                JobLog.id,
                JobLog.job_type,
                JobLog.error_message,
                JobLog.created_at,
                Client.name.label("client_name"),
                User.username.label("user_name")
            ).outerjoin(Client, JobLog.client_id == Client.id
            ).outerjoin(User, JobLog.user_id == User.id
            ).where(JobLog.status == "failed"
            ).order_by(JobLog.created_at.desc())
            
            failed_jobs = session.exec(failed_jobs_query).all()
            
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
                from app.models import Video, Post, JobLog
                from sqlalchemy import func, extract
                
                videos_by_day_query = select(
                    func.date(Video.created_at).label("day"),
                    func.count(Video.id).label("count")
                ).where(
                    Video.created_at.between(start_datetime, end_datetime)
                ).group_by(
                    "day"
                ).order_by(
                    "day"
                )
                videos_by_day = session.exec(videos_by_day_query).all()
                
                posts_by_day_query = select(
                    func.date(Post.created_at).label("day"),
                    func.count(Post.id).label("count")
                ).where(
                    Post.created_at.between(start_datetime, end_datetime)
                ).group_by(
                    "day"
                ).order_by(
                    "day"
                )
                posts_by_day = session.exec(posts_by_day_query).all()
                
                jobs_by_day_query = select(
                    func.date(JobLog.created_at).label("day"),
                    JobLog.status,
                    func.count(JobLog.id).label("count")
                ).where(
                    JobLog.created_at.between(start_datetime, end_datetime)
                ).group_by(
                    "day", JobLog.status
                ).order_by(
                    "day"
                )
                jobs_by_day = session.exec(jobs_by_day_query).all()
                
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
                
                job_types_query = select(
                    JobLog.job_type,
                    func.count(JobLog.id).label("count")
                ).where(
                    JobLog.created_at.between(start_datetime, end_datetime)
                ).group_by(
                    JobLog.job_type
                ).order_by(
                    func.count(JobLog.id).desc()
                )
                job_types = session.exec(job_types_query).all()
                
                if job_types:
                    job_types_df = pd.DataFrame(job_types, columns=["job_type", "count"])
                    
                    st.subheader("Job Types Distribution")
                    fig = px.pie(job_types_df, values="count", names="job_type", title="Job Types Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No job type data available for the selected period")
    
    except Exception as e:
        st.error(f"Error loading usage charts data: {str(e)}")
