from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.clients.keitaro import KeitaroError
from app.services.errors import CampaignSetupError, OfferNotFoundError, ServiceError

# От частного к общему: берётся первый подходящий класс.
SERVICE_ERROR_STATUS: list[tuple[type[ServiceError], int]] = [
    (OfferNotFoundError, status.HTTP_404_NOT_FOUND),
    (CampaignSetupError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (ServiceError, status.HTTP_400_BAD_REQUEST),
]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error(_: Request, exc: ServiceError) -> JSONResponse:
        code = next(code for cls, code in SERVICE_ERROR_STATUS if isinstance(exc, cls))
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    @app.exception_handler(KeitaroError)
    async def keitaro_error(_: Request, exc: KeitaroError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": str(exc)})
