import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import Settings, get_settings

router = APIRouter(include_in_schema=False)
security = HTTPBasic()


def require_docs_access(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> None:
    valid_username = secrets.compare_digest(
        credentials.username.encode(),
        settings.DOCS_USERNAME.encode(),
    )
    valid_password = secrets.compare_digest(
        credentials.password.encode(),
        settings.DOCS_PASSWORD.encode(),
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid documentation credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/openapi.json", dependencies=[Depends(require_docs_access)])
async def openapi_schema(request: Request) -> JSONResponse:
    return JSONResponse(request.app.openapi())


@router.get(
    "/docs",
    dependencies=[Depends(require_docs_access)],
    response_class=HTMLResponse,
)
async def swagger_documentation() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Online Cinema - Swagger UI",
    )


@router.get(
    "/redoc",
    dependencies=[Depends(require_docs_access)],
    response_class=HTMLResponse,
)
async def redoc_documentation() -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Online Cinema - ReDoc",
    )
