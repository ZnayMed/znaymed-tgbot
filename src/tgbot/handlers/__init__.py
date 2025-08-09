from .start import router as start_router
from .courses import router as courses_router
from .info import router as info_router

all_routers = (start_router, courses_router, info_router)
