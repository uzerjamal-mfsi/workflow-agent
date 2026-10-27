"""Application constants: env names, model config, route paths."""

from enum import Enum


class Environment(Enum):
    """Environment names and path constants."""

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class OPENROUTER_CHAT_MODEL(Enum):
    """OpenRouter chat model configuration."""

    MODEL_NAME = "openrouter/auto"
    TEMPERATURE = 0.0


class VECTOR_DB(Enum):
    """Vector database configuration constants."""

    TOP_K = 5
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    LOAD_MODE = "page"
    PAGES_DELIMITER = "\n\n"

    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class ROUTE_CONSTANTS(Enum):
    """API route/path constants shared across the app."""

    API_V1_PREFIX = "/api/v1"
