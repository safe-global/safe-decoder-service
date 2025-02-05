import datetime
import logging

from pydantic.main import BaseModel


class HttpRequestLog(BaseModel):
    dbSession: str
    url: str
    method: str
    body: str | None = None
    startTime: datetime.datetime


class HttpResponseLog(BaseModel):
    status: int
    endTime: datetime.datetime
    totalTime: int


class ErrorDetail(BaseModel):
    function: str
    line: int
    exceptionInfo: str


class TaskInfo(BaseModel):
    name: str
    id: str
    kwargs: dict | None = None
    args: tuple


class ContextMessageLog(BaseModel):
    httpRequest: HttpRequestLog | None = None
    httpResponse: HttpResponseLog | None = None
    errorDetail: ErrorDetail | None = None
    taskDetail: TaskInfo | None = None


class JsonLog(BaseModel):
    level: str
    timestamp: datetime.datetime
    context: str
    message: str
    contextMessage: ContextMessageLog | dict | None = None


class JsonLogger(logging.Formatter):
    """
    Json formatter
    """

    def format(self, record):
        if record.levelname == "ERROR":
            error_detail = ErrorDetail(
                function=record.funcName,
                line=record.lineno,
                exceptionInfo=str(record.exc_info),
            )
            # Add the error detail to a received contextMessage
            if hasattr(record, "contextMessage"):
                record.contextMessage.errorDetail = error_detail
            else:
                record.contextMessage = ContextMessageLog(errorDetail=error_detail)

        json_log = JsonLog(
            level=record.levelname,
            timestamp=datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc
            ),
            context=f"{record.name}.{record.funcName}",
            message=record.getMessage(),
            contextMessage=(
                record.contextMessage if hasattr(record, "contextMessage") else None
            ),
        )

        return json_log.model_dump_json(exclude_none=True)


class HttpRequestFilter(logging.Filter):
    """
    Add default information for any log initiated by a request
    """

    def __init__(self, session_id=None, url=None, method=None, start_time=None):
        super().__init__()
        # Set context_id via constructor or use a default value
        self.session_id = session_id
        self.url = url
        self.method = method
        self.start_time = start_time

    def filter(self, record):
        http_request = HttpRequestLog(
            dbSession=self.session_id,
            url=str(self.url),
            method=self.method,
            startTime=self.start_time,
        )
        if hasattr(record, "contextMessage"):
            # Add request
            record.contextMessage["httpRequest"] = http_request
        else:
            record.contextMessage = ContextMessageLog(httpRequest=http_request)

        return True
