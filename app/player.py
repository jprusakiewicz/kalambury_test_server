from typing import Optional


class Player:
    def __init__(self, id: int, player_data: Optional[str] = None):
        self.id = id
        self.player_data = player_data
