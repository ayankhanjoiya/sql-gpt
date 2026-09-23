"""PostgreSQL Connector for SQLGPT.

Enables extensible connections to PostgreSQL databases with read-only validation.
"""

from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from src.db.base import BaseDatabaseConnector
from src.db.security import SQLSecurityValidator


class PostgreSQLConnector(BaseDatabaseConnector):
    """PostgreSQL adapter implementing BaseDatabaseConnector."""

    def __init__(self):
        super().__init__()
        self.dialect_name = "postgresql"
        self.connection_url: Optional[str] = None

    def connect(self, host: str = "localhost", port: int = 5432, database: str = "",
                username: str = "", password: str = "", **kwargs) -> Tuple[bool, str]:
        """Connect to a PostgreSQL database instance."""
        try:
            self.disconnect()
            self.connection_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"

            self.engine = create_engine(
                self.connection_url,
                pool_pre_ping=True,
                pool_recycle=1800,
                connect_args={"options": "-c default_transaction_read_only=on"}
            )

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.load_schema_info()
            return True, f"Successfully connected to PostgreSQL database '{database}'."

        except Exception as e:
            self.disconnect()
            return False, f"PostgreSQL connection failed: {str(e)}"

    def disconnect(self) -> None:
        """Dispose of PostgreSQL engine pool."""
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass
            self.engine = None
        self.schema_info = {}

    def load_schema_info(self) -> Dict[str, Any]:
        """Inspect PostgreSQL tables, columns, types, and foreign keys."""
        if not self.engine:
            return {}

        try:
            inspector = inspect(self.engine)
            self.schema_info = {}
            tables = inspector.get_table_names(schema="public")

            for table in tables:
                try:
                    columns = inspector.get_columns(table, schema="public")
                    fks = inspector.get_foreign_keys(table, schema="public")
                    self.schema_info[table] = {
                        "columns": [(c["name"], str(c["type"])) for c in columns],
                        "foreign_keys": fks,
                        "indexes": []
                    }
                except Exception:
                    continue
            return self.schema_info
        except Exception:
            return {}

    def execute_query(self, sql_query: str, max_rows: int = 1000) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Validate and execute query on PostgreSQL."""
        if not self.engine:
            return None, "Database not connected."

        is_valid, sec_error, clean_sql = SQLSecurityValidator.validate(sql_query)
        if not is_valid:
            return None, f"Security Validation Rejected: {sec_error}"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(clean_sql))
                keys = list(result.keys()) if result.keys() else []
                rows = result.fetchmany(max_rows)
                df = pd.DataFrame(rows, columns=keys)
                return df, None
        except Exception as e:
            return None, f"Execution Error: {str(e)}"
