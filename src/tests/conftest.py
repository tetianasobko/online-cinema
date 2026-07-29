from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    CertificationModel,
    DirectorModel,
    GenreModel,
    MovieModel,
    StarModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from database.populate import seed_user_groups
from database.session import get_db
from main import app
from notifications import get_email_sender
from security.token_manager import JWTAuthManager
from config import get_settings
from tests.doubles.stubs import StubEmailSender


test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "functional: Functional tests")


@pytest_asyncio.fixture(autouse=True)
async def reset_test_database() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def email_sender_stub() -> StubEmailSender:
    return StubEmailSender()


@pytest_asyncio.fixture
async def client(
    email_sender_stub: StubEmailSender,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: email_sender_stub

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_user_groups(
    db_session: AsyncSession,
) -> AsyncSession:
    await seed_user_groups(db_session)
    return db_session


@pytest_asyncio.fixture
async def seeded_movies(
    db_session: AsyncSession,
) -> list[MovieModel]:
    certification = CertificationModel(name="PG-13")
    drama = GenreModel(name="Drama")
    action = GenreModel(name="Action")
    director_one = DirectorModel(name="First Director")
    director_two = DirectorModel(name="Second Director")
    actor_one = StarModel(name="Alice Actor")
    actor_two = StarModel(name="Bob Actor")

    movies = [
        MovieModel(
            name="Alpha Journey",
            year=2020,
            time=110,
            imdb=8.1,
            votes=900,
            description="A hopeful journey across the world.",
            price=Decimal("5.99"),
            certification=certification,
            genres=[drama],
            directors=[director_one],
            stars=[actor_one],
        ),
        MovieModel(
            name="Beta Mission",
            year=2022,
            time=125,
            imdb=7.4,
            votes=1500,
            description="A dangerous mission tests an experienced team.",
            price=Decimal("8.99"),
            certification=certification,
            genres=[action],
            directors=[director_two],
            stars=[actor_two],
        ),
        MovieModel(
            name="Gamma Story",
            year=2020,
            time=95,
            imdb=6.8,
            votes=400,
            description="A quiet family story.",
            price=Decimal("3.99"),
            certification=certification,
            genres=[drama],
            directors=[director_two],
            stars=[actor_two],
        ),
        MovieModel(
            name="Delta Force",
            year=2023,
            time=130,
            imdb=8.7,
            votes=2200,
            description="An elite force faces its greatest challenge.",
            price=Decimal("10.99"),
            certification=certification,
            genres=[action, drama],
            directors=[director_one],
            stars=[actor_one, actor_two],
        ),
    ]
    db_session.add_all(movies)
    await db_session.commit()
    return movies


@pytest_asyncio.fixture
async def active_user(
    seeded_user_groups: AsyncSession,
) -> UserModel:
    group = await seeded_user_groups.scalar(
        select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
    )
    assert group is not None
    user = UserModel(
        email="active-user@example.com",
        hashed_password="unused-in-interaction-tests",
        is_active=True,
        group_id=group.id,
    )
    seeded_user_groups.add(user)
    await seeded_user_groups.commit()
    return user


@pytest.fixture
def auth_headers(active_user: UserModel) -> dict[str, str]:
    settings = get_settings()
    jwt_manager = JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
    access_token = jwt_manager.create_access_token(
        {"user_id": active_user.id}
    )
    return {"Authorization": f"Bearer {access_token}"}
