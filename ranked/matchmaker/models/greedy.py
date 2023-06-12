import logging
import datetime
import random

from ranked.matchmaker.messages import MatchmakingRequest

import sqlalchemy
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import (
    BINARY,
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Float,
    UniqueConstraint,
    delete,
    select,
    update,
)


log = logging.getLogger(__name__)
Base = declarative_base()


class MMRequestSQL(Base):
    __tablename__ = "MMRequests"

    _id = Column(Integer, primary_key=True, autoincrement=True)
    skill = Column(Float, default=1500)
    party_count = Column(Integer)
    region = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("index_skill", "skill"),
        Index("index_region", "region"),
        Index("index_party", "party_count"),
        Index("index_created", "created_at"),
    )


class MatchmakerSqlite:
    """Use in-memory sqlite database"""

    def __init__(self) -> None:
        self.engine = sqlalchemy.create_engine("sqlite://", echo=False, future=True)
        Base.metadata.create_all(self.engine)
        self.requests = dict()
        self.id = dict()

        self.player_per_team = 5
        self.number_of_team = 2

    def insert_request(self, mm_request: MatchmakingRequest):
        with Session(self.engine) as session:
            request = MMRequestSQL(
                skill=mm_request.skill(),
                party_count=mm_request.player_count(),
            )
            session.add(request)
            session.flush()
            session.refresh(request)
            self.requests[request._id] = mm_request
            self.id[mm_request.unique_id] = request._id

    def remove_request(self, uid):
        with Session(self.engine) as session:
            request_id = self.id.pop(uid, None)
            self.requests.pop(request_id, None)

            if request_id:
                stmt = delete(MMRequestSQL).where(MMRequestSQL._id == request_id)
                session.execute(stmt)
                session.commit()

    def group_players(self, skill, margin):
        with Session(self.engine) as session:
            n = self.player_per_team * self.number_of_team

            entries = (
                select(MMRequestSQL)
                .where(MMRequestSQL.skill.between(skill - margin, skill + margin))
                .limit(n * 2)
                .all()
                .scalars()
            )

            random.shuffle(entries)
            selected = entries[:n]

            for s in selected:
                mm_request = self.requests[s._id]

            for s in selected:
                s.delete()
