"""
Routers Package
"""

# Safe imports - only import if modules exist
try:
    from .keys import router as keys_router
except ImportError:
    keys_router = None

try:
    from .admin import router as admin_router
except ImportError:
    admin_router = None

__all__ = ["keys_router", "admin_router"]
