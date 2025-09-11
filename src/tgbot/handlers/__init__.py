from .start import router as start_router
from .info import router as info_router
from .menu import router as menu_router
from .admin import router as admin_router
from .profile import router as profile_router

all_routers = (
    start_router,
    info_router,
    menu_router,
    admin_router,
    profile_router,
)

__all__ = ["all_routers"]
