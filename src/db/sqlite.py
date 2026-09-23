"""SQLite Connector for SQLGPT.

Supports local SQLite files, in-memory instances, and uploaded databases
with connection-level read-only enforcement and safety controls.
"""

import os
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text, inspect, event
from src.db.base import BaseDatabaseConnector
from src.db.security import SQLSecurityValidator


class SQLiteConnector(BaseDatabaseConnector):
    """SQLite implementation of BaseDatabaseConnector with read-only safeguards."""

    def __init__(self):
        super().__init__()
        self.db_path: Optional[str] = None
        self.dialect_name = "sqlite"

    def connect(self, db_path: str, read_only: bool = True) -> Tuple[bool, str]:
        """Connect to an SQLite database file."""
        try:
            self.disconnect()

            if not os.path.exists(db_path):
                return False, f"Database file not found at path: {db_path}"

            self.db_path = db_path
            abs_path = os.path.abspath(db_path).replace("\\", "/")

            # Read-only URI connection string
            if read_only:
                connection_url = f"sqlite:///file:{abs_path}?mode=ro&uri=true"
            else:
                connection_url = f"sqlite:///{abs_path}"

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )

            # Enforce PRAGMA query_only = ON at connection level
            if read_only:
                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA query_only = ON;")
                    cursor.close()

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Load schema information
            self.load_schema_info()

            table_count = len(self.schema_info)
            return True, f"Successfully connected to SQLite database ({table_count} tables found)."

        except Exception as e:
            self.disconnect()
            return False, f"SQLite connection failed: {str(e)}"

    def disconnect(self) -> None:
        """Dispose of the engine and clear metadata."""
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass
            self.engine = None
        self.schema_info = {}
        self.db_path = None

    def load_schema_info(self) -> Dict[str, Any]:
        """Inspect all tables, columns, foreign keys, and indexes."""
        if not self.engine:
            return {}

        try:
            inspector = inspect(self.engine)
            self.schema_info = {}
            table_names = inspector.get_table_names()

            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)

                    self.schema_info[table_name] = {
                        "columns": [(col["name"], str(col["type"])) for col in columns],
                        "foreign_keys": foreign_keys,
                        "indexes": indexes
                    }
                except Exception:
                    continue

            return self.schema_info
        except Exception:
            self.schema_info = {}
            return {}

    def execute_query(self, sql_query: str, max_rows: int = 1000) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Validate safety and execute read-only query on SQLite engine."""
        if not self.engine:
            return None, "Database is not connected."

        # Run multi-tier security validation
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
