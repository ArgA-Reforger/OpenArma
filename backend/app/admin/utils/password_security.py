from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_user_password_history import user_password_history_dao
from backend.common.exception import errors
from backend.core.conf import settings
from backend.utils.dynamic_config import load_user_security_config
from backend.utils.pattern_validate import is_has_letter, is_has_number, is_has_special_char

password_hash = PasswordHash((BcryptHasher(),))


def get_hash_password(password: str, salt: bytes | None) -> str:
    """
    Hash a password

    :param password: password
    :param salt: salt value
    :return:
    """
    return password_hash.hash(password, salt=salt)


def password_verify(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password

    :param plain_password: password to verify
    :param hashed_password: hashed password
    :return:
    """
    return password_hash.verify(plain_password, hashed_password)


async def validate_new_password(db: AsyncSession, user_id: int, new_password: str) -> None:
    """
    Validate a new password

    :param db: database session
    :param user_id: user ID
    :param new_password: new password
    :return:
    """
    await load_user_security_config(db)

    if len(new_password) < settings.USER_PASSWORD_MIN_LENGTH:
        raise errors.RequestError(msg=f'Password must be at least {settings.USER_PASSWORD_MIN_LENGTH} characters long')

    if len(new_password) > settings.USER_PASSWORD_MAX_LENGTH:
        raise errors.RequestError(msg=f'Password cannot exceed {settings.USER_PASSWORD_MAX_LENGTH} characters')

    if not is_has_number(new_password):
        raise errors.RequestError(msg='Password must contain a number')

    if not is_has_letter(new_password):
        raise errors.RequestError(msg='Password must contain a letter')

    if settings.USER_PASSWORD_REQUIRE_SPECIAL_CHAR and not is_has_special_char(new_password):
        raise errors.RequestError(msg='Password must contain a special character (e.g. !@#$%)')

    password_history = await user_password_history_dao.get_by_user_id(db, user_id)

    for hist in password_history[: settings.USER_PASSWORD_HISTORY_CHECK_COUNT]:
        if password_verify(new_password, hist.password):
            raise errors.RequestError(
                msg=f'New password cannot match any of the last {settings.USER_PASSWORD_HISTORY_CHECK_COUNT} passwords used'
            )
