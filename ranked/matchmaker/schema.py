import datetime
import logging

# Use MongoDB json serializer
from bson.json_util import dumps as to_json
from bson.json_util import loads as from_json
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
    UniqueConstraint,
    delete,
    select,
    update,
)


log = logging.getLogger(__name__)
Base = declarative_base()


class User(Base):
    """Defines the User table"""

    __tablename__ = "users"

    _id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), unique=True)

    # Current estimated skill
    skill = Column(Integer, default=1500)  
    sigma = Column(Integer, default=1500)  

    created_at = Column(DateTime)
    last_seen = Column(DateTime, onupdate=datetime.datetime.utcnow)


#
#   Save match history for data analytics
#

class Match(Base):
    __tablename__ = "matches"

    _id = Column(Integer, primary_key=True, autoincrement=True)

    # Match Data
    team_winner = Column(Integer)   # Team that won


class Player(Base):
    __tablename__ = 'players'

    user_id = Column(Integer, ForeignKey("users._id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches._id"), nullable=False)

    # Team id (0-n)
    team = Column(Integer, default=0)

    # estimated skill when the user played a particular game
    skill = Column(Integer, default=1500)
    sigma = Column(Integer, default=1500)

    # Meta data about the player
    # it will be used to train a ML network to estimate their skill level from the player stats
     

class MatchPlayer:
    __tablename__ = 'matchplayers'

    player_id = Column(Integer, ForeignKey("players._id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches._id"), nullable=False)

    # To avoid joins on common queries
    user_id = Column(Integer, ForeignKey("users._id"), nullable=False)

#
# Game Server 
#

class GameServer(Base):
    __tablename__ = 'gameservers'

    _id = Column(Integer, primary_key=True, autoincrement=True)
    port = Column(Integer)
    ipv4 = Column(String(15))
    ipv6 = Column(String(48)) # https://github.com/torvalds/linux/blob/master/include/linux/inet.h#L50
    available = Column(Integer)
    region = Column(Integer)


def get_sql_engine(uri):
    return sqlalchemy.create_engine(
            uri,
            echo=False,
            future=True,
            json_serializer=to_json,
            json_deserializer=from_json,
        )


def create_database(uri):
    engine = get_sql_engine(uri)

    try:
        Base.metadata.create_all(engine)
    except DBAPIError as err:
        log.warning("%s", err)


def fetch_player_skills(engine, mm_request):
    with Session(engine) as session:
        stmt = select(User).where(
            User._id.in_((mm_request.player_ids))
        )

        mm_request.player_skills =  session.execute(stmt).scalars().all()


def find_game_server(engine):
    with Session(engine) as session:
        stmt = select(GameServer).where(GameServer.available == 1)
        return session.scalar(stmt)
