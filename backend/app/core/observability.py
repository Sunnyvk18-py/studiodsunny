"""Optional Sentry + OpenTelemetry bootstrap."""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("sunny.observability")


def init_observability(app) -> None:
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.1 if settings.environment != "development" else 0.0,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            )
            logger.info("Sentry enabled")
        except Exception as exc:
            logger.warning("Sentry init failed: %s", exc)

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
