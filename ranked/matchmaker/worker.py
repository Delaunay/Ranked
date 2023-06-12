import asyncio
import logging
from itertools import chain
from multiprocessing import Manager, Process

from ranked.matchmaker.messages import MatchmakingRequest

log = logging.getLogger(__name__)


def worker(input_q, output_q, state, player_size=4, team_count=2):
    buckets = [[]] * 10000

    while state["running"]:
        mm_request = input_q.get()

        skill = mm_request.skill()
        arr = buckets[skill]
        arr.append(mm_request)

        mn = min(0, skill - 100)
        mx = max(len(buckets), skill + 101)

        mid = (mx - mn) // 2
        player_count = 0

        selected = []
        selected.extend(arr)

        for party in arr:
            player_count += party.player_count()

        for i in range(1, mid):
            if player_count >= player_size:
                break

            top = buckets[skill + i]
            bot = buckets[skill - i]

            for party in chain(top, bot):
                player_count += party.player_count()
                selected.append(party)

        # Makes teams
        player_per_team = player_size // team_count
        teams = [[]] * team_count

        for party in selected:
            n = party.player_count()
            teams
        # --
        # --

    input_q.close()


class MatchmakerProcessManager:
    def __init__(self) -> None:
        self.manager = Manager()
        self.input_q = self.manager.Queue()
        self.output_q = self.manager.Queue()
        self.state = self.manager.dict()
        self.state["running"] = True

        self.process = Process(target=worker, args=(self.input_q, self.output_q))
        self.process.start()

        self.futures = dict()
        self.unique_id = 0
        self.running = True

        asyncio.ProcessPoolExecutor

    def stop(self):
        self.state["running"] = False

    def find_team(self, mm_request: MatchmakingRequest, promise: asyncio.Future):
        if not self.state["running"]:
            log.warning("Not running")
            return

        uid = self.unique_id
        mm_request.request_id = uid
        self.futures[uid] = promise
        self.input_q.put(mm_request)
        self.unique_id += 1

    async def set_promises(self):
        while self.state["running"]:
            uid, response = self.output_q.get()
            fut = self.futures.pop(uid)
            fut.set_result(response)

        self.output_q.close()

        for _, fut in self.futures.items():
            fut.set_result(None)

        self.output_q.join_thread()
