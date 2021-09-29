from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from starlette.responses import JSONResponse

from app.connection_manager import ConnectionManager
from app.models import GuessResult, PlayerGuess
from app.server_errors import GameNotStarted, PlayerIdAlreadyInUse, NoRoomWithThisId, RoomIdAlreadyInUse

app = FastAPI()

manager = ConnectionManager()


@app.get("/")
async def get():
    return {"status": "ok"}


@app.post("/guess", response_model=GuessResult, tags=["Pawel"])
async def make_a_guess(player_guess: PlayerGuess = Body(..., description="a guess written by player")):
    try:
        response = await manager.handle_players_guess(player_guess)
    except GameNotStarted:
        raise HTTPException(status_code=404, detail=f"The game in room {player_guess.room_id} is not started")
    return response


@app.get("/stats")
async def get_stats(room_id: Optional[str] = None):
    if room_id:
        try:
            return manager.get_room_stats(room_id)
        except NoRoomWithThisId:
            return JSONResponse(
                status_code=403,
                content={"detail": f"No room with this id: {room_id}"}
            )
    return manager.get_overall_stats()


@app.post("/room/new/{room_id}")
async def end_game(room_id: str):
    try:
        await manager.create_new_room(room_id)
        return JSONResponse(
            status_code=200,
            content={"detail": "success"}
        )
    except RoomIdAlreadyInUse:
        print(f"Theres already a room with this id: {room_id}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Theres already a room with this id: {room_id}"}
        )


@app.delete("/room/{room_id}")
async def end_game(room_id: str):
    try:
        await manager.delete_room(room_id)
        return JSONResponse(
            status_code=200,
            content={"detail": "success"}
        )
    except NoRoomWithThisId:
        print(f"Theres no room with this id: {room_id}")
        return JSONResponse(
            status_code=403,
            content={"detail": f"Theres no room with this id: {room_id}"}
        )


@app.post("/game/end/{room_id}")
async def end_game(room_id: str):
    await manager.end_game(room_id)
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/end_all_games")
async def end_game():
    await manager.end_all_games()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/start/{room_id}")
async def start_game(room_id: str):
    await manager.start_game(room_id)
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/restart/{room_id}")
async def restart_game(room_id: str):
    await manager.restart_game(room_id)
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.websocket("/ws/{room_id}/{client_id}/{nick}")  # todo add nick
async def websocket_endpoint(websocket: WebSocket, room_id: str, client_id: str, nick: str):
    try:
        await manager.connect(websocket, room_id, client_id, nick)
        try:
            while True:
                message = await websocket.receive()
                await manager.handle_ws_message(message, room_id, client_id)
        except WebSocketDisconnect:
            print("disconnected")
            await manager.disconnect(websocket)
            await manager.broadcast(room_id)
        except RuntimeError as e:
            await manager.disconnect(websocket)
            print(e)
            print("runetime error")
    except PlayerIdAlreadyInUse:
        print(f"Theres already connection with this client id {client_id}")
        await websocket.close(403)

    except NoRoomWithThisId:
        print(f"Theres no room with this id: {room_id}")
        await websocket.close(403)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, workers=1)
