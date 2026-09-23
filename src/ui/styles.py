"""Custom CSS and Aesthetic Design System for SQLGPT."""

CUSTOM_CSS = """
<style>
/* Import modern font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header badge styling */
.sqlgpt-badge {
    display: inline-block;
    padding: 3px 10px;
    margin-right: 6px;
    margin-bottom: 6px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: linear-gradient(135deg, rgba(255, 107, 53, 0.15), rgba(255, 75, 75, 0.15));
    color: #FF6B35;
    border: 1px solid rgba(255, 107, 53, 0.3);
}

.sqlgpt-badge-blue {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(147, 51, 234, 0.15));
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.sqlgpt-badge-green {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

/* Metric Cards */
.metric-card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
    backdrop-filter: blur(8px);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.metric-card:hover {
    border-color: rgba(255, 107, 53, 0.4);
    transform: translateY(-2px);
}

/* Clean sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #0F172A;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

/* Styled SQL Query block header */
.sql-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: #1E293B;
    border-radius: 8px 8px 0 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: #94A3B8;
}

/* Status indicator dot */
.status-dot {
    height: 8px;
    width: 8px;
    background-color: #10B981;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}
</style>
"""
