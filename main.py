import os
import json
import base64
import random
import datetime
from typing import Tuple, Optional
from dataclasses import dataclass
from fastapi import FastAPI, BackgroundTasks, Request, Body, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from uuid import uuid4 as uuid
import models
import redis
import chess
import chess.engine
from minio import Minio
from minio.error import S3Error

load_dotenv()
app = FastAPI()

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
CHESS_ENGINE_PATH = os.getenv("CHESS_ENGINE_PATH")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")
MINIO_BUCKET_ACCESS_KEY = os.getenv("MINIO_BUCKET_ACCESS_KEY")
MINIO_BUKCET_SECRET_KEY = os.getenv("MINIO_BUKCET_SECRET_KEY")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_BUCKET_ACCESS_KEY,
    secret_key=MINIO_BUKCET_SECRET_KEY,
)


@dataclass
class RedisKeys:
    games = "games"


def generate_random_filename(extension: str = "svg", word_count: int = 3) -> str:
    words = [
        "sun",
        "moon",
        "tree",
        "cloud",
        "river",
        "stone",
        "eagle",
        "wolf",
        "fire",
        "wind",
        "storm",
        "leaf",
        "sky",
        "night",
        "light",
        "shadow",
        "mountain",
        "ocean",
        "echo",
        "whisper",
        "flame",
        "dust",
        "branch",
    ]
    chosen = random.sample(words, word_count)
    return "_".join(chosen) + f".{extension}"


class Game:
    def __init__(self, board, engine, engine_time_limit=0.5):
        self.board = board
        self.engine = engine
        self.engine_time_limit = engine_time_limit

    def aimove(self):
        ai = self.engine.play(
            self.board, chess.engine.Limit(time=self.engine_time_limit)
        )
        self.board.push(ai.move)
        return ai.move, self.board

    def usermove(self, move):
        try:
            self.board.push_san(move)
        except ValueError:
            raise ValueError(f"Invalid move: {move}")
        return self.board

    def to_dict(self):
        return {"fen": self.board.fen(), "engine_time_limit": self.engine_time_limit}

    @classmethod
    def from_dict(cls, data):
        board = chess.Board(data["fen"])
        engine_time_limit = data.get("engine_time_limit", 0.5)
        engine = chess.engine.SimpleEngine.popen_uci(CHESS_ENGINE_PATH)
        return cls(board, engine, engine_time_limit)


class GameRepository:
    def __init__(self, redis_client, redis_key_prefix=RedisKeys.games):
        self.r = redis_client
        self.prefix = redis_key_prefix

    def _session_key(self, session_id: str) -> str:
        return f"{self.prefix}:{session_id}"

    def save(self, session_id: str, game: Game):
        key = self._session_key(session_id)
        self.r.set(key, json.dumps(game.to_dict()))

    def load(self, session_id: str) -> Optional[Game]:
        key = self._session_key(session_id)
        data = self.r.get(key)
        if data:
            return Game.from_dict(json.loads(data))
        return None

    def delete(self, session_id: str):
        key = self._session_key(session_id)
        self.r.delete(key)


def start_game(engine_path: str) -> Game:
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    board = chess.Board()

    return Game(board, engine)


@app.get("/", response_class=HTMLResponse)
def read_root():
    return '<p style="font-size:40px">Chess bot A2A</p>'


game_repo = GameRepository(r)


async def handle_task_send(request_id: str, params: models.TaskParams):
    session_id = params.sessionId
    game = game_repo.load(session_id)

    if not game:
        game = start_game(engine_path=CHESS_ENGINE_PATH)

    tentative_move = params.message.parts[0].text
    try:
        game.usermove(tentative_move)
    except ValueError:
        response = models.RPCResponse(
            id=request_id,
            error=models.InvalidParamsError(
                message=f"Invalid move: '{tentative_move}'",
                data=f"You sent '{tentative_move}' which is not a valid chess move",
            ),
        )
        print(response)
        return response
    except:
        response = models.RPCResponse(
            id=request_id,
            error=models.InvalidParamsError(
                message="An error occured",
            ),
        )
        return response

    aimove, board = game.aimove()

    game_repo.save(session_id, game)

    filename = generate_random_filename()  # e.g., 'cloud_stone_echo.svg'
    destination_file = f"public/chessagent/{filename}"
    source_file = f"/tmp/{filename}"

    svg = board._repr_svg_()

    with open(source_file, "w") as f:
        f.write(svg)
        new_source_file = source_file.split(".svg")[0] + ".png"

        import cairosvg

        cairosvg.svg2png(url=source_file, write_to=new_source_file)

        source_file = new_source_file
        destination_file = destination_file.split(".svg")[0] + ".png"

    minio_client.fput_object(
        MINIO_BUCKET_NAME,
        destination_file,
        source_file,
    )

    image_url = f"https://media.tifi.tv/{MINIO_BUCKET_NAME}/{destination_file}"

    response = models.RPCResponse(
        id=request_id,
        result=models.Result(
            id=params.id,
            session_id=params.sessionId,
            status=models.TaskStatus(
                state=models.TaskState.inputrequired,
                timestamp=datetime.datetime.now().isoformat(),
                message=models.Message(
                    role="agent",
                    parts=[
                        models.TextPart(text=aimove.uci()),
                        models.TextPart(text=str(board)),
                        models.FilePart(
                            file=models.FileContent(
                                name=filename,
                                mimeType="image/svg+xml",
                                uri=image_url,
                            )
                        ),
                    ],
                ),
            ),
        ),
    )

    return response


async def handle_get_task(id: int, params: models.TaskParams):
    return "bro"


@app.post("/")
async def handle_rpc(rpc_request: models.RPCRequest):
    if rpc_request.method == models.RPCMethod.TASK_SEND:
        return await handle_task_send(rpc_request.id, rpc_request.params)
    elif rpc_request.method == models.RPCMethod.TASK_GET:
        return await handle_get_task(rpc_request.id, rpc_request.params)

    raise HTTPException(status_code=400, detail="Could not handle task")


@app.get("/.well-known/agent.json")
def agent_card(request: Request):
    external_base = request.headers.get("x-external-base-url", "")
    base_url = str(request.base_url).rstrip("/") + external_base
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

    PORT = int(os.getenv("PORT", 7000))

    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
