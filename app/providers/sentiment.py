# ============================================================================
# MARKETMIND AI - SENTIMENT ANALYSIS PROVIDER (LOCAL VADER / FALLBACK)
# ============================================================================

import logging
from typing import Dict, Any

logger = logging.getLogger("marketmind_ai")

# Hybrid import logic with custom fallback
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        VADER_AVAILABLE = True
    except ImportError:
        VADER_AVAILABLE = False

# Shared module-level singleton instance for VADER to avoid repetitive initialization overhead.
_vader_analyzer = None
if VADER_AVAILABLE:
    try:
        _vader_analyzer = SentimentIntensityAnalyzer()
        logger.info("Local VADER Sentiment Analyzer singleton initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing VADER analyzer singleton: {e}")
        VADER_AVAILABLE = False


class SentimentProvider:
    """Analyzes text sentiment using VADER Sentiment Analyzer, with a lightweight rule-based fallback."""

    def __init__(self) -> None:
        if VADER_AVAILABLE and _vader_analyzer is not None:
            self.analyzer = _vader_analyzer
        else:
            if not VADER_AVAILABLE:
                logger.warning("VADER Sentiment analyzer not found. Falling back to rule-based financial dictionary analyzer.")
            else:
                logger.warning("VADER Sentiment analyzer singleton was not initialized. Falling back to rule-based financial dictionary analyzer.")
            self.analyzer = None
            # Standard financial lexicon mapping
            self.pos_words = {
                "up", "soar", "gain", "rise", "positive", "growth", "bullish", "profit",
                "beat", "outperform", "success", "strong", "higher", "surge", "increase",
                "buy", "clearance", "upgrade", "approved", "revenue", "earnings", "good",
                "better", "boost", "optimistic", "growth", "high", "positive"
            }
            self.neg_words = {
                "down", "plummet", "loss", "fall", "negative", "decline", "bearish",
                "miss", "underperform", "failure", "weak", "lower", "crash", "decrease",
                "sell", "stale", "downgrade", "failed", "risk", "warning", "deficit", "bad",
                "worse", "drop", "pessimistic", "low", "negative"
            }

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyzes text and returns sentiment score, label, and confidence."""
        if not text:
            return {
                "score": 0.0,
                "label": "neutral",
                "explanation": "Empty text provided.",
                "confidence_score": 1.0
            }

        if self.analyzer:
            # Use real VADER
            scores = self.analyzer.polarity_scores(text)
            compound = scores["compound"]  # -1.0 to 1.0
            
            if compound >= 0.05:
                label = "positive"
            elif compound <= -0.05:
                label = "negative"
            else:
                label = "neutral"
                
            pos = scores.get("pos", 0.0)
            neg = scores.get("neg", 0.0)
            neu = scores.get("neu", 1.0)
            
            confidence = max(pos, neg, neu)
            
            return {
                "score": round(compound, 3),
                "label": label,
                "explanation": f"VADER scores: pos={pos}, neg={neg}, neu={neu}",
                "confidence_score": round(confidence, 3)
            }
        else:
            # Fallback simple dictionary analyzer
            words = text.lower().split()
            pos_count = sum(1 for w in words if w in self.pos_words)
            neg_count = sum(1 for w in words if w in self.neg_words)
            
            total_matches = pos_count + neg_count
            if total_matches == 0:
                score = 0.0
                label = "neutral"
                confidence = 1.0
            else:
                score = (pos_count - neg_count) / total_matches
                if score >= 0.1:
                    label = "positive"
                elif score <= -0.1:
                    label = "negative"
                else:
                    label = "neutral"
                
                # Confidence is match density
                confidence = total_matches / len(words) if len(words) > 0 else 0.5
                confidence = min(max(confidence, 0.5), 0.95)
                
            return {
                "score": round(score, 3),
                "label": label,
                "explanation": f"Rule-based fallback: pos={pos_count}, neg={neg_count}",
                "confidence_score": round(confidence, 3)
            }
