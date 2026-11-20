class ServiceError(Exception):
    """Ожидаемая ошибка бизнес-логики: сообщение можно показать пользователю."""


class StateConflictError(ServiceError):
    """Действие не подходит текущему состоянию потока или оффера (API: 409)."""


class CampaignSetupError(ServiceError):
    """В Keitaro нет домена, группы или источника, с которыми создаются кампании."""


class OfferNotFoundError(ServiceError):
    """Оффера нет в Keitaro или он недоступен по нашему ключу."""


class ShareError(ServiceError):
    """Закреплённые доли не позволяют распределить 100% (DISPUTED.md №3)."""


class StreamNotFoundError(ServiceError):
    """Потока нет в редакторе: сначала загрузите потоки кампании (Fetch)."""


class OfferAlreadyInStreamError(StateConflictError):
    """Оффер уже привязан к потоку."""


class OfferNotInStreamError(ServiceError):
    """Оффера нет в потоке."""


class OfferStateError(StateConflictError):
    """Оффер есть в потоке, но его статус не позволяет действие (удалить удалённый и т.п.)."""


class StreamChangedInKeitaroError(StateConflictError):
    """Поток изменён в Keitaro после нашего Fetch: Push затёр бы чужие изменения."""


class NoConflictError(StateConflictError):
    """У оффера нет конфликта с Keitaro — решать нечего."""


class ConflictsPendingError(StateConflictError):
    """Есть нерешённые конфликты с Keitaro: Push заблокирован (DISPUTED.md №8)."""
