class KeitaroError(Exception):
    """Ошибка Keitaro API. status_code = None, если ответа не было (сеть, таймаут)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(f"Keitaro API error ({status_code}): {message}")
        self.message = message
        self.status_code = status_code
