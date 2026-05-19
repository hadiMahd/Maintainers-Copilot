"""Model server API package."""

from model_server.api.classifier import router as classifier_router

__all__ = ["classifier_router"]