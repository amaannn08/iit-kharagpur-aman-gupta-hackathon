"""API route modules."""

from sentinel.api.routes.datasets import router as datasets_router
from sentinel.api.routes.health import router as health_router

__all__ = ["datasets_router", "health_router"]
