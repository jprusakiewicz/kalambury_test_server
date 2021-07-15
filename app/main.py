import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from starlette.responses import JSONResponse

from app.connection_manager import ConnectionManager
from app.models import GuessResult, PlayerGuess
from app.server_errors import GameNotStarted, IdAlreadyInUse

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
    return {"is_game_on": manager.is_game_on,
            "whos turn": manager.whos_turn,
            "number_of_connected_players": len(manager.active_connections),
            "clue": manager.clue}


@app.post("/game/end")
async def end_game():
    await manager.end_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/start")
async def start_game():
    await manager.start_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/restart")
async def restart_game():
    await manager.restart_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        await manager.connect(websocket, client_id)
        print(f"new client connected with id: {client_id}")

        try:
            while True:
                message = await websocket.receive()
                await manager.handle_ws_message(message, client_id)
        except WebSocketDisconnect:
            print("disconnected")
            await manager.disconnect(websocket)
            await manager.broadcast()
        except RuntimeError as e:
            await manager.disconnect(websocket)
            print(e)
            print("runetime error")
    except IdAlreadyInUse:
        print(f"Theres already connection with this client id {client_id}")
        await websocket.close(403)


@app.websocket("/ws_test")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        test_byte = bytes(os.urandom(2190000))
        await websocket.send_bytes(test_byte)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, workers=1)

