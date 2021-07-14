import json
import random
from typing import List

from starlette.websockets import WebSocket

from app.models import PlayerGuess, GuessResult
from app.player import Player
from fuzzywuzzy import fuzz

CLUES = ['pies', 'kot', 'Ala']


class Connection:
    def __init__(self, ws: WebSocket, player: Player):
        self.ws = ws
        self.player = player


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Connection] = []
        self.is_game_on = False
        self.game_data: bytes = bytearray()
        self.whos_turn: int = 0
        self.clue = None

    async def handle_players_guess(self, player_guess: PlayerGuess, score_thresh=60):
        score = fuzz.ratio(player_guess.message, self.clue)

        if self.is_game_on == False:
            raise FileNotFoundError #todo
        if player_guess.message == self.clue:
            await self.restart_game()
            return GuessResult(status="WIN", clue=self.clue)
        elif score > score_thresh:
            return GuessResult(status="IS_CLOSE")
        else:
            return GuessResult(status="MISS")

    async def connect(self, websocket: WebSocket, client_id):
        await websocket.accept()
        connection = Connection(ws=websocket, player=Player(id=client_id))
        await self.append_connection(connection)
        await websocket.send_text(self.get_game_state(client_id))
        await websocket.send_bytes(self.game_data)

    async def append_connection(self, connection):
        self.active_connections.append(connection)
        if len(self.active_connections) > 0 and self.is_game_on is False:  # todo
            await self.start_game()

    async def restart_game(self):
        self.game_data = bytearray()
        await self.start_game()

    async def start_game(self):
        self.is_game_on = True
        self.whos_turn = random.choice(
            [connection.player.id for connection in self.active_connections])  # todo if no enough players
        self.clue = random.choice(CLUES)
        await self.broadcast_json()

    async def end_game(self):
        self.is_game_on = False
        self.whos_turn = 0
        self.clue = None
        await self.broadcast_json()

    async def disconnect(self, websocket: WebSocket):
        connection_with_given_ws = next(c for c in self.active_connections if c.ws == websocket)
        self.active_connections.remove(connection_with_given_ws)
        if len(self.active_connections) <= 1:
            await self.end_game()

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_json(self):
        for connection in self.active_connections:
            gs = self.get_game_state(connection.player.id)
            await connection.ws.send_text(gs)

    async def broadcast(self):
        for connection in self.active_connections:
            await connection.ws.send_bytes(self.game_data)

    async def handle_ws_message(self, message, client_id):
        try:
            if client_id == self.whos_turn:
                self.game_data = message['bytes']
                await self.broadcast()
        except KeyError as e:
            print(e)

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
