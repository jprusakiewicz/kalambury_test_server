import asyncio
import json
import os
import threading
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from fuzzywuzzy import fuzz

from .clue import ClueManager
from .connection import Connection
from .logger import setup_custom_logger
from .models import PlayerGuess, GuessResult
from .server_errors import GameNotStarted, NoPlayerWithThisId


class Room:
    def __init__(self, room_id, locale):
        self.id = room_id
        self.active_connections: List[Connection] = []
        self.is_game_on = False
        self.game_data: bytes = bytearray()
        self.whos_turn: Optional[str] = None
        self.clue = None
        self.category = None
        self.locale = locale
        self.timeout = 120
        self.timer = threading.Timer(self.timeout, self.next_person_async)
        self.clue_manager = ClueManager(self.locale)
        self.used_words = []
        self.logger = setup_custom_logger(f"room_{self.id}")

    def next_person_async(self):
        self.export_clue()
        asyncio.run(self.restart_or_end_game())

    async def append_connection(self, connection):
        self.active_connections.append(connection)
        self.export_room_status()
        if len(self.active_connections) > 1 and self.is_game_on is False:
            await self.start_game()

    async def kick_player(self, player_id):
        await self.remove_player_by_id(player_id)
        self.export_room_status()
        if len(self.active_connections) <= 1:
            await self.end_game()
        elif player_id == self.whos_turn:
            await self.restart_game()

    async def remove_player_by_id(self, id):
        try:
            connection = next(
                connection for connection in self.active_connections if connection.player.id == id)
        except StopIteration:
            raise NoPlayerWithThisId
        await self.remove_connection(connection)

    async def remove_connection(self, connection_with_given_ws):
        self.active_connections.remove(connection_with_given_ws)
        self.export_room_status()
        if len(self.active_connections) <= 1:
            await self.end_game()
        elif connection_with_given_ws.player.id == self.whos_turn:
            await self.restart_game()

    def check_players_clue(self, players_message):
        self.logger.info(f"checking players clue: {players_message}")
        players_message_stripped = players_message.lower().replace(",", "").replace(".", "")
        clue_stripped = self.clue.lower().replace(",", "").replace(".", "")
        if players_message_stripped == clue_stripped:
            self.logger.info(f"players clue match: {players_message_stripped}")
            return True
        else:
            self.logger.info(f"players clue mismatch: {players_message_stripped}, clue: {clue_stripped}")

    async def handle_players_guess(self, player_guess: PlayerGuess, score_thresh=60):
        score = fuzz.ratio(player_guess.message, self.clue)

        if not self.is_game_on:
            raise GameNotStarted

        if self.check_players_clue(player_guess.message):
            winning_clue = self.clue
            drawer = str(self.whos_turn)
            await self.restart_game()
            return GuessResult(status="WIN", clue=winning_clue, winner=player_guess.player_id, drawer=drawer)

        elif score > score_thresh:
            return GuessResult(status="IS_CLOSE")
        else:
            return GuessResult(status="MISS")

    async def broadcast(self):
        for connection in self.active_connections:
            gs = self.get_game_state(connection.player.id)
            await connection.ws.send_text(gs)
            await connection.ws.send_bytes(self.game_data)

    async def restart_or_end_game(self):
        if len(self.active_connections) >= 2:
            await self.restart_game()
        else:
            await self.end_game()

    async def restart_game(self):
        await self.start_game()

    async def start_game(self):
        self.whos_turn = self.next_person_move()
        self.game_data = bytearray()
        self.is_game_on = True
        self.category, self.clue = self.clue_manager.get_new_clue()
        self.restart_timer()
        await self.broadcast()

    async def end_game(self):
        self.is_game_on = False
        self.whos_turn = None
        self.clue = None
        self.category = None
        await self.broadcast()

    def get_game_state(self, client_id) -> str:
        if client_id == self.whos_turn:
            game_state = {
                "is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "sequence_to_guess": self.clue + f" \ncategory: {self.category}",
                "timestamp": self.timestamp.isoformat(),
            }
        else:
            game_state = {
                "is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "drawer": self.get_guesser_ui_text(),
            }
            if self.is_game_on is True:
                game_state["timestamp"] = self.timestamp.isoformat()
        return json.dumps(game_state)

    def get_players_ids(self):
        return [player.player.id for player in self.active_connections]

    def next_person_move(self):
        if self.whos_turn:
            active_players_ids = self.get_players_ids()
            try:
                current_idx = active_players_ids.index(self.whos_turn)
                new_id = active_players_ids[current_idx + 1]
            except (IndexError, ValueError):
                new_id = active_players_ids[0]

        else:
            players_ids = self.get_players_ids()
            new_id = players_ids[0]
        return new_id

    def get_stats(self):
        return {"is_game_on": self.is_game_on,
                "whos_turn": self.whos_turn,
                "number_of_connected_players": len(self.active_connections),
                "players_ids": self.get_players_ids(),
                "clue": self.clue}

    def restart_timer(self):
        self.timer.cancel()
        self.timer = threading.Timer(self.timeout, self.next_person_async)
        self.timer.start()
        self.timestamp = datetime.now() + timedelta(0, self.timeout)

    def export_clue(self):
        try:
            result = requests.post(
                url=os.path.join(os.getenv('EXPORT_RESULTS_URL'), "/games/handle-timeout/kalambury"),
                json=dict(roomId=self.id, clue=self.clue))
            if result.status_code == 200:
                self.logger.info("timeout export succesfull")
            else:
                self.logger.info("timeout export failed: ", result.text, result.status_code)
        except Exception as e:
            self.logger.info(e.__class__.__name__)
            self.logger.info("failed to get EXPORT_RESULTS_URL env var")

    def export_room_status(self):
        try:
            players_in_game = self.get_players_ids()
            result = requests.post(
                url=os.path.join(os.getenv('EXPORT_RESULTS_URL'), "rooms/update-room-status"),
                json=dict(roomId=self.id, activePlayers=players_in_game,
                          currentDrawer=self.whos_turn if self.whos_turn != 0 else None))
            if result.status_code == 200:
                self.logger.info("export succesfull")
            else:
                self.logger.info("export failed: ", result.text, result.status_code)
        except Exception as e:
            self.logger.info(e.__class__.__name__)
            self.logger.info("failed to get EXPORT_RESULTS_URL env var")

    def get_guesser_ui_text(self):
        try:
            player_nick = next(
                connection.player.nick for connection in self.active_connections if
                connection.player.id == self.whos_turn)
            text = "drawer: " + str(player_nick) + f"\ncategory: {self.category}"
        except StopIteration:
            text = " " + f"\ncategory: {self.category}"
        return text

    async def handle_other_move(self, other_move):
        if other_move["type"] == "skip":
            await self.restart_game()

    async def handle_text_message(self, message: dict):
        if 'other_move' in message:
            await self.handle_other_move(message['other_move'])
        else:
            self.logger.info("other text message")
