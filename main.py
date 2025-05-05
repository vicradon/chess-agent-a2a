import os
import json
from fastapi import FastAPI, BackgroundTasks, Request, Body
from dotenv import load_dotenv
from uuid import uuid4 as uuid
from jsonrpcclient import parse, parse_json
import models

load_dotenv()
app = FastAPI()

CHESS_ENGINE_PATH = os.getenv("CHESS_ENGINE_PATH")

def start_game():
    import chess
    import chess.engine
    engine = chess.engine.SimpleEngine.popen_uci(CHESS_ENGINE_PATH)
    board = chess.Board()
    
    return board, engine

def aimove(board):
    ai = engine.play(board, chess.engine.Limit(time=0.5))
    board.push(ai.move)

def usermove(board, change):
    piece = chess.Move.from_uci(change)
    board.push(piece)

@app.get("/")
def read_root():
    return "<p>Chess bot A2A</p>"

async def handle_task_send(id: int, params: models.TaskSendParams):
    response = models.RPCResponse(
        id=id,
        result=models.Result(
            id=uuid(),
            session_id=uuid(),
            status=models.TaskStatus(
                state=models.TaskState.inputrequired,
                message=models.Message(
                    role="agent",
                    parts=[models.TextPart(
                        text="make your move"
                    )]
                )
            ),
        )
    )

    return response


async def handle_get_task(id: int, params: models.TaskSendParams):
    return "bro"

@app.post("/")
async def handle_rpc(rpc_request: models.RPCRequest):
    if rpc_request.method == "tasks/send":
        return await handle_task_send(rpc_request.id, rpc_request.params)
    elif rpc_request.method == "tasks/get":
        return await handle_get_task(rpc_request.id, rpc_request.params)

    raise HTTPException(status_code=400, detail="Could not handle task")

@app.get("/.well-known/agent.json")
def agent_card(request: Request):
    base_url = str(request.base_url).rstrip("/")
    card = {
        "name": "Chess Agent",
        "description": "An agent that plays chess. Accepts moves in standard notation and returns updated board state as FEN and an image.",
        "url": f"{base_url}",
        "provider": {
            "organization": "CoolVicradon",
            "url": f"{base_url}/provider",
        },
        "version": "1.0.0",
        "documentationUrl": f"{base_url}/docs",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "authentication": {"schemes": ["Bearer"]},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/x-fen", "image/png"],
        "skills": [
            {
                "id": "play_move",
                "name": "Play Move",
                "description": "Plays a move and returns the updated board in FEN format and as an image.",
                "tags": ["chess", "gameplay", "board"],
                "examples": ["e4", "Nf3", "d5"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/x-fen", "image/png"],
            }
        ],
    }

    return card


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=7000, reload=True)
