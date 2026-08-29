from __future__ import annotations

import logging
import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)


def mask_email(email: str) -> str:
    text = (email or "").strip()
    if "@" not in text:
        return "***"
    local, domain = text.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def redact_text(text: str) -> str:
    return EMAIL_RE.sub(lambda m: mask_email(m.group(0)), text or "")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_value(v) for k, v in record.args.items()}
            else:
                record.args = tuple(_redact_value(v) for v in record.args)
        return True


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    return value


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("moriyama_mail")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
