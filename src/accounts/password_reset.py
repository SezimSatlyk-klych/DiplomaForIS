"""Восстановление пароля: код на почту и одноразовый reset_token."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

from .models import PasswordResetCode

User = get_user_model()

RESEND_SECONDS = int(getattr(settings, 'PASSWORD_RESET_RESEND_SECONDS', 60))
CODE_TTL_SECONDS = int(getattr(settings, 'PASSWORD_RESET_CODE_TTL', 600))
RESET_TOKEN_MAX_AGE = int(getattr(settings, 'PASSWORD_RESET_TOKEN_MAX_AGE', 900))
MAX_VERIFY_ATTEMPTS = 5

_signer = TimestampSigner(salt='accounts.PasswordResetCode')


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def hash_code(email: str, code: str) -> str:
    payload = f'{email}\0{code}\0{settings.SECRET_KEY}'.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def generate_code() -> str:
    return f'{secrets.randbelow(10000):04d}'


def send_reset_email(to_email: str, code: str) -> None:
    subject = getattr(
        settings,
        'PASSWORD_RESET_EMAIL_SUBJECT',
        'CareSteps: код восстановления пароля',
    )
    body = (
        f'Ваш код подтверждения: {code}\n\n'
        f'Код действует несколько минут. Если вы не запрашивали восстановление, '
        f'проигнорируйте это письмо.'
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )


def request_reset_code(email: str) -> tuple[bool, int | None]:
    """
    Отправить новый код (если пользователь есть и не сработал cooldown).

    Returns:
        (success, retry_after_seconds) — при success=False передать retry_after_seconds для UI.
    """
    email = normalize_email(email)
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return True, None

    latest = PasswordResetCode.objects.filter(email=email).order_by('-created_at').first()
    if latest:
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        if elapsed < RESEND_SECONDS:
            wait = max(1, int(RESEND_SECONDS - elapsed))
            return False, wait

    PasswordResetCode.objects.filter(email=email).delete()
    plain = generate_code()
    PasswordResetCode.objects.create(
        email=email,
        code_hash=hash_code(email, plain),
        expires_at=timezone.now() + timezone.timedelta(seconds=CODE_TTL_SECONDS),
        failed_attempts=0,
    )
    send_reset_email(user.email, plain)
    return True, None


def verify_code(email: str, code: str) -> tuple[str | None, str | None]:
    """
    Проверить 4-значный код, выдать подписанный reset_token (на новый пароль).

    Returns:
        (reset_token, error_message)
    """
    email = normalize_email(email)
    code = (code or '').strip()
    if len(code) != 4 or not code.isdigit():
        return None, 'Введите 4-значный код из письма.'

    row = PasswordResetCode.objects.filter(email=email).order_by('-created_at').first()
    if not row or row.expires_at < timezone.now():
        return None, 'Код устарел или не запрашивался. Запросите новый.'

    if row.failed_attempts >= MAX_VERIFY_ATTEMPTS:
        return None, 'Слишком много неверных попыток. Запросите новый код.'

    if not hmac.compare_digest(row.code_hash, hash_code(email, code)):
        row.failed_attempts += 1
        row.save(update_fields=['failed_attempts'])
        return None, 'Неверный код.'

    user = User.objects.filter(email__iexact=email).first()
    row.delete()
    if not user:
        return None, 'Пользователь не найден.'

    token = _signer.sign(str(user.pk))
    return token, None


def reset_password_with_token(token: str, new_password: str) -> tuple[User | None, str | None]:
    """Установить новый пароль по reset_token после успешной проверки кода."""
    try:
        user_id = int(_signer.unsign(token, max_age=RESET_TOKEN_MAX_AGE))
    except SignatureExpired:
        return None, 'Срок действия истёк. Запросите код заново.'
    except BadSignature:
        return None, 'Недействительный токен.'

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None, 'Пользователь не найден.'

    user.set_password(new_password)
    user.save(update_fields=['password'])
    return user, None
