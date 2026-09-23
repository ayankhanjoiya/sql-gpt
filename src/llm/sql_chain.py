"""LangChain SQL Orchestration Engine with Self-Correction and Result Summarization.

Orchestrates the conversion of natural-language questions into accurate SQL queries,
validates syntax and security, supports automatic error-correction loops, and summarizes
retrieved data into executive natural language insights.
"""

from typing import Tuple, Optional, Dict, Any, List
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.db.base import BaseDatabaseConnector
from src.db.security import SQLSecurityValidator
from src.llm.models import get_groq_llm_with_fallbacks, build_groq_llm, DEFAULT_MODEL_ID


SQL_GEN_SYSTEM_PROMPT = """You are an expert SQL engineer. Given a database schema and a natural language question, your task is to generate a single, syntactically correct, highly optimized read-only SQL query.

{dialect_info}

{schema_context}

{sample_data_context}

STRICT GENERATION RULES:
1. Output ONLY the raw SQL query. No greetings, markdown explanations, or thoughts.
2. The query MUST be strictly read-only (SELECT or WITH ... SELECT).
3. Use proper column and table names exactly as defined in the schema.
4. Use standard JOIN operations with explicit ON conditions where necessary.
5. Apply appropriate aggregate functions (SUM, AVG, COUNT, MIN, MAX) when summarizing data.
6. Use meaningful column aliases (e.g. AS total_revenue) for readability.
7. Always append 'LIMIT 100' or appropriate limit if large result sets are expected and not explicitly requested otherwise.
8. NEVER generate mutating statements like INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or PRAGMA.
"""

SQL_FIX_SYSTEM_PROMPT = """You are an expert SQL debugger. The SQL query previously generated resulted in an execution error. Fix the query using the database schema and error message provided.

{dialect_info}
{schema_context}

Original Question: {question}
Failing SQL Query: {failing_sql}
Database Error: {error_message}

RULES:
1. Output ONLY the corrected raw SQL query.
2. Ensure it strictly adheres to read-only constraints and resolves the specific error.
"""

SUMMARY_SYSTEM_PROMPT = """You are an executive data analyst. Summarize the following SQL query results to directly answer the user's natural language question in 2-3 concise, insightful bullet points.

User Question: {question}
SQL Query Executed: {sql_query}
Data Preview (First {row_count} rows):
{data_preview}

Summary Guidelines:
- Highlight key trends, top metrics, anomalies, or totals.
- Be direct, professional, and clear.
- Keep numbers formatted nicely (e.g., $12,500 or 45%).
"""


