from aiogram import Router
from .root import router as root_router, send_main_menu
from .courses import router as courses_router
from .payment import router as pay_router
from .pay_sections import router as pay_sections_router

router = Router(name="menu")
router.include_router(root_router)
router.include_router(courses_router)
router.include_router(pay_router)
router.include_router(pay_sections_router)

routers = (root_router, courses_router, pay_router, pay_sections_router)

__all__ = ["router", "routers", "send_main_menu"]
