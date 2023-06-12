from dataclasses import dataclass, field
from enum import Enum
import secrets
from typing import Optional


class MessageKind(Enum):
    MMRequest = 1
    MMResponse = 2
    MMServerConfig = 3
    KeepAlive = 4


@dataclass
class MatchmakingRequest:
    kind: MessageKind
    player_ids: list[str]
    player_skills: list[int] = field(default_factory=list)
    client_secrets: list[str] = field(default_factory=list)
    request_id: Optional[int] = None

    def generate_secrets(self):
        self.client_secrets = [secrets.token_hex(16) for _ in self.player_ids]

    def skill(self):
        return int(sum(self.player_skills) / len(self.player_skills))

    def player_count(self):
        return len(self.player_ids)


@dataclass
class KeepAlive:
    kind: MessageKind = MessageKind.KeepAlive


@dataclass
class MatchmakingResponse:
    server_ip: str  # Address of the game instance
    server_port: int  # Port to use to connect to the game instane
    client_secret: list[str]  # secret to use to connect to the instance

    kind: MessageKind = MessageKind.MMResponse


@dataclass
class MatchmakingServerConfig:
    kind: MessageKind
    client_secrets: list[str]  # expected client secrets