class SQLGenerationEngine:
    """Orchestrates natural language to SQL generation, self-correction, and summarization."""

    def __init__(self, api_key: str, preferred_model: Optional[str] = None):
        self.api_key = api_key
        self.preferred_model = preferred_model or DEFAULT_MODEL_ID
        self.llm_chain = get_groq_llm_with_fallbacks(api_key, self.preferred_model)

    def generate_sql(self, question: str, connector: BaseDatabaseConnector) -> Tuple[Optional[str], Optional[str]]:
        """Generate a validated read-only SQL query from a user question."""
        schema_context = connector.get_schema_prompt_description()
        dialect_info = f"Target Database Dialect: {connector.dialect_name.upper()}"

        # Collect sample data for the first 3 tables
        sample_data_context = "Sample Data for Context:\n"
        table_keys = list(connector.schema_info.keys())[:3]
        for tbl in table_keys:
            sample_data_context += f"Table '{tbl}':\n{connector.get_sample_data(tbl, limit=2)}\n\n"

        prompt = ChatPromptTemplate.from_messages([
            ("system", SQL_GEN_SYSTEM_PROMPT),
            ("user", "Generate the SQL query for: {question}")
        ])

        chain = prompt | self.llm_chain | StrOutputParser()

        try:
            raw_sql = chain.invoke({
                "dialect_info": dialect_info,
                "schema_context": schema_context,
                "sample_data_context": sample_data_context,
                "question": question
            })

            clean_sql = SQLSecurityValidator.sanitize_query(raw_sql)
            return clean_sql, None

        except Exception as e:
            return None, f"LLM Generation Error: {str(e)}"

    def self_heal_sql(self, question: str, failing_sql: str, error_msg: str,
                      connector: BaseDatabaseConnector) -> Tuple[Optional[str], Optional[str]]:
        """Self-healing loop: feed execution error back to LLM to regenerate working SQL."""
        schema_context = connector.get_schema_prompt_description()
        dialect_info = f"Target Database Dialect: {connector.dialect_name.upper()}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", SQL_FIX_SYSTEM_PROMPT),
            ("user", "Fix the failing SQL query.")
        ])

        chain = prompt | self.llm_chain | StrOutputParser()

        try:
            fixed_sql = chain.invoke({
                "dialect_info": dialect_info,
                "schema_context": schema_context,
                "question": question,
                "failing_sql": failing_sql,
                "error_message": error_msg
            })

            clean_sql = SQLSecurityValidator.sanitize_query(fixed_sql)
            return clean_sql, None
        except Exception as e:
            return None, f"Self-healing error: {str(e)}"

    def execute_and_self_heal(self, question: str, connector: BaseDatabaseConnector,
                              max_retries: int = 2) -> Dict[str, Any]:
        """Generate, validate, and execute SQL with automatic self-healing and result synthesis.

        Returns a dictionary containing:
        - sql_query: Final executed SQL query
        - dataframe: Query results as pandas DataFrame
        - summary: Natural language executive summary
        - success: Boolean status
        - error: Error description if failed
        - retries_used: Number of self-healing attempts performed
        """
        # Step 1: Initial SQL Generation
        sql_query, gen_error = self.generate_sql(question, connector)
        if gen_error or not sql_query:
            return {
                "sql_query": None,
                "dataframe": None,
                "summary": None,
                "success": False,
                "error": gen_error or "Could not generate query.",
                "retries_used": 0
            }

        retries_used = 0
        current_sql = sql_query

        # Step 2: Execution & Self-Correction Loop
        for attempt in range(max_retries + 1):
            df, exec_error = connector.execute_query(current_sql)

            if exec_error is None and df is not None:
                # Query executed successfully!
                summary = self.summarize_results(question, current_sql, df)
                return {
                    "sql_query": current_sql,
                    "dataframe": df,
                    "summary": summary,
                    "success": True,
                    "error": None,
                    "retries_used": retries_used
                }

            # If failed and retries remaining, attempt self-healing
            if attempt < max_retries:
                retries_used += 1
                healed_sql, heal_err = self.self_heal_sql(question, current_sql, exec_error, connector)
                if healed_sql and not heal_err:
                    current_sql = healed_sql
                else:
                    break
            else:
                return {
                    "sql_query": current_sql,
                    "dataframe": None,
                    "summary": None,
                    "success": False,
                    "error": exec_error,
                    "retries_used": retries_used
                }

        return {
            "sql_query": current_sql,
            "dataframe": None,
            "summary": None,
            "success": False,
            "error": "Query failed after retry attempts.",
            "retries_used": retries_used
        }

    def summarize_results(self, question: str, sql_query: str, df: pd.DataFrame) -> str:
        """Synthesize query results into concise natural language insights."""
        if df.empty:
            return "The query executed successfully but returned 0 records matching your criteria."

        preview_rows = min(10, len(df))
        preview_text = df.head(preview_rows).to_string(index=False)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARY_SYSTEM_PROMPT),
            ("user", "Please provide the executive summary.")
        ])

        chain = prompt | self.llm_chain | StrOutputParser()

        try:
            return chain.invoke({
                "question": question,
                "sql_query": sql_query,
                "row_count": preview_rows,
                "data_preview": preview_text
            })
        except Exception:
            return f"Retrieved {len(df)} rows corresponding to your request."
