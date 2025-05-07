from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Union, Literal, NamedTuple
from enum import Enum


class ErrorDetail(NamedTuple):
    message: str
    description: str

ERROR_CODES = {
    -32700: ErrorDetail("JSON parse error", "Invalid JSON was sent"),
    -32600: ErrorDetail("Invalid Request", "Request payload validation error"),
    -32601: ErrorDetail("Method not found", "Not a valid method"),
    -32602: ErrorDetail("Invalid params", "Invalid method parameters"),
    -32603: ErrorDetail("Internal error", "Internal JSON-RPC error"),
    -32001: ErrorDetail("Task not found", "Task not found with the provided id"),
    -32002: ErrorDetail("Task cannot be canceled", "Task cannot be canceled by the remote agent"),
    -32003: ErrorDetail("Push notifications not supported", "Push Notification is not supported by the agent"),
    -32004: ErrorDetail("Unsupported operation", "Operation is not supported"),
    -32005: ErrorDetail("Incompatible content types", "Incompatible content types between client and an agent"),
}

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


class TaskParams(BaseModel):
    id: str
    sessionId: Optional[str] = None
    message: Message


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

class RPCMethod(Enum):
    TASK_SEND = "tasks/send"
    TASK_GET = "tasks/get"
    TASK_CANCEL = "tasks/cancel"
    TASK_PUSH = "tasks/push"
    TASK_RESUBSCRIBE = "tasks/resubscribe"
    TASK_PUSH_GET = "tasks/push/get"
    TASK_PUSH_UPDATE = "tasks/push/update"
    TASK_PUSH_DELETE = "tasks/push/delete"

class RPCRequest(BaseModel):
    jsonrpc: str
    id: UUID4
    method: RPCMethod
    params: TaskParams
    acceptedOutputModes: Optional[List[str]] = None
    pushNotification: Optional[Dict[str, object]] = None
    historyLength: Optional[int] = None
    metadata: Optional[Dict[str, object]] = {}

class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: UUID4
    result: Result

