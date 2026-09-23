import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import re
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from sqlalchemy import create_engine, text, inspect
from langchain.prompts import PromptTemplate
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

# Load environment variables
load_dotenv()

# Model configuration (embedded for deployment)
AVAILABLE_MODELS = {
    "llama-3.1-70b-versatile": {
        "name": "Llama 3.1 70B Versatile",
        "description": "Best for complex reasoning and SQL generation",
        "context_length": 131072,
        "recommended": True
    },
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B Instant", 
        "description": "Faster responses, good for simple queries",
        "context_length": 131072,
        "recommended": False
    },
    "gemma2-9b-it": {
        "name": "Gemma 2 9B IT",
        "description": "Google's instruction-tuned model",
        "context_length": 8192,
        "recommended": False
    }
}

DEFAULT_MODEL = "llama-3.1-70b-versatile"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "gemma2-9b-it"]

class EnhancedSQLAssistant:
    def __init__(self):
        self.llm = None
        self.db_path = None
        self.engine = None
        self.schema_info = None
        self.current_model = None
        self.sql_database = None
        self.agent = None
        self._connection = None  # Track connection for cleanup
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
        
    def cleanup(self):
        """Properly cleanup all resources"""
        try:
            # Close database connection
            if self._connection:
                self._connection.close()
                self._connection = None
            
            # Dispose of SQLAlchemy engine
            if self.engine:
                self.engine.dispose()
                self.engine = None
            
            # Clear agent and database references
            self.agent = None
            self.sql_database = None
            
            # Clear cached data
            self.schema_info = None
            
        except Exception as e:
            # Silent cleanup - don't raise exceptions during cleanup
            pass
        
    def setup_llm(self, api_key, preferred_model=None):
        """Initialize the ChatGroq LLM with automatic fallback"""
        models_to_try = [preferred_model] if preferred_model else [DEFAULT_MODEL] + FALLBACK_MODELS
        
        for model_name in models_to_try:
            if model_name is None:
                continue
                
            try:
                self.llm = ChatGroq(
                    api_key=api_key,
                    model_name=model_name,
                    temperature=0,
                    streaming=True
                )
                # Test the model with a simple query
                test_response = self.llm.invoke("Hello")
                self.current_model = model_name
                return True, f"Successfully connected using {AVAILABLE_MODELS.get(model_name, {}).get('name', model_name)}"
            except Exception as e:
                error_msg = str(e)
                if "decommissioned" in error_msg.lower() or "not supported" in error_msg.lower():
                    continue  # Try next model
                else:
                    return False, f"Error with {model_name}: {error_msg}"
        
        return False, "All available models failed. Please check your API key and try again."
    
    def connect_database(self, db_path):
        """Connect to SQLite database with proper resource management"""
        try:
            # Cleanup any existing connections first
            self.cleanup()
            
            self.db_path = db_path
            
            # Create engine with proper connection pooling and cleanup
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=False           # Disable SQL logging for performance
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                self._connection = conn
            
            # Create LangChain SQLDatabase for agent
            self.sql_database = SQLDatabase(self.engine)
            
            # Setup SQL Agent if LLM is available
            if self.llm:
                self.setup_agent()
            
            # Get schema information for UI display
            self._load_schema_info()
            
            return True
            
        except Exception as e:
            st.error(f"Error connecting to database: {str(e)}")
            self.cleanup()  # Cleanup on error
            return False
    
    def _load_schema_info(self):
        """Load schema information with proper error handling"""
        try:
            inspector = inspect(self.engine)
            self.schema_info = {}
            
            # Limit schema loading to prevent memory issues
            table_names = inspector.get_table_names()[:10]  # Limit to first 10 tables
            
            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)
                    
                    self.schema_info[table_name] = {
                        'columns': [(col['name'], str(col['type'])) for col in columns],
                        'foreign_keys': foreign_keys,
                        'indexes': indexes
                    }
                except Exception as table_error:
                    # Skip problematic tables instead of failing completely
                    st.warning(f"Could not load schema for table {table_name}: {str(table_error)}")
                    continue
                    
        except Exception as e:
            st.error(f"Error loading schema information: {str(e)}")
            self.schema_info = {}
    
    def setup_agent(self):
        """Setup SQL Agent with toolkit and proper safeguards"""
        try:
            if self.llm and self.sql_database:
                toolkit = SQLDatabaseToolkit(db=self.sql_database, llm=self.llm)
                
                # Create agent with strict limits to prevent infinite loops
                self.agent = create_sql_agent(
                    llm=self.llm,
                    toolkit=toolkit,
                    verbose=False,  # Disable verbose to prevent output loops
                    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    handle_parsing_errors=True,
                    max_iterations=3,  # Strict limit on iterations
                    max_execution_time=15  # Reduced timeout
                )
                return True
        except Exception as e:
            st.error(f"Error setting up SQL agent: {str(e)}")
            # Log the specific error for debugging
            print(f"Agent setup error: {str(e)}")
            self.agent = None
            return False
    
    def is_visualization_requested(self, query):
        """Check if the user is asking for a visualization"""
        viz_keywords = [
            'chart', 'graph', 'plot', 'visualize', 'visualization', 'show chart',
            'bar chart', 'pie chart', 'line chart', 'scatter plot', 'histogram',
            'draw', 'display chart', 'create chart', 'generate chart'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in viz_keywords)
    
    def process_query_with_agent(self, natural_language_query):
        """Process query using SQL Agent with proper timeout and circuit breaker"""
        if not self.agent:
            return None, None, "SQL Agent not initialized. Please connect to database and AI first."
        
        try:
            import threading
            import time
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            # Use ThreadPoolExecutor for proper timeout handling (Windows compatible)
            def run_agent_query():
                try:
                    # Use invoke instead of deprecated run method
                    response = self.agent.invoke({"input": natural_language_query})
                    # Extract the output from the response
                    if isinstance(response, dict) and 'output' in response:
                        return response['output']
                    elif isinstance(response, str):
                        return response
                    else:
                        return str(response)
                except Exception as e:
                    # Log the specific error for debugging
                    print(f"Agent execution error: {str(e)}")
                    raise e
            
            # Execute with timeout using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_agent_query)
                try:
                    # 15 second timeout with proper exception handling
                    response = future.result(timeout=15)
                    
                    # Try to extract data if the agent executed a query
                    df = self.extract_data_from_agent_execution(natural_language_query)
                    
                    return None, df, response
                    
                except FutureTimeoutError:
                    # Cancel the future and fallback
                    future.cancel()
                    st.warning("Agent query timed out. Switching to direct SQL approach...")
                    return self.fallback_sql_execution(natural_language_query)
                    
        except Exception as e:
            # Always fallback to direct SQL on any error
            error_message = str(e)
            if "early_stopping_method" in error_message:
                st.warning("Agent configuration issue detected. Using direct SQL approach...")
            else:
                st.warning(f"Agent execution failed: {error_message[:100]}... Using direct SQL approach.")
            return self.fallback_sql_execution(natural_language_query)
    
    def fallback_sql_execution(self, natural_language_query):
        """Fallback method when agent fails"""
        try:
            # Try to generate and execute a simple SQL query
            sql_query, error = self.generate_sql_query(natural_language_query)
            if sql_query and not error:
                df, exec_error = self.execute_query(sql_query)
                if not exec_error:
                    return sql_query, df, f"Executed SQL query: {sql_query}"
                else:
                    return None, None, f"SQL execution error: {exec_error}"
            else:
                return None, None, f"Could not generate SQL query: {error}"
        except Exception as e:
            return None, None, f"Fallback execution failed: {str(e)}"
    
    def extract_data_from_agent_execution(self, query):
        """Try to extract data by executing a simple query if agent's response suggests data retrieval"""
        try:
            # Generate a simple SQL query as fallback
            sql_query, error = self.generate_sql_query(query)
            if sql_query and not error:
                df, exec_error = self.execute_query(sql_query)
                if not exec_error:
                    return df
        except:
            pass
        return None
    
    def generate_sql_query(self, natural_language_query):
        """Generate SQL query from natural language using LLM (fallback method)"""
        if not self.llm or not self.schema_info:
            return None, "LLM or database not initialized"
        
        # Get schema description
        schema_desc = self.get_schema_description()
        
        # Get sample data for context
        sample_data = ""
        for table_name in list(self.schema_info.keys())[:3]:
            sample_data += f"\nSample data from {table_name}:\n"
            sample_data += self.get_sample_data(table_name, 2)
            sample_data += "\n"
        
        prompt_template = PromptTemplate(
            input_variables=["schema", "sample_data", "question"],
            template="""
You are an expert SQL query generator. Given the database schema and sample data below, generate a SQL query to answer the user's question.

{schema}

{sample_data}

User Question: {question}

Important Instructions:
1. Generate ONLY a valid SQL query, no explanations
2. Use proper SQLite syntax
3. Include appropriate JOINs when needed
4. Use aggregate functions when appropriate
5. Add LIMIT clauses for large result sets (default LIMIT 100)
6. Use proper column aliases for readability
7. Ensure the query is safe and doesn't modify data

SQL Query:
"""
        )
        
        try:
            prompt = prompt_template.format(
                schema=schema_desc,
                sample_data=sample_data,
                question=natural_language_query
            )
            
            response = self.llm.invoke(prompt)
            sql_query = response.content.strip()
            
            # Clean up the response
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()
            
            return sql_query, None
        except Exception as e:
            return None, f"Error generating query: {str(e)}"
    
    def execute_query(self, sql_query):
        """Execute SQL query with proper resource management and security"""
        try:
            if not sql_query or not sql_query.strip():
                return None, "Empty query provided"
                
            # Enhanced security check
            query_upper = sql_query.strip().upper()
            if not query_upper.startswith('SELECT'):
                return None, "Only SELECT queries are allowed for security reasons"
            
            # Check for dangerous keywords even within SELECT statements
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return None, f"Query contains potentially dangerous operations: {keyword}"
            
            # Additional security: check for semicolon (SQL injection prevention)
            if ';' in sql_query and not sql_query.rstrip().endswith(';'):
                return None, "Multiple statements not allowed for security reasons"
            
            # Execute query with proper connection management
            with self.engine.connect() as connection:
                try:
                    # Use text() for proper query execution
                    result = connection.execute(text(sql_query))
                    
                    # Convert to DataFrame with size limit
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    
                    # Limit result size to prevent memory issues
                    if len(df) > 1000:
                        df = df.head(1000)
                        st.warning("Results limited to first 1000 rows for performance")
                    
                    return df, None
                    
                except Exception as exec_error:
                    return None, f"Query execution error: {str(exec_error)}"
                    
        except Exception as e:
            return None, f"Error executing query: {str(e)}"
    
    def get_schema_description(self):
        """Generate a comprehensive schema description for the LLM"""
        if not self.schema_info:
            return "No schema information available."
        
        description = "Database Schema:\n\n"
        
        for table_name, info in self.schema_info.items():
            description += f"Table: {table_name}\n"
            description += "Columns:\n"
            for col_name, col_type in info['columns']:
                description += f"  - {col_name} ({col_type})\n"
            
            if info['foreign_keys']:
                description += "Foreign Keys:\n"
                for fk in info['foreign_keys']:
                    description += f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}\n"
            
            description += "\n"
        
        return description
    
    def get_sample_data(self, table_name, limit=3):
        """Get sample data from a table"""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            df = pd.read_sql_query(query, self.engine)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error getting sample data: {str(e)}"
    
    def suggest_visualizations(self, df):
        """Suggest appropriate visualizations based on data"""
        if df is None or df.empty:
            return []
        
        suggestions = []
        
        # Check for numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            suggestions.append({
                'type': 'bar',
                'title': 'Bar Chart',
                'description': f'Show {numeric_cols[0]} by {categorical_cols[0]}'
            })
            
            if len(numeric_cols) >= 2:
                suggestions.append({
                    'type': 'scatter',
                    'title': 'Scatter Plot',
                    'description': f'Show relationship between {numeric_cols[0]} and {numeric_cols[1]}'
                })
        
        if len(numeric_cols) >= 1:
            suggestions.append({
                'type': 'histogram',
                'title': 'Histogram',
                'description': f'Distribution of {numeric_cols[0]}'
            })
        
        if len(categorical_cols) >= 1:
            suggestions.append({
                'type': 'pie',
                'title': 'Pie Chart',
                'description': f'Distribution of {categorical_cols[0]}'
            })
        
        return suggestions
    
    def create_visualization(self, df, viz_type, x_col=None, y_col=None):
        """Create visualization based on type and columns"""
        try:
            if viz_type == 'bar':
                fig = px.bar(df, x=x_col, y=y_col, title=f'{y_col} by {x_col}')
            elif viz_type == 'scatter':
                fig = px.scatter(df, x=x_col, y=y_col, title=f'{y_col} vs {x_col}')
            elif viz_type == 'histogram':
                fig = px.histogram(df, x=x_col, title=f'Distribution of {x_col}')
            elif viz_type == 'pie':
                pie_data = df[x_col].value_counts().reset_index()
                pie_data.columns = [x_col, 'count']
                fig = px.pie(pie_data, values='count', names=x_col, title=f'Distribution of {x_col}')
            elif viz_type == 'line':
                fig = px.line(df, x=x_col, y=y_col, title=f'{y_col} over {x_col}')
            else:
                return None
            
            return fig
        except Exception as e:
            st.error(f"Error creating visualization: {str(e)}")
            return None

