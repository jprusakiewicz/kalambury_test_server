import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ConnectionManager import ConnectionManager

app = FastAPI()

manager = ConnectionManager()


@app.get("/")
async def get():
    return {"hello": "world"}


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
        manager.disconnect(websocket)
        await manager.broadcast()
    except RuntimeError:
        print("runetime error")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
