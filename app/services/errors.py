class ServiceError(Exception):
    """Ожидаемая ошибка бизнес-логики: сообщение можно показать пользователю."""


class CampaignSetupError(ServiceError):
    """В Keitaro нет домена, группы или источника, с которыми создаются кампании."""


class OfferNotFoundError(ServiceError):
    """Оффера нет в Keitaro или он недоступен по нашему ключу."""


class ShareError(ServiceError):
    """Закреплённые доли не позволяют распределить 100% (DISPUTED.md №3)."""
