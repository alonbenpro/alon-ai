import logging
import re
from collections.abc import Sequence
from urllib.parse import unquote, urlsplit

import structlog
from pydantic import SecretStr

from alon_ai.config import Settings


def remove_exception_details(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict.pop("exc_info", None)
    event_dict.pop("exception", None)
    event_dict.pop("stack_info", None)
    return event_dict


_REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"password|passwd|secret|token|authorization|cookie|apikey|credential|"
    r"provideroutput|providerresponse|rawresponse|responsebody|requestbody|"
    r"exception|excinfo|stackinfo|stacktrace|payload"
)
_URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"'<>]+")
_ASSIGNMENT = re.compile(
    r"(?i)((?:password|secret|token|api[_-]?key|authorization)\s*[=:]\s*)[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


class LogRedactor:
    def __init__(self, settings: Settings) -> None:
        values: set[str] = set()
        for name in type(settings).model_fields:
            value = getattr(settings, name)
            if isinstance(value, SecretStr):
                raw = value.get_secret_value()
                if raw:
                    values.add(raw)
                if name in {"database_url", "dbos_system_database_url"}:
                    parsed = urlsplit(raw)
                    if parsed.password:
                        values.add(parsed.password)
                        values.add(unquote(parsed.password))
        self._secrets = tuple(sorted(values, key=len, reverse=True))

    def _text(self, value: str) -> str:
        for secret in self._secrets:
            value = value.replace(secret, _REDACTED)

        def redact_url(match: re.Match[str]) -> str:
            candidate = match.group()
            try:
                url = urlsplit(candidate)
                if url.username is not None or _SENSITIVE_KEY.search(
                    re.sub(r"[^a-z]", "", unquote(url.query).lower())
                ):
                    return _REDACTED
            except ValueError:
                return _REDACTED
            return candidate

        value = _URL.sub(redact_url, value)
        value = _ASSIGNMENT.sub(r"\1[REDACTED]", value)
        return _BEARER.sub("Bearer [REDACTED]", value)

    def _value(self, value: object, depth: int = 0) -> object:
        if depth > 20:
            return _REDACTED
        if type(value) is str:
            return self._text(value)
        if type(value) is dict:
            return {
                self._text(key): (
                    _REDACTED
                    if _SENSITIVE_KEY.search(re.sub(r"[^a-z]", "", key.lower()))
                    else self._value(item, depth + 1)
                )
                for key, item in value.items()
                if type(key) is str
            }
        if type(value) is tuple:
            return tuple(self._value(item, depth + 1) for item in value)
        if type(value) is list:
            return [self._value(item, depth + 1) for item in value]
        if value is None or type(value) in {bool, int, float}:
            return value
        # Never invoke an arbitrary object's repr (exceptions, models, SecretStr).
        return _REDACTED

    def format_event(self, event: object, arguments: object) -> str:
        # Sanitize before interpolation: afterward an exception's message is
        # indistinguishable from an ordinary, unconfigured string.
        safe_event = self._value(event)
        safe_arguments = self._value(arguments)
        if (
            isinstance(safe_arguments, tuple)
            and len(safe_arguments) == 1
            and isinstance(safe_arguments[0], dict)
            and safe_arguments[0]
        ):
            safe_arguments = safe_arguments[0]
        try:
            return (
                str(safe_event) % safe_arguments if safe_arguments else str(safe_event)
            )
        except (TypeError, ValueError, KeyError, OverflowError):
            # A sanitized object cannot satisfy e.g. %d. Never let logging's
            # formatting-error diagnostic print the original message/arguments.
            return _REDACTED

    def format_structlog_event(
        self,
        _logger: structlog.types.WrappedLogger,
        _method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        event_dict["event"] = self.format_event(
            event_dict.get("event"), event_dict.pop("positional_args", None)
        )
        return event_dict

    def __call__(
        self,
        _logger: structlog.types.WrappedLogger,
        _method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        redacted = self._value(event_dict)
        assert isinstance(redacted, dict)
        return redacted


class SafeProcessorFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(
        self,
        redactor: LogRedactor,
        *,
        processors: Sequence[structlog.types.Processor],
        foreign_pre_chain: Sequence[structlog.types.Processor],
    ) -> None:
        super().__init__(
            processors=processors,
            foreign_pre_chain=foreign_pre_chain,
            keep_exc_info=False,
            keep_stack_info=False,
        )
        self._redactor = redactor

    def format(self, record: logging.LogRecord) -> str:
        # ProcessorFormatter calls foreign getMessage before its processors.
        # Copy the record and sanitize before that irreversible conversion.
        safe_record = logging.makeLogRecord(record.__dict__)
        if not (hasattr(safe_record, "_logger") and hasattr(safe_record, "_name")):
            safe_record.msg = self._redactor.format_event(record.msg, record.args)
            safe_record.args = ()
        return super().format(safe_record)


def configure_logging(settings: Settings) -> None:
    """Configure structured logs without exposing configuration values."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        remove_exception_details,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    renderer: structlog.types.Processor
    if settings.environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    redactor = LogRedactor(settings)
    formatter = SafeProcessorFormatter(
        redactor,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            redactor,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    for logger_name in ("httpx", "httpx2", "httpcore", "httpcore2"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            redactor.format_structlog_event,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
