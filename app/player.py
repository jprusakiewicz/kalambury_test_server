from typing import Optional


class Player:
    def __init__(self, player_id: str, player_data: Optional[str] = None):
        self.id = player_id
        self.player_data = player_data
