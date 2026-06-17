# ============================================================================
# MARKETMIND AI - RESEARCH AGENT INTERFACE DEFINITIONS
# ============================================================================

from typing import Any, Dict, List
from uuid import UUID


class ResearchAgentInterface:
    """Agentic workflow interface coordinating multi-stage LLM financial research."""

    async def run_sentiment_extraction(self, text_content: str, stock_ticker: str) -> Dict[str, Any]:
        """Extracts sentiment score and keywords from news articles or transcripts."""
        raise NotImplementedError

    async def synthesize_research_report(
        self,
        stock_metadata: Dict[str, Any],
        historical_prices: List[Dict[str, Any]],
        financial_statements: List[Dict[str, Any]],
        context_snippets: List[str]
    ) -> Dict[str, Any]:
        """Orchestrates LLM prompts to draft executive summaries, bull/bear cases, and targets."""
        raise NotImplementedError
