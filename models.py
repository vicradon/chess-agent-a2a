from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Union, Literal
from enum import Enum


class TextPart(BaseModel):
    type: str = "text"
    text: str
    metadata: Optional[Dict[str, object]] = None


class FilePart(BaseModel):
    type: str = "file"
    file: Dict[str, Optional[Union[str, Dict[str, str]]]]
    metadata: Optional[Dict[str, object]] = None


class DataPart(BaseModel):
    type: str = "data"
    data: Dict[str, object]
    metadata: Optional[Dict[str, object]] = None


Part = Union[TextPart, FilePart, DataPart]

class TaskState(Enum):
    submitted = "submitted"
    working = "working"
    inputrequired = "input-required"
    completed = "completed"
    canceled = "canceled"
    failed = "failed"
    unknown = "unknown"

class Message(BaseModel):
    role: Literal["agent", "user"]
    parts: List[Part]
    metadata: Optional[Dict[str, object]] = {}


class Artifact(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Part]
    metadata: Optional[Dict[str, object]] = {}
    index: int
    append: Optional[bool] = False
    lastChunk: Optional[bool] = False


class TaskStatus(BaseModel):
    state: TaskState
    message: Optional[Message] = None
    timestamp: Optional[str] = None


class Task(BaseModel):
    id: str
    sessionId: Optional[str] = None
    status: TaskStatus
    history: Optional[List[Message]] = []
    artifacts: Optional[List[Artifact]] = []
    metadata: Optional[Dict[str, object]] = {}


class TaskSendParams(BaseModel):
    id: str
    sessionId: Optional[str] = None
    message: Message
    historyLength: Optional[int] = None
    pushNotification: Optional[Dict[str, object]] = None
    metadata: Optional[Dict[str, object]] = {}


class PushNotificationConfig(BaseModel):
    url: str
    token: Optional[str] = None
    authentication: Optional[Dict[str, object]] = None


class TaskPushNotificationConfig(BaseModel):
    id: str
    pushNotificationConfig: PushNotificationConfig


class Result(BaseModel):
    id: UUID4
    session_id: UUID4
    status: TaskStatus

class RPCRequest(BaseModel):
    jsonrpc: str
    id: int
    method: str
    params: TaskSendParams

class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    result: Result