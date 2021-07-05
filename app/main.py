import os

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.responses import JSONResponse

from app.ConnectionManager import ConnectionManager

app = FastAPI()

manager = ConnectionManager()


@app.get("/")
async def get():
    return {"status": "ok"}


@app.get("/stats")
async def get():
    return {"is_game_on": manager.is_game_on,
            "whos turn": manager.whos_turn,
            "number_of_connected_players": len(manager.active_connections)}


@app.post("/game/end")
async def end_game():
    await manager.end_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/start")
async def end_game():
    await manager.start_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.post("/game/restart")
async def end_game():
    await manager.restart_game()
    return JSONResponse(
        status_code=200,
        content={"detail": "success"}
    )


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket, client_id)
    print(f"new client connected with id: {client_id}")
    try:
        while True:
            message = await websocket.receive()
            await manager.handle_message(message, client_id)
    except WebSocketDisconnect:
        print("disconnected")
        await manager.disconnect(websocket)
        await manager.broadcast()
    except RuntimeError as e:
        await manager.disconnect(websocket)
        print(e)
        print("runetime error")


@app.websocket("/ws_test")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        test_byte = bytes(os.urandom(2190000))
        await websocket.send_bytes(test_byte)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, workers=1)
