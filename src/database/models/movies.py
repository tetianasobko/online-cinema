from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


MovieGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id"),
        primary_key=True,
        nullable=False,
    ),
)


MovieDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "director_id",
        ForeignKey("directors.id"),
        primary_key=True,
        nullable=False,
    ),
)


MovieStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id"),
        primary_key=True,
        nullable=False,
    ),
)


FavoriteMoviesModel = Table(
    "favorite_movies",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=MovieGenresModel,
        back_populates="genres",
    )


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=MovieStarsModel,
        back_populates="stars",
    )


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=MovieDirectorsModel,
        back_populates="directors",
    )


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        back_populates="certification"
    )


class MovieModel(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "year",
            "time",
            name="unique_movie_constraint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        Uuid, default=uuid4, unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float | None] = mapped_column(Float)
    gross: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2))
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id"), nullable=False
    )

    certification: Mapped["CertificationModel"] = relationship(
        back_populates="movies"
    )
    genres: Mapped[list["GenreModel"]] = relationship(
        secondary=MovieGenresModel,
        back_populates="movies",
    )
    directors: Mapped[list["DirectorModel"]] = relationship(
        secondary=MovieDirectorsModel,
        back_populates="movies",
    )
    stars: Mapped[list["StarModel"]] = relationship(
        secondary=MovieStarsModel,
        back_populates="movies",
    )
    favorited_by: Mapped[list["UserModel"]] = relationship(
        secondary=FavoriteMoviesModel,
        back_populates="favorite_movies",
    )
