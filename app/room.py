import json
import random
from typing import List

from fuzzywuzzy import fuzz

from .connection import Connection
from .models import PlayerGuess, GuessResult
from .server_errors import GameNotStarted

CLUES = ['pies', 'kot', 'Ala']


class Room:
    def __init__(self, room_id):
        self.id = room_id
        self.active_connections: List[Connection] = []
        self.is_game_on = False
        self.game_data: bytes = bytearray()
        self.whos_turn: int = 0
        self.clue = None

    async def append_connection(self, connection):
        self.active_connections.append(connection)
        if len(self.active_connections) > 0 and self.is_game_on is False:  # todo change to 1
            await self.start_game()

    async def remove_connection(self, connection_with_given_ws):
        self.active_connections.remove(connection_with_given_ws)
        if len(self.active_connections) <= 1:
            await self.end_game()

    async def handle_players_guess(self, player_guess: PlayerGuess, score_thresh=60):
        score = fuzz.ratio(player_guess.message, self.clue)

        if not self.is_game_on:
            raise GameNotStarted
        if player_guess.message == self.clue:
            winning_clue = self.clue
            await self.restart_game()
            return GuessResult(status="WIN", clue=winning_clue)
        elif score > score_thresh:
            return GuessResult(status="IS_CLOSE")
        else:
            return GuessResult(status="MISS")

    async def broadcast_json(self):
        for connection in self.active_connections:
            gs = self.get_game_state(connection.player.id)
            await connection.ws.send_text(gs)

    async def restart_game(self):
        await self.start_game()

    async def start_game(self):
        self.game_data = bytearray()
        self.is_game_on = True
        self.whos_turn = self.draw_random_player_id()
        self.clue = random.choice(CLUES)
        await self.broadcast_json()

    async def end_game(self):
        self.is_game_on = False
        self.whos_turn = 0
        self.clue = None
        await self.broadcast_json()

    def get_game_state(self, client_id) -> str:
        if client_id == self.whos_turn:
            player = next(
                connection.player for connection in self.active_connections if connection.player.id == client_id)
            game_state = {
                "is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "game_data": self.game_data.decode('ISO-8859-1'),
                "sequence_to_guess": player.player_data
            }
        else:
            game_state = {
                "is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "game_data": self.game_data.decode('ISO-8859-1')
            }

        return json.dumps(game_state)

    def draw_random_player_id(self):
        return random.choice(
            [connection.player.id for connection in self.active_connections])

    def get_stats(self):
        return {"is_game_on": self.is_game_on,
                "whos turn": self.whos_turn,
                "number_of_connected_players": len(self.active_connections),
                "clue": self.clue}
