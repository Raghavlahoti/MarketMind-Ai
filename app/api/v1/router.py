# ============================================================================
# MARKETMIND AI - API ROUTER v1 BINDINGS
# ============================================================================

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.reports import router as reports_router
from app.api.v1.news import router as news_router
from app.api.v1.sentiment import router as sentiment_router
from app.api.v1.search import router as search_router
from app.api.v1.watchlists import router as watchlists_router
from app.api.v1.alerts import router as alerts_router

api_router = APIRouter()

# Register sub-routes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])
api_router.include_router(reports_router, prefix="/research", tags=["Research"])
api_router.include_router(news_router, prefix="/news", tags=["News"])
api_router.include_router(sentiment_router, prefix="/sentiment", tags=["Sentiment"])
api_router.include_router(search_router, prefix="/search", tags=["AI Search"])
api_router.include_router(watchlists_router, prefix="/watchlists", tags=["Watchlists"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
