"""Intelligent Data Visualization Engine for SQLGPT.

Analyzes dataframes and query intent to automatically generate optimal, interactive
Plotly visualizations (bar, line, pie, scatter, histogram, area, box charts).
"""

from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re


VIZ_KEYWORDS = [
    "chart", "graph", "plot", "visualize", "visualization", "show chart",
    "bar chart", "pie chart", "line chart", "scatter plot", "histogram",
    "trend", "distribution", "breakdown", "compare", "draw"
]


class VisualizationEngine:
    """Detects visual intent and constructs beautiful, interactive Plotly figures."""

    @staticmethod
    def is_visualization_requested(query: str) -> bool:
        """Check if user prompt mentions visual intent or chart requests."""
        if not query:
            return False
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in VIZ_KEYWORDS)

    @classmethod
    def auto_recommend_chart(cls, df: pd.DataFrame, query: str = "") -> Optional[Dict[str, Any]]:
        """Intelligently recommend the best chart configuration based on data shape and query."""
        if df is None or df.empty or len(df.columns) < 1:
            return None

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        datetime_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower() or "year" in c.lower()]
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        # Check for explicit chart requests in query
        query_lower = query.lower() if query else ""

        # Case 1: Line / Trend chart (dates present or 'trend' in query)
        if (datetime_cols or "trend" in query_lower or "over time" in query_lower or "line" in query_lower) and numeric_cols:
            x_col = datetime_cols[0] if datetime_cols else (categorical_cols[0] if categorical_cols else numeric_cols[0])
            y_col = numeric_cols[0] if numeric_cols[0] != x_col else (numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0])
            return {
                "type": "line",
                "x": x_col,
                "y": y_col,
                "title": f"{y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}",
                "confidence": 0.95
            }

        # Case 2: Pie chart (distribution / share / proportions or <= 8 categories)
        if ("pie" in query_lower or "share" in query_lower or "proportion" in query_lower) and categorical_cols:
            cat_col = categorical_cols[0]
            val_col = numeric_cols[0] if numeric_cols else None
            return {
                "type": "pie",
                "x": cat_col,
                "y": val_col,
                "title": f"Distribution by {cat_col.replace('_', ' ').title()}",
                "confidence": 0.9
            }

        # Case 3: Bar chart (comparison across categories)
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            return {
                "type": "bar",
                "x": cat_col,
                "y": num_col,
                "title": f"{num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                "confidence": 0.9
            }

        # Case 4: Scatter plot (2 numeric columns and relationship asked)
        if len(numeric_cols) >= 2 and ("scatter" in query_lower or "relationship" in query_lower or "correlation" in query_lower):
            return {
                "type": "scatter",
                "x": numeric_cols[0],
                "y": numeric_cols[1],
                "title": f"{numeric_cols[1].replace('_', ' ').title()} vs {numeric_cols[0].replace('_', ' ').title()}",
                "confidence": 0.85
            }

        # Case 5: Single numeric column -> Histogram
        if len(numeric_cols) == 1 and not categorical_cols:
            return {
                "type": "histogram",
                "x": numeric_cols[0],
                "y": None,
                "title": f"Distribution of {numeric_cols[0].replace('_', ' ').title()}",
                "confidence": 0.8
            }

        # Default fallback to first two columns
        if len(df.columns) >= 2:
            return {
                "type": "bar",
                "x": df.columns[0],
                "y": df.columns[1],
                "title": f"{df.columns[1]} by {df.columns[0]}",
                "confidence": 0.7
            }

        return None

    @classmethod
    def create_figure(cls, df: pd.DataFrame, chart_type: str, x_col: str,
                      y_col: Optional[str] = None, title: Optional[str] = None,
                      color_col: Optional[str] = None) -> Optional[go.Figure]:
        """Construct an interactive Plotly figure with modern styling."""
        if df is None or df.empty:
            return None

        # Clean title
        display_title = title or f"{chart_type.title()} Chart"

        # Modern unified layout styling
        layout_theme = dict(
            template="plotly_dark",
            title=dict(text=f"<b>{display_title}</b>", font=dict(size=16)),
            margin=dict(l=40, r=40, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(bgcolor="#1E293B", font_size=13),
            font=dict(family="Inter, system-ui, sans-serif")
        )

        try:
            if chart_type == "bar":
                if y_col and y_col in df.columns:
                    fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                                 color_discrete_sequence=px.colors.qualitative.Prism,
                                 title=display_title)
                else:
                    counts = df[x_col].value_counts().reset_index()
                    counts.columns = [x_col, "count"]
                    fig = px.bar(counts, x=x_col, y="count",
                                 color_discrete_sequence=px.colors.qualitative.Prism,
                                 title=display_title)

            elif chart_type == "line":
                fig = px.line(df, x=x_col, y=y_col, color=color_col,
                              markers=True,
                              color_discrete_sequence=px.colors.qualitative.Plotly,
                              title=display_title)

            elif chart_type == "scatter":
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                                 size=numeric_cols[0] if (numeric_cols := df.select_dtypes(include=['number']).columns.tolist()) else None,
                                 color_discrete_sequence=px.colors.qualitative.Vivid,
                                 title=display_title)

            elif chart_type == "pie":
                if y_col and y_col in df.columns:
                    fig = px.pie(df, names=x_col, values=y_col,
                                 color_discrete_sequence=px.colors.qualitative.Safe,
                                 title=display_title, hole=0.35)
                else:
                    counts = df[x_col].value_counts().reset_index()
                    counts.columns = [x_col, "count"]
                    fig = px.pie(counts, names=x_col, values="count",
                                 color_discrete_sequence=px.colors.qualitative.Safe,
                                 title=display_title, hole=0.35)

            elif chart_type == "histogram":
                fig = px.histogram(df, x=x_col,
                                   color_discrete_sequence=px.colors.qualitative.Pastel,
                                   title=display_title)

            elif chart_type == "area":
                fig = px.area(df, x=x_col, y=y_col,
                              color_discrete_sequence=px.colors.qualitative.Set2,
                              title=display_title)

            elif chart_type == "box":
                fig = px.box(df, x=x_col, y=y_col,
                             color_discrete_sequence=px.colors.qualitative.Bold,
                             title=display_title)
            else:
                return None

            fig.update_layout(**layout_theme)
            return fig

        except Exception as e:
            print(f"Visualization generation error: {str(e)}")
            return None
