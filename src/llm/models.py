"""Groq Model Registry and Runtime Fallback Management for SQLGPT.

Configures primary, fast, and backup Groq LLM models and provides
automatic fallback chains for high reliability against rate limits (HTTP 429)
or service disruptions.
"""

from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq


# Catalog of Groq models supported by SQLGPT
GROQ_MODELS: Dict[str, Dict[str, Any]] = {
    "llama-3.3-70b-versatile": {
        "name": "Llama 3.3 70B Versatile",
        "description": "Primary model: State-of-the-art reasoning, optimal for complex SQL and analytical queries.",
        "context_length": 128000,
        "is_default": True,
        "role": "primary"
    },
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B Instant",
        "description": "Fast fallback: Ultra-low latency, ideal for high throughput and straightforward queries.",
        "context_length": 128000,
        "is_default": False,
        "role": "fast_fallback"
    },
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B MoE",
        "description": "Backup model: High context capacity with balanced reasoning efficiency.",
        "context_length": 32768,
        "is_default": False,
        "role": "backup"
    },
    "gemma2-9b-it": {
        "name": "Gemma 2 9B IT",
        "description": "Alternative instruction-tuned model by Google on Groq hardware.",
        "context_length": 8192,
        "is_default": False,
        "role": "alternative"
    }
}

DEFAULT_MODEL_ID = "llama-3.3-70b-versatile"
FALLBACK_ORDER = ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]


def build_groq_llm(api_key: str, model_name: str, temperature: float = 0.0) -> ChatGroq:
    """Instantiate a single ChatGroq LLM instance."""
    return ChatGroq(
        groq_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        streaming=True,
        max_retries=2
    )


def get_groq_llm_with_fallbacks(api_key: str, preferred_model: Optional[str] = None,
                                temperature: float = 0.0) -> Any:
    """Construct an LCEL Runnable with automatic runtime fallbacks across Groq models.

    If the primary model hits a rate limit (429) or transient error,
    LangChain automatically executes the request using the next fallback model.
    """
    primary_id = preferred_model if preferred_model in GROQ_MODELS else DEFAULT_MODEL_ID
    primary_llm = build_groq_llm(api_key, primary_id, temperature=temperature)

    # Build list of backup models excluding the primary
    backup_ids = [m for m in [DEFAULT_MODEL_ID] + FALLBACK_ORDER if m != primary_id]
    fallback_llms = [build_groq_llm(api_key, m_id, temperature=temperature) for m_id in backup_ids]

    # Bind fallbacks in LangChain LCEL
    return primary_llm.with_fallbacks(fallback_llms)
