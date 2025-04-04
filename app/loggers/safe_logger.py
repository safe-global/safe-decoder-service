import datetime
import logging
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator

from pydantic.main import BaseModel

logger = logging.getLogger(__name__)


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
        logger.debug("Starting task...")
        yield
    finally:
        logger.debug("Finishing task...")
        _task_info.reset(token)


def get_task_info() -> TaskInfo:
    return _task_info.get()
