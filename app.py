"""SQLGPT — Natural Language SQL Assistant.

Main application entry point orchestrating Streamlit UI, LangChain LCEL SQL Engine,
Groq multi-model fallback, read-only security validation, and Plotly visualizations.
"""

import os
import uuid
import streamlit as st
from dotenv import load_dotenv

from src.db.sqlite import SQLiteConnector
from src.db.postgres import PostgreSQLConnector
from src.db.mysql import MySQLConnector
from src.llm.sql_chain import SQLGenerationEngine
from src.llm.viz_engine import VisualizationEngine
from src.ui.styles import CUSTOM_CSS
from src.ui.components import (
    render_header,
    render_sidebar_config,
    render_schema_explorer,
    render_example_queries,
    render_query_result_card
)

# Load environment variables
load_dotenv()


def init_session():
    """Initialize application session states."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "connector" not in st.session_state:
        st.session_state.connector = SQLiteConnector()
    if "viz_engine" not in st.session_state:
        st.session_state.viz_engine = VisualizationEngine()
    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = os.getenv("GROQ_API_KEY", "")
    if "db_connected" not in st.session_state:
        st.session_state.db_connected = False
    if "db_name" not in st.session_state:
        st.session_state.db_name = None


def ensure_sample_database():
    """Ensure the sample database exists, generating it if necessary."""
    sample_db = "extended_sample_data.db"
    if not os.path.exists(sample_db):
        try:
            from create_sample_db import create_extended_sample_database
            create_extended_sample_database()
        except Exception:
            pass
    return sample_db


def main():
    """Main execution loop for SQLGPT."""
    st.set_page_config(
        page_title="SQLGPT — Natural Language SQL Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Inject custom CSS styles
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_session()

    # Sidebar: Configuration & Models
    api_key, selected_model_id = render_sidebar_config()

    # Sidebar: Database Connection Management
    st.sidebar.subheader("🗄️ Database Source")
    db_source = st.sidebar.radio(
        "Select Database Type",
        ["Sample SQLite (Enterprise)", "Upload Custom SQLite (.db)", "PostgreSQL / MySQL"],
        index=0
    )

    connector = st.session_state.connector

    if db_source == "Sample SQLite (Enterprise)":
        sample_path = ensure_sample_database()
        # Auto-connect if not connected yet or on explicit click
        if not st.session_state.db_connected and not st.session_state.db_name:
            success, msg = connector.connect(sample_path)
            if success:
                st.session_state.db_connected = True
                st.session_state.db_name = "Enterprise Sample DB (Customers, Orders, Products)"

        if st.sidebar.button("⚡ Reconnect Sample DB", use_container_width=True):
            success, msg = connector.connect(sample_path)
            if success:
                st.session_state.db_connected = True
                st.session_state.db_name = "Enterprise Sample DB (Customers, Orders, Products)"
                st.sidebar.success("✅ Connected to Sample Database")
            else:
                st.sidebar.error(f"Connection error: {msg}")

    elif db_source == "Upload Custom SQLite (.db)":
        uploaded_file = st.sidebar.file_uploader(
            "Upload SQLite File",
            type=["db", "sqlite", "sqlite3"],
            help="Upload your own database to query (Max 100MB)"
        )
        if uploaded_file:
            save_path = "uploaded_custom.db"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            success, msg = connector.connect(save_path)
            if success:
                st.session_state.db_connected = True
                st.session_state.db_name = uploaded_file.name
                st.sidebar.success(f"✅ Loaded: {uploaded_file.name}")
            else:
                st.sidebar.error(f"Failed to load: {msg}")

    elif db_source == "PostgreSQL / MySQL":
        engine_type = st.sidebar.selectbox("Dialect", ["PostgreSQL", "MySQL"])
        host = st.sidebar.text_input("Host", "localhost")
        port = st.sidebar.number_input("Port", value=5432 if engine_type == "PostgreSQL" else 3306)
        db = st.sidebar.text_input("Database Name", "")
        user = st.sidebar.text_input("Username", "")
        pwd = st.sidebar.text_input("Password", type="password")

        if st.sidebar.button("🔗 Connect to Server", use_container_width=True):
            if engine_type == "PostgreSQL":
                st.session_state.connector = PostgreSQLConnector()
            else:
                st.session_state.connector = MySQLConnector()

            connector = st.session_state.connector
            success, msg = connector.connect(
                host=host, port=port, database=db, username=user, password=pwd
            )
            if success:
                st.session_state.db_connected = True
                st.session_state.db_name = f"{engine_type}: {db}@{host}"
                st.sidebar.success(f"✅ Connected to {engine_type}")
            else:
                st.sidebar.error(f"Connection failed: {msg}")

    # Sidebar: Schema Explorer
    render_schema_explorer(connector.schema_info)

    # Main Application Interface
    render_header()

    # Active connection banner
    if st.session_state.db_connected and st.session_state.db_name:
        st.markdown(
            f"""<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">
                <div><span class="status-dot"></span><b>Connected Database:</b> {st.session_state.db_name} ({len(connector.schema_info)} tables)</div>
            </div>""",
            unsafe_allow_html=True
        )
    else:
        st.info("👈 **Get Started:** Please connect to the Sample Database or upload an SQLite file in the sidebar.")

    # Render Example Query Chips
    render_example_queries()

    st.markdown("---")

    # Chat history display & actions
    if st.session_state.chat_history:
        col_clear, _ = st.columns([1, 6])
        if col_clear.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            st.rerun()

        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f"**{message['content']}**")
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    render_query_result_card(message, st.session_state.viz_engine)

    # Handle Input from Chat Input or Prompt Chips
    user_prompt = st.chat_input("Ask any question about your database (e.g., 'Show top 5 customers by sales')...")

    if "submitted_prompt" in st.session_state and st.session_state["submitted_prompt"]:
        user_prompt = st.session_state["submitted_prompt"]
        st.session_state["submitted_prompt"] = None

    if user_prompt:
        if not api_key:
            st.error("🔑 Please provide your Groq API Key in the sidebar to generate queries.")
            return

        if not st.session_state.db_connected or not connector.schema_info:
            st.error("🗄️ Please connect to a database first.")
            return

        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            st.markdown(f"**{user_prompt}**")

        # Execute AI SQL Generation and Self-Healing Pipeline
        with st.chat_message("assistant"):
            with st.spinner("🤖 Translating natural language to SQL & orchestrating Groq models..."):
                sql_engine = SQLGenerationEngine(api_key=api_key, preferred_model=selected_model_id)
                result = sql_engine.execute_and_self_heal(user_prompt, connector)

            if result["success"]:
                result_payload = {
                    "id": str(uuid.uuid4())[:8],
                    "role": "assistant",
                    "user_query": user_prompt,
                    "sql_query": result["sql_query"],
                    "dataframe": result["dataframe"],
                    "summary": result["summary"],
                    "retries_used": result["retries_used"]
                }
                st.session_state.chat_history.append(result_payload)
                render_query_result_card(result_payload, st.session_state.viz_engine)
            else:
                err_payload = {
                    "id": str(uuid.uuid4())[:8],
                    "role": "assistant",
                    "user_query": user_prompt,
                    "sql_query": result.get("sql_query"),
                    "dataframe": None,
                    "summary": f"❌ **Execution Failed:** {result.get('error')}",
                    "retries_used": result.get("retries_used", 0)
                }
                st.session_state.chat_history.append(err_payload)
                st.error(err_payload["summary"])
                if result.get("sql_query"):
                    with st.expander("View Attempted SQL Query"):
                        st.code(result["sql_query"], language="sql")


if __name__ == "__main__":
    main()
