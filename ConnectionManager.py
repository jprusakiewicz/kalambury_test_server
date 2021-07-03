import json
from typing import List
import random
from starlette.websockets import WebSocket

from player import Player


class Connection:
    def __init__(self, ws: WebSocket, player: Player):
        self.ws = ws
        self.player = player


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Connection] = []
        self.is_game_on = False
        self.game_data: List[bytes] = []
        self.whos_turn: int = 0

    async def connect(self, websocket: WebSocket, client_id):
        await websocket.accept()
        connection = Connection(ws=websocket, player=Player(id=client_id))
        self.append_connection(connection)
        await websocket.send_text(self.get_game_state(client_id))

    def append_connection(self, connection):
        self.active_connections.append(connection)
        if len(self.active_connections) > 1:
            self.start_game()

    def start_game(self):
        self.is_game_on = True
        self.whos_turn = random.choice([connection.player.id for connection in self.active_connections])

    def disconnect(self, websocket: WebSocket):
        connection_with_given_ws = next(c for c in self.active_connections if c.ws == websocket)
        self.active_connections.remove(connection_with_given_ws)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self):
        for connection in self.active_connections:
            await connection.ws.send_text(self.get_game_state(connection.player.id))

    async def handle_message(self, message, client_id):
        try:
            if message["id"] == client_id:
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
                "game_data": self.game_data,
                "sequence_to_guess": player.player_data
            }
        else:
            game_state = {
                "is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "game_data": self.game_data
            }

        return json.dumps(game_state)
