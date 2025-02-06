import datetime
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator

from pydantic.main import BaseModel


class HttpRequestLog(BaseModel):
    url: str
    method: str
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


class TaskInfo(BaseModel):
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
            record.error_detail = ErrorInfo(
                function=record.funcName,
                line=record.lineno,
                exceptionInfo=str(record.exc_info),
            )
        context_message = ContextMessageLog(
            dbSession=record.db_session if hasattr(record, "db_session") else None,
            httpRequest=(
                record.http_request if hasattr(record, "http_request") else None
            ),
            httpResponse=(
                record.http_response if hasattr(record, "http_response") else None
            ),
            errorInfo=(
                record.error_detail if hasattr(record, "error_detail") else None
            ),
            taskInfo=record.task_detail if hasattr(record, "task_detail") else None,
        )

        json_log = JsonLog(
            level=record.levelname,
            timestamp=datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc
            ),
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


@contextmanager
def logging_task_context(task_message) -> Generator[None, None, None]:
    """
    Set taskInfo ContextVar, at the end it will be removed.
    This context is designed to be retrieved during logs to get information about the task.

    :param task_message:
    :return:
    """
    task_detail = TaskInfo(
        name=task_message.actor_name,
        id=task_message.message_id,
        kwargs=task_message.kwargs,
        args=task_message.args,
    )
    token = _task_info.set(task_detail)
    try:
        yield
    finally:
        _task_info.reset(token)


def get_task_info() -> TaskInfo:
    return _task_info.get()
