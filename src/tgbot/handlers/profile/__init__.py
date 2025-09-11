from aiogram import Router
from .change_email import router as change_email_router

router = Router(name="profile")
router.include_router(change_email_router)

__all__ = ["router"]
