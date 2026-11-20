class ServiceError(Exception):
    """Ожидаемая ошибка бизнес-логики: сообщение можно показать пользователю."""


class CampaignSetupError(ServiceError):
    """В Keitaro нет домена, группы или источника, с которыми создаются кампании."""


class OfferNotFoundError(ServiceError):
    """Оффера нет в Keitaro или он недоступен по нашему ключу."""


class ShareError(ServiceError):
    """Закреплённые доли не позволяют распределить 100% (DISPUTED.md №3)."""


class StreamNotFoundError(ServiceError):
    """Потока нет в редакторе: сначала загрузите потоки кампании (Fetch)."""


class OfferAlreadyInStreamError(ServiceError):
    """Оффер уже привязан к потоку."""


class OfferNotInStreamError(ServiceError):
    """Оффера нет в потоке."""
