from starlette.websockets import WebSocket

from app.connection import Connection
from app.models import PlayerGuess
from app.player import Player
from app.room import Room
from app.server_errors import PlayerIdAlreadyInUse, NoRoomWithThisId, RoomIdAlreadyInUse


class ConnectionManager:
    def __init__(self):
        self.rooms = [Room(room_id="1")]

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
