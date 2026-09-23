"""Abstract Base Database Connector for SQLGPT.

Defines the contract for database connections, schema inspection,
and secure read-only execution across various SQL dialects.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy.engine import Engine


class BaseDatabaseConnector(ABC):
    """Abstract interface for SQL database adapters."""

    def __init__(self):
        self.engine: Optional[Engine] = None
        self.schema_info: Dict[str, Any] = {}
        self.dialect_name: str = "sql"

    @abstractmethod
    def connect(self, **kwargs) -> Tuple[bool, str]:
        """Establish connection to the database.

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely release and close all active connections and engine pools."""
        pass

    @abstractmethod
    def load_schema_info(self) -> Dict[str, Any]:
        """Inspect and return schema metadata including tables, columns, and types."""
        pass

    @abstractmethod
    def execute_query(self, sql_query: str, max_rows: int = 1000) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Execute a validated read-only SQL query and return results as a DataFrame.

        Returns:
            Tuple of (dataframe: Optional[pd.DataFrame], error_message: Optional[str])
        """
        pass

    def get_sample_data(self, table_name: str, limit: int = 3) -> str:
        """Fetch a sample of rows from a specified table for schema prompting."""
        if not self.engine:
            return "No connection."
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            df, error = self.execute_query(query, max_rows=limit)
            if df is not None and not df.empty:
                return df.to_string(index=False)
            return "No data in table."
        except Exception as e:
            return f"Error retrieving sample: {str(e)}"

    def get_schema_prompt_description(self) -> str:
        """Format the database schema as a detailed prompt string for LLM SQL generation."""
        if not self.schema_info:
            return "No schema available."

        desc = f"Database Dialect: {self.dialect_name.upper()}\nDatabase Schema:\n\n"
        for table_name, info in self.schema_info.items():
            desc += f"Table: {table_name}\n"
            desc += "Columns:\n"
            for col_name, col_type in info.get("columns", []):
                desc += f"  - {col_name} ({col_type})\n"

            fks = info.get("foreign_keys", [])
            if fks:
                desc += "Foreign Keys:\n"
                for fk in fks:
                    referred = fk.get("referred_table", "")
                    const_cols = fk.get("constrained_columns", [])
                    ref_cols = fk.get("referred_columns", [])
                    desc += f"  - {const_cols} -> {referred}.{ref_cols}\n"
            desc += "\n"
        return desc
