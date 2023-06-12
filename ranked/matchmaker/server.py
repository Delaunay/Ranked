import asyncio
import json
import logging
import socket
import sys
from dataclasses import asdict
from struct import unpack

import ranked.matchmaker.schema as db
from ranked.matchmaker.messages import (
    MatchmakingRequest,
    MatchmakingResponse,
    MessageKind,
)
from ranked.matchmaker.worker import Matchmaker

log = logging.getLogger(__name__)


class Server:
    def __init__(self) -> None:
        self.database_uri = ""
        self.worker = Matchmaker()
        self._dispatch = {MessageKind.MMRequest: self.matchmaking_request}

        db.create_database(self.get_sql_client())

    def get_sql_client(self):
        return db.get_sql_engine(self.database_uri)

    async def fetch_player_skills(self, mm_request: MatchmakingRequest):
        engine = self.get_sql_client()
        db.fetch_player_skills(engine, mm_request)

    async def find_free_game_server(self):
        engine = self.get_sql_client()
        return db.find_game_server(engine)

    def find_team(self, mm_request: MatchmakingRequest, promise: asyncio.Future):
        pass

    async def matchmaking_request(self, client, payload):
        mm_request = MatchmakingRequest(**payload)
        mm_request.generate_secrets()

        await self.fetch_player_skills(mm_request)

        loop = asyncio.get_event_loop()
        result = loop.create_future()
        self.find_team(mm_request, result)

        await result

        server = await self.find_free_game_server()

        await self.send_json(
            client,
            asdict(
                MatchmakingResponse(
                    server.ip,
                    server.port,
                    mm_request.client_secrets,
                )
            ),
        )
        client.close()

    async def send_json(self, client, obj):
        payload = json.dumps(obj).encode("utf8")

        size = len(payload)
        size_bytes = size.to_bytes(4, byteorder=sys.byteorder)

        loop = asyncio.get_event_loop()
        await loop.sock_sendall(client, size_bytes)
        await loop.sock_sendall(client, payload)

    async def handle_request(self, client):
        loop = asyncio.get_event_loop()

        size_bytes = await loop.sock_recv(client, 4)
        size = int(unpack("@I", size_bytes)[0])

        request_bytes = await loop.sock_recv(client, size)

        payload = json.loads(request_bytes)

        handler = self._dispatch.get(MessageKind.MMRequest, None)

        if handler:
            handler(client, payload)

        client.close()

    async def run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server.bind(("localhost", 15555))
        server.listen(8)
        server.setblocking(False)

        loop = asyncio.get_event_loop()

        # the matchmaker worker
        loop.create_task(self.worker.set_promises())

        # start accepting clients
        while True:
            try:
                client, _ = await loop.sock_accept(server)
                loop.create_task(self.handle_request(client))
            except KeyboardInterrupt:
                log.info("Server stopped by user")
                break

        self.worker.stop()
        # task.cancel()


def main():
    mm = Server()
    asyncio.run(mm.run_server())


if __name__ == "__main__":
    main()
