import datetime
import logging

from pydantic.main import BaseModel


class HttpRequestLog(BaseModel):
    url: str
    method: str
    body: str | None = None
    startTime: datetime.datetime


class HttpResponseLog(BaseModel):
    status: int
    end_time: datetime.datetime
    totalTime: int


class ErrorDetail(BaseModel):
    function: str
    line: int


class ContextMessageLog(BaseModel):
    httpRequest: HttpRequestLog | None = None
    httpResponse: HttpResponseLog | None = None
    errorDetail: ErrorDetail | None = None


class JsonLog(BaseModel):
    level: str
    timestamp: datetime.datetime
    context: str
    message: str
    contextMessage: ContextMessageLog | dict


class JsonLogger(logging.Formatter):
    """
    Json formatter
    """

    def format(self, record):
        context_message = {}

        if record.levelname == "ERROR":
            error_message = ErrorDetail(function=record.funcName, line=record.lineno)
            context_message["errorDetail"] = error_message.model_dump()

        json_log = JsonLog(
            level=record.levelname,
            timestamp=datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc
            ),
            context=record.module,
            message=record.getMessage(),
            contextMessage=(
                record.context_message
                if hasattr(record, "context_message")
                else context_message
            ),
        )

        return json_log.model_dump_json(exclude_none=True)
