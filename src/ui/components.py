"""Streamlit UI Components for SQLGPT.

Provides reusable presentation components for headers, model & database controls,
schema browser, message bubbles, SQL preview, and interactive Plotly chart views.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from src.llm.models import GROQ_MODELS, DEFAULT_MODEL_ID
from src.llm.viz_engine import VisualizationEngine


def render_header():
    """Render the application header with branding and tech stack badges."""
    st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #FF6B35 0%, #FFA07A 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    SQLGPT
                </h1>
                <span style="font-size: 1.1rem; color: #94A3B8; font-weight: 500;">— Natural Language SQL Assistant</span>
            </div>
        </div>
        <div style="margin-bottom: 20px;">
            <span class="sqlgpt-badge">⚡ Generative AI</span>
            <span class="sqlgpt-badge">🚀 Groq Llama 3.3 & Fallbacks</span>
            <span class="sqlgpt-badge-blue">🔗 LangChain Orchestration</span>
            <span class="sqlgpt-badge-green">🔒 Read-Only & AST Protected</span>
            <span class="sqlgpt-badge-blue">📊 Auto Plotly Visualizations</span>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar_config(current_model_id: Optional[str] = None):
    """Render sidebar configuration for Groq API Key and Model Selection."""
    st.sidebar.header("⚙️ Configuration")

    # API Key Input
    api_key = st.sidebar.text_input(
        "🔑 Groq API Key",
        type="password",
        value=st.session_state.get("groq_api_key", ""),
        help="Get a free ultra-fast Groq API key at console.groq.com"
    )
    if api_key:
        st.session_state["groq_api_key"] = api_key

    # Model Selection with status & fallback details
    st.sidebar.subheader("🤖 AI Model Orchestration")
    model_choices = list(GROQ_MODELS.keys())
    model_labels = {k: f"{v['name']} ({'Recommended' if v['is_default'] else v['role'].title()})" for k, v in GROQ_MODELS.items()}

    selected_model_id = st.sidebar.selectbox(
        "Primary LLM",
        model_choices,
        format_func=lambda x: model_labels.get(x, x),
        index=0
    )

    model_meta = GROQ_MODELS[selected_model_id]
    st.sidebar.caption(f"ℹ️ {model_meta['description']}")

    # Display fallback mechanism status
    with st.sidebar.expander("🛡️ Automatic Fallback Pipeline", expanded=False):
        st.markdown("""
        **Cascading Reliability:**
        1. **Primary**: `Llama 3.3 70B` (Complex SQL reasoning)
        2. **Fast Fallback**: `Llama 3.1 8B` (Instant backup on 429/rate-limit)
        3. **Backup**: `Mixtral 8x7B` & `Gemma 2` (Large context & backup)
        """)

    return api_key, selected_model_id


def render_schema_explorer(schema_info: Dict[str, Any]):
    """Render an interactive schema explorer in the sidebar."""
    if not schema_info:
        st.sidebar.info("Connect a database to view tables and schema.")
        return

    st.sidebar.subheader("🗄️ Database Schema")
    st.sidebar.caption(f"{len(schema_info)} tables available")

    # Search filter for tables
    search_query = st.sidebar.text_input("🔍 Filter tables/columns", "").lower()

    for table_name, info in schema_info.items():
        columns = info.get("columns", [])
        col_names = [col[0] for col in columns]

        # Filter check
        if search_query and (search_query not in table_name.lower() and not any(search_query in c.lower() for c in col_names)):
            continue

        with st.sidebar.expander(f"📁 {table_name} ({len(columns)} cols)"):
            st.markdown("**Columns:**")
            for col_name, col_type in columns:
                st.markdown(f"• `{col_name}` <span style='color: #94A3B8; font-size: 0.8rem;'>({col_type})</span>", unsafe_allow_html=True)

            fks = info.get("foreign_keys", [])
            if fks:
                st.markdown("**Relations:**")
                for fk in fks:
                    ref_tbl = fk.get("referred_table", "")
                    st.markdown(f"🔗 `{fk.get('constrained_columns')}` $\\rightarrow$ `{ref_tbl}`")


def render_example_queries():
    """Render clickable prompt chips for rapid testing."""
    st.markdown("##### 💡 Suggested Questions")
    example_prompts = [
        "Show the top 5 customers by total order spend",
        "Create a bar chart of product inventory by category",
        "What is the average employee salary by department?",
        "Show monthly sales revenue trend over time as a line chart",
        "Which products have stock lower than 50 units?",
        "Plot a pie chart showing distribution of orders by country"
    ]

    cols = st.columns(3)
    for idx, prompt in enumerate(example_prompts):
        with cols[idx % 3]:
            if st.button(f"✨ {prompt}", key=f"ex_btn_{idx}", use_container_width=True):
                st.session_state["submitted_prompt"] = prompt


def render_query_result_card(entry: Dict[str, Any], viz_engine: VisualizationEngine):
    """Render a comprehensive, multi-section query result card."""
    # Section 1: Executive Summary
    if entry.get("summary"):
        st.markdown(f"### 💡 Answer\n{entry['summary']}")

    # Section 2: Generated SQL Query (Syntax highlighted + expandable)
    sql_query = entry.get("sql_query")
    if sql_query:
        with st.expander("💻 View Generated SQL Query", expanded=False):
            st.code(sql_query, language="sql")

    # Section 3: Data Table & Metrics
    df = entry.get("dataframe")
    if df is not None and not df.empty:
        col_m1, col_m2, col_m3 = st.columns([1, 1, 2])
        col_m1.metric("Rows Returned", f"{len(df):,}")
        col_m2.metric("Columns", len(df.columns))

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download CSV / JSON
        c1, c2, _ = st.columns([1, 1, 2])
        csv_data = df.to_csv(index=False).encode("utf-8")
        c1.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name="sqlgpt_query_results.csv",
            mime="text/csv"
        )
        json_data = df.to_json(orient="records", indent=2).encode("utf-8")
        c2.download_button(
            label="⬇️ Download JSON",
            data=json_data,
            file_name="sqlgpt_query_results.json",
            mime="application/json"
        )

        # Section 4: Data Visualization
        query_text = entry.get("user_query", "")
        viz_requested = viz_engine.is_visualization_requested(query_text)
        chart_rec = viz_engine.auto_recommend_chart(df, query_text)

        if viz_requested or chart_rec:
            st.markdown("### 📊 Interactive Visualization")

            # Allow interactive override or fine-tuning
            with st.expander("⚙️ Customize Chart", expanded=False):
                chart_types = ["bar", "line", "pie", "scatter", "histogram", "area", "box"]
                default_type_idx = chart_types.index(chart_rec["type"]) if (chart_rec and chart_rec["type"] in chart_types) else 0

                v_col1, v_col2, v_col3 = st.columns(3)
                chosen_chart = v_col1.selectbox("Chart Type", chart_types, index=default_type_idx, key=f"viz_type_{entry.get('id')}")

                all_cols = df.columns.tolist()
                default_x = chart_rec.get("x") if chart_rec else all_cols[0]
                default_x_idx = all_cols.index(default_x) if default_x in all_cols else 0
                chosen_x = v_col2.selectbox("X-Axis / Category", all_cols, index=default_x_idx, key=f"viz_x_{entry.get('id')}")

                num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                num_options = ["None"] + num_cols if chosen_chart in ["histogram", "pie"] else (num_cols if num_cols else all_cols)
                default_y = chart_rec.get("y") if chart_rec else (num_options[0] if num_options else None)
                default_y_idx = num_options.index(default_y) if (default_y and default_y in num_options) else 0
                chosen_y_raw = v_col3.selectbox("Y-Axis / Metric", num_options, index=default_y_idx, key=f"viz_y_{entry.get('id')}")
                chosen_y = None if chosen_y_raw == "None" else chosen_y_raw

            # Render Plotly Figure
            active_type = chosen_chart if "chosen_chart" in locals() else (chart_rec["type"] if chart_rec else "bar")
            active_x = chosen_x if "chosen_x" in locals() else (chart_rec["x"] if chart_rec else df.columns[0])
            active_y = chosen_y if "chosen_y" in locals() else (chart_rec.get("y") if chart_rec else None)

            fig = viz_engine.create_figure(df, active_type, active_x, active_y, title=f"{active_type.title()} View: {query_text[:50]}")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