def main():
    st.title("🤖 Enhanced SQL Assistant")
    st.markdown("Chat with your SQL database using natural language!")
    
    # Initialize session state with proper cleanup
    if 'assistant' not in st.session_state:
        st.session_state.assistant = EnhancedSQLAssistant()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_data' not in st.session_state:
        st.session_state.current_data = None
    if 'show_visualization' not in st.session_state:
        st.session_state.show_visualization = False
    
    # Register cleanup function for session end
    def cleanup_on_session_end():
        if 'assistant' in st.session_state:
            st.session_state.assistant.cleanup()
    
    # Add cleanup to session state
    if 'cleanup_registered' not in st.session_state:
        import atexit
        atexit.register(cleanup_on_session_end)
        st.session_state.cleanup_registered = True
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input("Groq API Key", type="password", 
                               value=os.getenv("GROQ_API_KEY", ""))
        
        # Model selection
        st.subheader("🤖 AI Model")
        model_options = ["Auto (Recommended)"] + list(AVAILABLE_MODELS.keys())
        selected_model = st.selectbox("Choose Model", model_options)
        
        if selected_model == "Auto (Recommended)":
            preferred_model = None
        else:
            preferred_model = selected_model
            st.info(f"**{AVAILABLE_MODELS[selected_model]['name']}**\n\n{AVAILABLE_MODELS[selected_model]['description']}")
        
        # Setup LLM
        if api_key and st.button("🔗 Connect to AI"):
            with st.spinner("Connecting to AI model..."):
                success, message = st.session_state.assistant.setup_llm(api_key, preferred_model)
                if success:
                    st.success(f"✅ {message}")
                    # Setup agent if database is already connected
                    if st.session_state.assistant.sql_database:
                        if st.session_state.assistant.setup_agent():
                            st.info("🤖 SQL Agent initialized for intelligent query processing!")
                else:
                    st.error(f"❌ {message}")
        
        # Show current model status
        if st.session_state.assistant.current_model:
            model_info = AVAILABLE_MODELS.get(st.session_state.assistant.current_model, {})
            st.success(f"🤖 **Connected**: {model_info.get('name', st.session_state.assistant.current_model)}")
        
        # Database selection
        st.header("🗄️ Database")
        
        # Check for sample database
        sample_db_path = "extended_sample_data.db"
        if os.path.exists(sample_db_path):
            if st.button("Use Sample Database"):
                if st.session_state.assistant.connect_database(sample_db_path):
                    if st.session_state.assistant.agent:
                        st.success("✅ Connected to sample database with AI Agent!")
                    else:
                        st.success("✅ Connected to sample database!")
        
        # File upload for custom database
        uploaded_file = st.file_uploader("Upload SQLite Database", type=['db', 'sqlite', 'sqlite3'])
        if uploaded_file:
            try:
                # Validate file size (max 100MB)
                if uploaded_file.size > 100 * 1024 * 1024:
                    st.error("File size too large. Maximum size is 100MB.")
                else:
                    # Save uploaded file with proper error handling
                    upload_path = "uploaded_database.db"
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Clean up any existing connections before connecting to new database
                    st.session_state.assistant.cleanup()
                    
                    if st.session_state.assistant.connect_database(upload_path):
                        if st.session_state.assistant.agent:
                            st.success("✅ Database uploaded and connected with AI Agent!")
                        else:
                            st.success("✅ Database uploaded and connected!")
                    else:
                        # Clean up failed upload
                        try:
                            os.remove(upload_path)
                        except:
                            pass
                        st.error("Failed to connect to uploaded database.")
            except Exception as e:
                st.error(f"Error uploading database: {str(e)}")
                # Clean up on error
                try:
                    os.remove("uploaded_database.db")
                except:
                    pass
        
        # Display schema information
        if st.session_state.assistant.schema_info:
            st.header("📋 Database Schema")
            for table_name, info in st.session_state.assistant.schema_info.items():
                with st.expander(f"Table: {table_name}"):
                    st.write("**Columns:**")
                    for col_name, col_type in info['columns']:
                        st.write(f"• {col_name} ({col_type})")
    
    # Main chat interface
    if st.session_state.assistant.llm and st.session_state.assistant.schema_info:
        
        # Chat controls and example queries
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.header("💬 Chat with your Database")
        
        with col2:
            if st.button("🗑️ Clear Chat", help="Clear chat history"):
                st.session_state.chat_history = []
                st.session_state.current_data = None
                st.session_state.show_visualization = False
                st.rerun()
        
        # Example queries section
        with st.expander("💡 Example Queries (click to use)"):
            example_queries = [
                "Show all tables in the database",
                "Count total records in each table", 
                "Show the first 10 records from any table",
                "Find records with null values",
                "Show table with the most records",
                "Display column names and types for all tables"
            ]
            
            cols = st.columns(2)
            for i, example in enumerate(example_queries):
                with cols[i % 2]:
                    if st.button(example, key=f"example_{i}"):
                        st.session_state.pending_query = example
        
        # Chat input
        user_query = st.chat_input("Ask me anything about your database...")
        
        # Handle example query clicks
        if 'pending_query' in st.session_state:
            user_query = st.session_state.pending_query
            del st.session_state.pending_query
        
        if user_query:
            # Check if visualization is requested
            visualization_requested = st.session_state.assistant.is_visualization_requested(user_query)
            
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            # Process query with enhanced agent-based approach
            with st.spinner("🤖 Processing your query with AI agent..."):
                sql_query, df, agent_response = st.session_state.assistant.process_query_with_agent(user_query)
            
            if "Error" in str(agent_response):
                st.session_state.chat_history.append({"role": "assistant", "content": f"❌ {agent_response}"})
            else:
                # Store current data for visualization
                st.session_state.current_data = df
                st.session_state.show_visualization = visualization_requested
                
                # Create enhanced result message
                result_message = f"🤖 **AI Agent Response:**\n\n{agent_response}"
                
                if df is not None and not df.empty:
                    result_message += f"\n\n📊 **Data Retrieved:** {len(df)} rows"
                    if visualization_requested:
                        result_message += "\n\n📈 *Visualization options are shown below the results.*"
                
                st.session_state.chat_history.append({"role": "assistant", "content": result_message})
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Display current results
        if st.session_state.current_data is not None and not st.session_state.current_data.empty:
            st.header("📊 Query Results")
            
            # Display data table
            st.dataframe(st.session_state.current_data, use_container_width=True)
            
            # Download button
            csv = st.session_state.current_data.to_csv(index=False)
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv"
            )
            
            # Visualization section - only show when requested
            if st.session_state.show_visualization:
                st.header("📈 Data Visualization")
                
                # Get visualization suggestions
                suggestions = st.session_state.assistant.suggest_visualizations(st.session_state.current_data)
                
                if suggestions:
                    # Create columns for visualization controls
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        viz_type = st.selectbox("Chart Type", 
                                              [s['type'] for s in suggestions],
                                              format_func=lambda x: next(s['title'] for s in suggestions if s['type'] == x))
                    
                    # Get column options
                    numeric_cols = st.session_state.current_data.select_dtypes(include=['int64', 'float64']).columns.tolist()
                    categorical_cols = st.session_state.current_data.select_dtypes(include=['object']).columns.tolist()
                    all_cols = st.session_state.current_data.columns.tolist()
                    
                    with col2:
                        if viz_type in ['bar', 'scatter', 'line']:
                            x_col = st.selectbox("X-axis", all_cols)
                        elif viz_type in ['histogram', 'pie']:
                            x_col = st.selectbox("Column", all_cols)
                        else:
                            x_col = None
                    
                    with col3:
                        if viz_type in ['bar', 'scatter', 'line']:
                            y_col = st.selectbox("Y-axis", numeric_cols if numeric_cols else all_cols)
                        else:
                            y_col = None
                    
                    # Create and display visualization
                    if st.button("🎨 Create Visualization"):
                        fig = st.session_state.assistant.create_visualization(
                            st.session_state.current_data, viz_type, x_col, y_col
                        )
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("❌ No suitable visualizations available for this data.")
            else:
                # Show tip when visualization is not requested
                st.info("💡 **Tip:** Ask for a chart or visualization in your query to see data visualization options!")
                st.markdown("**Examples:** *'Show me a bar chart of...'* or *'Create a pie chart of...'* or *'Visualize the distribution of...'*")
    
    else:
        st.info("👋 Please configure your API key and connect to a database to start chatting!")
        
        # Quick start section
        st.header("🚀 Quick Start")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🔑 Step 1: Get your Groq API Key
            - Visit [console.groq.com](https://console.groq.com/)
            - Create an account and get your API key
            - Enter it in the sidebar
            """)
        
        with col2:
            st.markdown("""
            ### 🗄️ Step 2: Connect to Database
            - Use the sample database (if available)
            - Or upload your own SQLite database
            - Schema will be displayed in sidebar
            """)
        
        st.markdown("""
        ### 💬 Step 3: Start Chatting
        - Ask questions in natural language
        - Use example queries for common database operations
        - Request visualizations by mentioning 'chart', 'graph', or 'plot'
        """)

if __name__ == "__main__":
    main()
