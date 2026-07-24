import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class MovieReactionEnum(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


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
    reactions: Mapped[list["MovieReactionModel"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    ratings: Mapped[list["MovieRatingModel"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["MovieCommentModel"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )


class MovieReactionModel(Base):
    __tablename__ = "movie_reactions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    reaction: Mapped[MovieReactionEnum] = mapped_column(
        Enum(MovieReactionEnum), nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        back_populates="movie_reactions"
    )
    movie: Mapped["MovieModel"] = relationship(back_populates="reactions")


class MovieRatingModel(Base):
    __tablename__ = "movie_ratings"
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 10",
            name="check_movie_rating_range",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["UserModel"] = relationship(back_populates="movie_ratings")
    movie: Mapped["MovieModel"] = relationship(back_populates="ratings")


class MovieCommentModel(Base):
    __tablename__ = "movie_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("movie_comments.id", ondelete="CASCADE")
    )

    user: Mapped["UserModel"] = relationship(back_populates="movie_comments")
    movie: Mapped["MovieModel"] = relationship(back_populates="comments")
    parent: Mapped["MovieCommentModel | None"] = relationship(
        remote_side=[id],
        back_populates="replies",
    )
    replies: Mapped[list["MovieCommentModel"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="MovieCommentModel.created_at",
    )
