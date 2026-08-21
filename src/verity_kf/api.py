from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Security, status
from fastapi.security import OpenIdConnect
from pydantic import BaseModel, ConfigDict, Field

from verity_kf.authorization import PrincipalContext
from verity_kf.serving import (
    AuthorizedReleaseSummary,
    ConceptEnvelope,
    ConceptNotFound,
    ReleaseNotFound,
    ReleaseWithdrawn,
    SearchResponse,
    ServingError,
    ServingService,
)


class PrincipalResolver(Protocol):
    def __call__(self, request: Request) -> PrincipalContext: ...


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    release: str = Field(min_length=1, description="Immutable sha256 digest or protected channel")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str = "ok"


def create_app(
    service: ServingService,
    principal_resolver: PrincipalResolver,
    *,
    open_id_connect_url: str,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Create an API only when an explicit authenticated-principal resolver is supplied."""

    current_time = clock or (lambda: datetime.now(UTC))
    if not open_id_connect_url.startswith("https://"):
        raise ValueError("open_id_connect_url must use HTTPS")
    oidc = OpenIdConnect(
        openIdConnectUrl=open_id_connect_url,
        scheme_name="EnterpriseOIDC",
        description="Enterprise-issued human or workload bearer token",
    )
    app = FastAPI(
        title="VerityKF Serving API",
        version="1.0.0",
        description=(
            "Release-pinned, deny-by-default retrieval contract. The application must be "
            "constructed with an approved authenticated-principal resolver."
        ),
        docs_url=None,
        redoc_url=None,
    )

    def no_store(response: Response) -> None:
        response.headers["Cache-Control"] = "no-store"

    def resolve_principal(
        request: Request,
        _identity_token: Annotated[str, Security(oidc)],
    ) -> PrincipalContext:
        return principal_resolver(request)

    Principal = Annotated[PrincipalContext, Depends(resolve_principal)]

    @app.get(
        "/healthz",
        operation_id="health",
        response_model=HealthResponse,
        tags=["operations"],
    )
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/v1/releases",
        operation_id="listAuthorizedReleases",
        response_model=list[AuthorizedReleaseSummary],
        tags=["retrieval"],
    )
    def list_releases(principal: Principal, response: Response) -> list[AuthorizedReleaseSummary]:
        no_store(response)
        try:
            return list(service.list_releases(principal, now=current_time()))
        except ServingError as exc:
            raise _safe_http_error(exc) from exc

    @app.post(
        "/v1/search",
        operation_id="searchAuthorizedConcepts",
        response_model=SearchResponse,
        tags=["retrieval"],
    )
    def search(
        body: SearchRequest,
        principal: Principal,
        response: Response,
    ) -> SearchResponse:
        no_store(response)
        try:
            return service.search(
                principal,
                digest_or_channel=body.release,
                query=body.query,
                now=current_time(),
                limit=body.limit,
            )
        except ServingError as exc:
            raise _safe_http_error(exc) from exc

    @app.get(
        "/v1/releases/{digest_or_channel}/concepts/{concept_uid}",
        operation_id="getAuthorizedConcept",
        response_model=ConceptEnvelope,
        tags=["retrieval"],
        responses={
            status.HTTP_404_NOT_FOUND: {"description": "Not found or not authorized"},
            status.HTTP_410_GONE: {"description": "Release withdrawn"},
        },
    )
    def get_concept(
        digest_or_channel: str,
        concept_uid: str,
        principal: Principal,
        response: Response,
    ) -> ConceptEnvelope:
        no_store(response)
        now = current_time()
        if now.tzinfo is None or now.utcoffset() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="serving clock must include an explicit UTC offset",
            )
        try:
            return service.fetch_concept(
                principal,
                digest_or_channel=digest_or_channel,
                concept_uid=concept_uid,
                now=now,
            )
        except ServingError as exc:
            raise _safe_http_error(exc) from exc

    return app


def _safe_http_error(error: ServingError) -> HTTPException:
    if isinstance(error, ReleaseWithdrawn):
        return HTTPException(status_code=status.HTTP_410_GONE, detail="release is withdrawn")
    if isinstance(error, (ConceptNotFound, ReleaseNotFound)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
