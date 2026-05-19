"""Model server API package."""

from model_server.api.classifier import router as classifier_router
from model_server.api.issue_analysis import router as issue_analysis_router

__all__ = ["classifier_router", "issue_analysis_router"]
