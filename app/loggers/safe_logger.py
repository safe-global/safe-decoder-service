# SPDX-License-Identifier: FSL-1.1-MIT
import datetime
import logging
import traceback
from contextvars import ContextVar, Token

from pydantic.main import BaseModel

logger = logging.getLogger(__name__)


class HttpRequestLog(BaseModel):
    url: str
    method: str
    route: str | None = None
    body: str | None = None
    startTime: datetime.datetime


class HttpResponseLog(BaseModel):
    status: int
    endTime: datetime.datetime
    totalTime: int


class ErrorInfo(BaseModel):
    function: str
    line: int
    exceptionInfo: str | None = None


class TaskInfo(BaseModel):  # type: ignore
    name: str
    id: str
    kwargs: dict | None = None
    args: tuple


class ContextMessageLog(BaseModel):
    dbSession: str | None = None
    httpRequest: HttpRequestLog | None = None
    httpResponse: HttpResponseLog | None = None
    errorInfo: ErrorInfo | None = None
    taskInfo: TaskInfo | None = None


class JsonLog(BaseModel):
    level: str
    timestamp: datetime.datetime
    context: str
    message: str
    contextMessage: ContextMessageLog | dict | None = None


class SafeJsonFormatter(logging.Formatter):
    """
    Json formatter with following schema
    {
        level: str,
        timestamp: Datetime,
        context: str,
        message: str,
        contextMessage: <contextMessage>
    }
    """

    def format(self, record):
        if record.levelname == "ERROR":
            exception_info: str | None = None
            # Check if the error contains exception data
            if record.exc_info:
                exc_type, exc_value, exc_tb = record.exc_info
                exception_info = "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                )
            record.error_detail = ErrorInfo(
                function=record.funcName,
                line=record.lineno,
                exceptionInfo=exception_info,
            )

        context_message = ContextMessageLog(
            dbSession=getattr(record, "db_session", None),
            httpRequest=getattr(record, "http_request", None),
            httpResponse=getattr(record, "http_response", None),
            errorInfo=getattr(record, "error_detail", None),
            taskInfo=getattr(record, "task_detail", None),
        )

        json_log = JsonLog(
            level=record.levelname,
            timestamp=datetime.datetime.fromtimestamp(record.created, datetime.UTC),
            context=f"{record.module}.{record.funcName}",
            message=record.getMessage(),
            contextMessage=(
                context_message
                if len(context_message.model_dump(exclude_none=True))
                else None
            ),
        )

        return json_log.model_dump_json(exclude_none=True)


_task_info: ContextVar["TaskInfo"] = ContextVar("task_info")


def log_record_factory(*args, **kwargs) -> logging.LogRecord:
    """
    Inject both db_session and task_detail into every log record.
    """
    record = logging.LogRecord(*args, **kwargs)
    try:
        from app.datasources.db.database import (  # noqa: PLC0415
            _db_session_context,
        )

        record.db_session = _db_session_context.get()
    except LookupError:
        pass
    try:
        record.task_detail = _task_info.get()
    except LookupError:
        pass
    return record


logging.setLogRecordFactory(log_record_factory)


def set_task_context(task_message) -> Token[TaskInfo]:
    """
    Set the taskInfo ContextVar so logs emitted while the task runs include its detail.
    Returns the token to later reset it with `reset_task_context`.
    """
    task_detail = TaskInfo(
        name=task_message.task_name,
        id=task_message.task_id,
        kwargs=task_message.kwargs,
        args=task_message.args,
    )
    return _task_info.set(task_detail)


def reset_task_context(token: Token[TaskInfo]) -> None:
    _task_info.reset(token)


def get_task_info() -> TaskInfo:
    return _task_info.get()
