# ============================================================================
# MARKETMIND AI - RESEARCH PROMPT BUILDER
# ============================================================================

from typing import Dict, Any, List


class ResearchPromptBuilder:
    """Constructs prompts for NVIDIA LLM report generation."""

    @staticmethod
    def build_prompts(
        symbol: str,
        profile: Dict[str, Any],
        fundamentals: List[Dict[str, Any]],
        news: List[Dict[str, Any]],
        sentiment: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Constructs system and user prompts with structured inputs."""
        
        # 1. Format Stock Profile
        profile_str = (
            f"Company Name: {profile.get('name', 'N/A')}\n"
            f"Ticker: {symbol}\n"
            f"Sector: {profile.get('sector', 'N/A')}\n"
            f"Industry: {profile.get('industry', 'N/A')}\n"
            f"CEO: {profile.get('ceo', 'N/A')}\n"
            f"Headquarters: {profile.get('headquarters', 'N/A')}\n"
            f"Founded Year: {profile.get('founded_year', 'N/A')}\n"
            f"Description: {profile.get('description', 'N/A')}\n"
            f"Market Cap: {profile.get('market_cap', 'N/A')}\n"
            f"Shares Outstanding: {profile.get('shares_outstanding', 'N/A')}\n"
            f"Current Market Price: ${profile.get('current_price', 'N/A')}\n"
        )

        # 2. Format Fundamentals
        fundamentals_str = ""
        for item in fundamentals:
            fundamentals_str += (
                f"- Period: {item.get('period_type', 'N/A')} | Date: {item.get('report_date', 'N/A')}\n"
                f"  Revenue: {item.get('revenue', 'N/A')} | Net Income: {item.get('net_income', 'N/A')}\n"
                f"  EPS: {item.get('eps', 'N/A')} | EBITDA: {item.get('ebitda', 'N/A')}\n"
                f"  Assets: {item.get('assets', 'N/A')} | Liabilities: {item.get('liabilities', 'N/A')}\n"
                f"  Cash Flow: {item.get('cash_flow', 'N/A')}\n"
            )
        if not fundamentals_str:
            fundamentals_str = "No fundamentals data available.\n"

        # 3. Format News Articles
        news_str = ""
        for idx, item in enumerate(news[:15]):  # Limit to top 15 news for context limits
            news_str += (
                f"{idx + 1}. Title: {item.get('title', 'N/A')}\n"
                f"   Source: {item.get('source_name', 'N/A')} | Date: {item.get('published_at', 'N/A')}\n"
                f"   Summary: {item.get('summary', 'N/A')}\n"
            )
        if not news_str:
            news_str = "No news articles available.\n"

        # 4. Format Sentiment Results
        sentiment_str = (
            f"Overall Sentiment Score: {sentiment.get('overall_score', '0.0')} (-1.0 to +1.0)\n"
            f"Overall Sentiment Label: {sentiment.get('overall_label', 'neutral')}\n"
            f"Article-level sentiments:\n"
        )
        for idx, art in enumerate(sentiment.get('articles', [])[:15]):
            sentiment_str += (
                f"- Article {idx + 1}: {art.get('title', 'N/A')}\n"
                f"  Score: {art.get('sentiment_score', '0.0')} | Label: {art.get('sentiment_label', 'neutral')}\n"
            )

        system_message = (
            "You are an expert Wall Street institutional equity research analyst. Your task is to write a highly professional, "
            "detailed, and objective stock research report based on the provided company profile, financial fundamentals, "
            "news history, and news sentiments. Your report must contain insightful, data-driven analysis and be structured strictly in JSON format."
        )

        user_message = (
            f"Analyze the following data for stock {symbol} and generate an institutional-grade research report.\n\n"
            f"=== STOCK PROFILE ===\n{profile_str}\n"
            f"=== FUNDAMENTALS ===\n{fundamentals_str}\n"
            f"=== NEWS ARTICLES ===\n{news_str}\n"
            f"=== NEWS SENTIMENT ===\n{sentiment_str}\n\n"
            "Return the research report as a valid JSON object with the following keys:\n"
            "{\n"
            "  \"title\": \"Title of the Research Report\",\n"
            "  \"executive_summary\": \"Provide a comprehensive executive summary of the investment findings (minimum 2-3 paragraphs). You MUST explicitly mention the current market price of the stock and calculate the upside or downside percentage of your target price relative to the current market price.\",\n"
            "  \"bull_case\": \"Detailed bullish thesis for the stock.\",\n"
            "  \"bear_case\": \"Detailed bearish thesis for the stock.\",\n"
            "  \"key_risks\": \"Highlight 3-4 major operational, regulatory, or market risks for this company.\",\n"
            "  \"financial_highlights\": \"Summarize key fundamental highlights, revenue growth trends, debt structure, or cash flows.\",\n"
            "  \"sentiment_summary\": \"Analyze recent news headlines and overall sentiment trends.\",\n"
            "  \"investment_thesis\": \"Conclude with the overall investment thesis and rating logic.\",\n"
            "  \"rating\": \"Bullish\",\n"
            "  \"target_price\": 0.00\n"
            "}\n"
            "Note: The rating and target_price values in the template above are placeholders. You must replace 'rating' with exactly one of: Bullish, Neutral, Bearish based on your logic, and replace 'target_price' with your dynamically calculated 12-month target price as a float. Do not output 195.50 or the placeholder values.\n"
            "Important: When referencing facts, news articles, or sentiment trends, you MUST cite your sources using inline bracketed numbers corresponding to the numbered list in the === NEWS ARTICLES === section (e.g. [1], [2]). Use these citations throughout the executive summary, bull case, bear case, and sentiment summary to provide verifiable evidence.\n"
            "Do NOT wrap the output in markdown code blocks like ```json or anything else. Output only raw JSON."
        )

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
