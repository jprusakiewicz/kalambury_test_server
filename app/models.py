from enum import Enum
from typing import Optional

from pydantic.main import BaseModel


class GuessStatus(str, Enum):
    win = "WIN"
    miss = "MISS"
    is_close = "IS_CLOSE"


class PlayerGuess(BaseModel):
    player_id: str
    room_id: str
    message: str


class GuessResult(BaseModel):
    status: GuessStatus
    clue: Optional[str]
