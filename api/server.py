"""HTTP Chat API Server for SupportBot AI.

Provides a lightweight, robust, multi-tenant HTTP endpoint for the
embeddable JavaScript widget (`embed.js`) and external client applications.
"""

import json
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Mount, Route
from starlette.staticfiles import StaticFiles

from api.schemas import ChatApiRequest, ChatApiResponse, ErrorResponse, HealthResponse
from core.config import get_config
from core.database import DatabaseManager
from services.chatbot_service import ChatbotService, chatbot_service


class ChatApiHandler:
    """Encapsulated handler for chat API endpoints with dependency injection support."""

    def __init__(
        self,
        service: Optional[ChatbotService] = None,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.service = service or chatbot_service
        self.db = db_manager or DatabaseManager()

    async def handle_chat(self, request: Request) -> JSONResponse:
        """Handle incoming chat messages from widget or external websites."""
        # 1. Parse JSON body
        try:
            body = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return JSONResponse(
                ErrorResponse(
                    error="Malformed JSON body",
                    detail="Request body must be valid JSON.",
                ).model_dump(),
                status_code=400,
            )

        if not isinstance(body, dict):
            return JSONResponse(
                ErrorResponse(
                    error="Invalid JSON structure",
                    detail="Request body must be a JSON object.",
                ).model_dump(),
                status_code=400,
            )

        # 2. Validate payload schema with Pydantic
        try:
            chat_req = ChatApiRequest.model_validate(body)
        except ValidationError as exc:
            field_errors = []
            for err in exc.errors():
                loc = " -> ".join(str(l) for l in err.get("loc", []))
                field_errors.append(f"{loc}: {err.get('msg')}")
            return JSONResponse(
                ErrorResponse(
                    error="Invalid request payload",
                    detail="; ".join(field_errors),
                ).model_dump(),
                status_code=400,
            )

        # 3. Validate tenant existence in database
        business = self.db.get_business(chat_req.business_id)
        if not business:
            return JSONResponse(
                ErrorResponse(
                    error="Business Not Found",
                    detail=f"Business '{chat_req.business_id}' is not registered.",
                ).model_dump(),
                status_code=404,
            )

        # 4. Dispatch to ChatbotService / RAG Pipeline
        try:
            rag_response = self.service.answer(
                business_id=chat_req.business_id,
                session_id=chat_req.session_id,
                question=chat_req.message,
            )
        except Exception:
            # Internal server error without leaking stack traces or internal secrets
            return JSONResponse(
                ErrorResponse(
                    error="Internal Server Error",
                    detail="An unexpected error occurred while processing your request.",
                ).model_dump(),
                status_code=500,
            )

        # 5. Return sanitized response
        api_response = ChatApiResponse(
            answer=rag_response.answer,
            business_id=rag_response.business_id,
            session_id=rag_response.session_id,
            fallback_triggered=rag_response.fallback_triggered,
        )
        return JSONResponse(api_response.model_dump(), status_code=200)

    async def handle_health(self, request: Request) -> JSONResponse:
        """Handle health check probes."""
        return JSONResponse(HealthResponse().model_dump(), status_code=200)


def create_app(
    cors_origins: Optional[List[str]] = None,
    service: Optional[ChatbotService] = None,
    db_manager: Optional[DatabaseManager] = None,
) -> Starlette:
    """Application factory constructing the Starlette ASGI application with CORS and routing.

    Args:
        cors_origins: Optional list of allowed origins for CORS.
        service: Optional ChatbotService dependency injection.
        db_manager: Optional DatabaseManager dependency injection.

    Returns:
        Configured Starlette application instance.
    """
    cfg = get_config()
    allowed_origins = cors_origins or cfg.cors_allowed_origins or ["*"]

    handler = ChatApiHandler(service=service, db_manager=db_manager)

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=False,
        )
    ]

    routes: List[BaseRoute] = [
        Route("/api/chat", handler.handle_chat, methods=["POST"]),
        Route("/api/health", handler.handle_health, methods=["GET"]),
        Route("/health", handler.handle_health, methods=["GET"]),
    ]

    # Mount widget directory for serving embed.js and storefront demos
    widget_dir = Path(__file__).resolve().parent.parent / "widget"
    if widget_dir.is_dir():
        routes.append(
            Mount("/widget", StaticFiles(directory=str(widget_dir), html=True), name="widget")
        )

    return Starlette(debug=cfg.debug, routes=routes, middleware=middleware)


# Default application instance for Uvicorn: `uvicorn api.server:app`
app = create_app()
