"""Optional Sentry + OpenTelemetry bootstrap."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger("sunny.observability")

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|csrf|session|api[_-]?key|totp)",
    re.I,
)
_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-csrf-token",
    "x-api-key",
}


def _scrub_mapping(data: Any) -> Any:
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            if _SENSITIVE_KEY.search(str(key)):
                out[key] = "[Filtered]"
            else:
                out[key] = _scrub_mapping(value)
        return out
    if isinstance(data, list):
        return [_scrub_mapping(item) for item in data]
    return data


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Drop secrets from breadcrumbs, request bodies, and headers."""
    request = event.get("request") or {}
    headers = request.get("headers")
    if isinstance(headers, dict):
        request["headers"] = {
            k: ("[Filtered]" if k.lower() in _SENSITIVE_HEADERS or _SENSITIVE_KEY.search(k) else v)
            for k, v in headers.items()
        }
    if "cookies" in request:
        request["cookies"] = "[Filtered]"
    if "data" in request:
        request["data"] = _scrub_mapping(request["data"])
    event["request"] = request

    # Never attach PII identity — role is tagged separately.
    event.pop("user", None)

    for crumb in event.get("breadcrumbs", {}).get("values", []) if isinstance(event.get("breadcrumbs"), dict) else []:
        if isinstance(crumb.get("data"), dict):
            crumb["data"] = _scrub_mapping(crumb["data"])

    event["extra"] = _scrub_mapping(event.get("extra") or {})
    return event


def init_observability(app) -> None:
    # Disabled in local unless SENTRY_DSN is explicitly set (empty in .env.example).
    if settings.sentry_dsn and settings.environment != "development":
        _init_sentry(enabled_traces=True)
    elif settings.sentry_dsn and settings.environment == "development":
        # DSN present in dev: capture errors so /debug/boom can be verified; no traces by default.
        _init_sentry(enabled_traces=False)
    else:
        logger.info("Sentry disabled (no SENTRY_DSN)")

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": "studio-sunny-hq-api"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
            )
            trace.set_tracer_provider(provider)
            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry enabled")
        except Exception as exc:
            logger.warning("OpenTelemetry init failed: %s", exc)


def _init_sentry(*, enabled_traces: bool) -> None:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if enabled_traces else 0.0,
            send_default_pii=False,
            before_send=_before_send,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        sentry_sdk.set_tag("service", "api")
        logger.info("Sentry enabled (traces=%s)", enabled_traces)
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


def tag_request_role(role_key: str | None) -> None:
    if not role_key:
        return
    try:
        import sentry_sdk

        sentry_sdk.set_tag("user.role", role_key)
    except Exception:
        pass
