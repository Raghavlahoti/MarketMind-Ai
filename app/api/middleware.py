# ============================================================================
# MARKETMIND AI - API MIDDLEWARE STRUCTURE
# ============================================================================

import time
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Logs incoming request paths, IP addresses, and response status codes,
    injecting a tracking Request ID.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        # Log incoming
        logger.info(
            f"Incoming Request: {request.method} {request.url.path} (RID: {request_id}, IP: {request.client.host if request.client else 'unknown'})"
        )

        try:
            response: Response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"

            # Log outgoing
            logger.info(
                f"Completed Request: {request.method} {request.url.path} - {response.status_code} (RID: {request_id}, Duration: {process_time:.4f}s)"
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request Exception: {request.method} {request.url.path} - Failed (RID: {request_id}, Duration: {process_time:.4f}s, Error: {e})"
            )
            raise


def setup_middlewares(app: FastAPI) -> None:
    """Configures CORS and adds custom logging middlewares to the app instance."""
    from fastapi.middleware.cors import CORSMiddleware

    # CORS configurations
    from app.core.config import settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logger
    app.add_middleware(RequestLogMiddleware)
