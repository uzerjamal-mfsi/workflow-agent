"""FastAPI application factory."""

import os

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.env_config import settings
from app.config.log_config import logger
from app.constants.app_constants import ROUTE_CONSTANTS
from app.exceptions import AppError
from app.exceptions.handlers import (
    app_error_handler,
    global_exception_handler,
    http_exception_handler,
    request_validation_handler,
)
from app.health import router as health_router
from app.routes.core_routes.router import router as core_router


def start_application():
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance with middleware, routers, and exception handlers.
    """
    logger.info("Starting application...")
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=settings.PROJECT_DESCRIPTION,
        root_path=settings.BASE_PATH,
    )

    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # EXCEPTION HANDLERS
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # CORS MIDDLEWARE
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ROUTERS
    app.include_router(health_router)
    api_v1 = APIRouter(prefix=ROUTE_CONSTANTS.API_V1_PREFIX.value)
    api_v1.include_router(core_router)
    app.include_router(api_v1)

    logger.info("Application started successfully")

    return app
