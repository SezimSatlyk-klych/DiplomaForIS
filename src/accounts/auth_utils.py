"""Вспомогательные функции для аутентификации."""

from .models import Specialist, UserProfile


def resolve_user_type(user) -> str:
    """
    Тип аккаунта для маршрутизации после входа.

    Returns:
        parent — есть профиль родителя;
        specialist — есть профиль специалиста;
        both — оба (редко);
        none — только зарегистрирован, профиль ещё не создан.
    """
    has_parent = UserProfile.objects.filter(user_id=user.pk).exists()
    has_specialist = Specialist.objects.filter(user_id=user.pk).exists()
    if has_specialist and has_parent:
        return 'both'
    if has_specialist:
        return 'specialist'
    if has_parent:
        return 'parent'
    return 'none'
