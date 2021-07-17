import json
import random
from typing import List

from fuzzywuzzy import fuzz
from starlette.websockets import WebSocket

from app.models import PlayerGuess, GuessResult
from app.player import Player
from app.server_errors import GameNotStarted, PlayerIdAlreadyInUse, NoRoomWithThisId, RoomIdAlreadyInUse

CLUES = ['pies', 'kot', 'Ala']


class Connection:
    def __init__(self, ws: WebSocket, player: Player):
        self.ws = ws
        self.player = player


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


class ConnectionManager:
    def __init__(self):
        self.rooms = [Room(room_id="2")]

    def get_room(self, room_id):
        try:
            return next(r for r in self.rooms if r.id == room_id)
        except StopIteration:
            raise NoRoomWithThisId

    async def restart_game(self, room_id: str):
        room = self.get_room(room_id)
        await room.restart_game()

    async def start_game(self, room_id: str):
        room = self.get_room(room_id)
        await room.start_game()

    async def end_game(self, room_id: str):
        room = self.get_room(room_id)
        await room.end_game()

    async def end_all_games(self):
        for room in self.rooms:
            await room.end_game()

    async def connect(self, websocket: WebSocket, room_id: str, client_id: str):
        self.validate_client_id(room_id, client_id)
        await websocket.accept()
        connection = Connection(ws=websocket, player=Player(player_id=client_id))
        await self.append_connection(room_id, connection)
        room = self.get_room(room_id)
        await websocket.send_text(room.get_game_state(client_id))
        await websocket.send_bytes(room.game_data)

    async def append_connection(self, room_id, connection):
        room = self.get_room(room_id)
        await room.append_connection(connection)

    async def disconnect(self, websocket: WebSocket):
        connection_with_given_ws, room = self.get_active_connection(websocket)
        await room.remove_connection(connection_with_given_ws)

    async def broadcast(self, room_id):
        room = self.get_room(room_id)
        for connection in room.active_connections:
            await connection.ws.send_bytes(self.game_data)

    async def handle_ws_message(self, message, room_id, client_id):
        room = self.get_room(room_id)
        try:
            if client_id == room.whos_turn:
                self.game_data = message['bytes']
                await self.broadcast(room_id)
        except KeyError as e:
            print(e)

    async def handle_players_guess(self, player_guess: PlayerGuess):
        room = self.get_room(player_guess.room_id)
        return await room.handle_players_guess(player_guess)

    def get_active_connection(self, websocket: WebSocket):
        for r in self.rooms:
            for connection in r.active_connections:
                if connection.ws == websocket:
                    return connection, r

    def validate_client_id(self, room_id: str, client_id: str):
        room = self.get_room(room_id)
        if client_id in [connection.player.id for connection in room.active_connections]:
            raise PlayerIdAlreadyInUse

    def get_room_stats(self, room_id):
        room = self.get_room(room_id)
        return room.get_stats()

    def get_overall_stats(self):
        return {'rooms_count': len(self.rooms),
                'rooms_ids': [r.id for r in self.rooms]}

    async def create_new_room(self, room_id):
        if room_id not in [room.id for room in self.rooms]:
            self.rooms.append(Room(room_id=room_id))
        else:
            raise RoomIdAlreadyInUse

    async def delete_room(self, room_id):
        room = self.get_room(room_id)
        self.rooms.remove(room)
