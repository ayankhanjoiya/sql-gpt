"""SQL Security and Injection Prevention Validator.

Implements multi-layer defenses to ensure all executed SQL queries are strictly
read-only and free from malicious injection patterns or multi-statement attacks.
"""

import re
from typing import Tuple, Optional

try:
    import sqlparse
    from sqlparse.sql import Statement, Token
    from sqlparse.tokens import Keyword, DDL, DML
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False


class SQLSecurityValidator:
    """Validates SQL queries to enforce read-only execution and prevent injection."""

    # Disallowed SQL keywords that mutate state or grant elevated access
    DANGEROUS_KEYWORDS = {
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE",
        "REPLACE", "ATTACH", "DETACH", "PRAGMA", "EXEC", "EXECUTE", "GRANT",
        "REVOKE", "MERGE", "UPSERT", "SHUTDOWN", "KILL", "INTO OUTFILE",
        "INTO DUMPFILE", "LOAD DATA", "FLUSH"
    }

    # Allowed leading statement keywords
    ALLOWED_STATEMENT_TYPES = {"SELECT", "WITH"}

    @classmethod
    def sanitize_query(cls, sql_query: str) -> str:
        """Strip enclosing markdown codeblocks, comments, and whitespace."""
        if not sql_query:
            return ""

        query = sql_query.strip()
        # Remove markdown code blocks (```sql ... ``` or ``` ...)
        query = re.sub(r"^```(?:sql)?\s*", "", query, flags=re.IGNORECASE)
        query = re.sub(r"\s*```$", "", query)
        query = query.strip()

        # Remove single-line SQL comments (-- ...)
        query = re.sub(r"--.*$", "", query, flags=re.MULTILINE)

        # Remove multi-line SQL comments (/* ... */)
        query = re.sub(r"/\*[\s\S]*?\*/", "", query)

        return query.strip()

    @classmethod
    def validate(cls, sql_query: str) -> Tuple[bool, Optional[str], str]:
        """Validate query for read-only safety and return (is_valid, error_msg, sanitized_query).

        Returns:
            Tuple of:
            - is_valid: True if safe to execute
            - error_message: None if valid, or reason string if rejected
            - sanitized_query: Cleaned SQL query string
        """
        sanitized = cls.sanitize_query(sql_query)

        if not sanitized:
            return False, "Empty query provided.", ""

        # Check for multiple statements (semicolon in middle of query)
        # Semicolon is only allowed at the very end
        statements_split = [s.strip() for s in sanitized.split(";") if s.strip()]
        if len(statements_split) > 1:
            return (
                False,
                "Security violation: Multiple statements detected (stacked query attack prevention).",
                sanitized
            )

        # Remove trailing semicolon for uniform parsing
        normalized_query = statements_split[0]

        # AST-level validation if sqlparse is available
        if SQLPARSE_AVAILABLE:
            parsed = sqlparse.parse(normalized_query)
            if not parsed:
                return False, "Failed to parse SQL syntax.", normalized_query

            stmt = parsed[0]
            stmt_type = stmt.get_type()

            # Must be SELECT or UNKNOWN (for WITH CTE statements)
            first_token = None
            for token in stmt.tokens:
                if not token.is_whitespace and token.value:
                    first_token = token.value.strip().upper()
                    break

            if first_token not in cls.ALLOWED_STATEMENT_TYPES:
                return (
                    False,
                    f"Security violation: Only SELECT and CTE (WITH...SELECT) queries are permitted. Found: '{first_token}'",
                    normalized_query
                )

            # Deep token inspection for disallowed keywords
            for token in stmt.flatten():
                token_val = token.value.strip().upper()
                if token_val in cls.DANGEROUS_KEYWORDS:
                    return (
                        False,
                        f"Security violation: Disallowed keyword '{token_val}' detected in query.",
                        normalized_query
                    )

        else:
            # Fallback regex-based validation
            upper_query = normalized_query.upper()

            # Verify it begins with SELECT or WITH
            if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
                return (
                    False,
                    "Security violation: Query must begin with SELECT or WITH.",
                    normalized_query
                )

            # Word boundary check for dangerous keywords
            for keyword in cls.DANGEROUS_KEYWORDS:
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, upper_query):
                    return (
                        False,
                        f"Security violation: Disallowed keyword '{keyword}' detected.",
                        normalized_query
                    )

        # Enforce reasonable row limit if no LIMIT clause is present
        if "LIMIT" not in normalized_query.upper():
            normalized_query = f"{normalized_query} LIMIT 1000"

        return True, None, normalized_query
