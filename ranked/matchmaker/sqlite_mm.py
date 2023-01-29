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








# from scipy.optimize import linprog



# def get_inequality_constraint(pool_size):
#     """Force team1 weights to be possitive, force team2 weights to be negative"""
#     # t1 > 0
#     # t2 < 0
#     # 
#     # -t1 <= 0
#     #  t2 <= 0
#     A_ub = np.zeros((pool_size * 2, pool_size * 2))
#     for i in range(pool_size):
#         A_ub[i, i] = -1
#         A_ub[pool_size + i, pool_size + i] = 1

#     b_ub = np.zeros((pool_size * 2,))
#     b_ub[:] = 0

#     return A_ub, b_ub


# def get_player_count_constraints(pool_size, player_per_team):
#     A = np.zeros((3, pool_size * 2))
#     b = np.zeros((3,))

#     A[0, :pool_size] = 1
#     A[1, pool_size:] = -1

#     A[2, :pool_size] = 1
#     A[2, pool_size:] = -1
    
#     b[0] = player_per_team
#     b[1] = player_per_team
#     b[2] = player_per_team * 2

#     return A, b

# def optimize(skills, player_per_team=5) -> None:
#     # A x = b
#     #
#     #   For 2 players
#     #   
#     #       we a pool of player of size n
#     #       their skill is S = [s1 ... sn]
#     #       
#     #       Minimize f = (S .* T1 - S .* T2) ^2
#     #                f = (S .* (T1 - T2) ) ^2
#     #
#     #               f'T1 =   2 * S. T1          = 0
#     #               f'T2 = - 2 * S. T2          = 0
#     #               f'l1 = sum(t1) - #Player    = 0
#     #               f'l2 = sum(t2) - #Player    = 0
#     #               f'l3 = T1 .* T2             = 0         <= Non Linear
#     #       With:
#     #            sum(T1) = #Player    
#     #            sum(T2) = -#Player
#     #           T1 .* T2 = 0
#     #
#     #
#     #       System = (S .* (T1 - T2) ) ^2 - l1 * (sum(T1) - #Player) - l2 * (sum(T2) - #Player) - l3 * T1 .* T2
#     #
#     #   Reformulate constraint to be
#     #
#     #       (t1 - t2) <= 1
#     #
#     #           
#     pool_size = len(skills)

#     c = np.zeros((pool_size * 2,))
#     c[:pool_size] = skills
#     c[pool_size:] = skills

#     A, b = get_player_count_constraints(pool_size, player_per_team)
#     A_ub, b_ub = get_inequality_constraint(pool_size)

#     results = linprog(
#         c, 
#         A_eq=A, 
#         b_eq=b, 
#         A_ub=A_ub,
#         b_ub=b_ub,
#         bounds=(-1, 1), 
#     )

#     x = results.x

#     t1 = x[:pool_size]
#     t2 = - x[pool_size:]

#     return t1, t2


# def main():
#     skills = np.array([
#         1501, 
#         1499, 
#         1500, 
#         1500, 
#         1500, 
#         1500, 
#         1500, 
#         1500, 
#         1501, 
#         1499,
#     ])

#     t1, t2 = optimize(skills, 2)

#     t1_rating = t1 @ skills
#     t2_rating = t2 @ skills

#     print

#     print(t1, t1_rating, t2, t2_rating)

# """
# if __name__ == '__main__':
#     main()
