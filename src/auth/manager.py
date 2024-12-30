from typing import Optional, Dict, Any

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin

from src.DB_config import SECRET_KEY
from src.auth.models import User
from src.auth.utils import get_user_db

SECRET = SECRET_KEY


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
