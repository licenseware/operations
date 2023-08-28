import sys

import fastapi
from opentelemetry import metrics
from opentelemetry import trace as _trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.instrumentation.urllib import URLLibInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from logger import get_logger
from settings import conf

logger = get_logger(__name__, level=conf.LOG_LEVEL)


def _get_trace_provider(service_name: str) -> TracerProvider:
    assert conf.OTEL_EXPORTER_OTLP_ENDPOINT, "OTEL_EXPORTER_OTLP_ENDPOINT is not set"

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: service_name}),
        active_span_processor=BatchSpanProcessor(
            OTLPSpanExporter(endpoint=conf.OTEL_EXPORTER_OTLP_ENDPOINT)
        ),
    )
    _trace.set_tracer_provider(tracer_provider)

    return tracer_provider


def get_meter_provider(service_name: str):
    resource = Resource(attributes={SERVICE_NAME: service_name})

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(conf.OTEL_EXPORTER_OTLP_ENDPOINT)
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    return provider


def _get_propagator():
    return TraceContextTextMapPropagator()


_system_metrics_config = {
    "system.cpu.time": ["idle", "user", "system", "irq"],
    "system.cpu.utilization": ["idle", "user", "system", "irq"],
    "system.memory.usage": ["used", "free", "cached"],
    "system.memory.utilization": ["used", "free", "cached"],
    "system.swap.usage": ["used", "free"],
    "system.swap.utilization": ["used", "free"],
    "system.disk.io": ["read", "write"],
    "system.disk.operations": ["read", "write"],
    "system.disk.time": ["read", "write"],
    "system.network.dropped.packets": ["transmit", "receive"],
    "system.network.packets": ["transmit", "receive"],
    "system.network.errors": ["transmit", "receive"],
    "system.network.io": ["transmit", "receive"],
    "system.network.connections": ["family", "type"],
    "system.thread_count": None,
    "process.runtime.memory": ["rss", "vms"],
    "process.runtime.cpu.time": ["user", "system"],
}


def _instrument_fastapi(fastapi_app):
    return FastAPIInstrumentor().instrument_app(fastapi_app)


def _instrument_asgi(asgi_app):
    return OpenTelemetryMiddleware(asgi_app)


def trace(span_name: str, trace_name: str = None):
    return (
        _trace.get_tracer_provider()
        .get_tracer(trace_name or __name__)
        .start_as_current_span(span_name)
    )


def init_tracing(fastapi_app: fastapi.FastAPI, service_name):
    _get_trace_provider(service_name)
    _instrument_fastapi(fastapi_app)
    _instrument_asgi(fastapi_app)

    @fastapi_app.middleware("http")
    async def _propagate_traceparent(request: fastapi.Request, call_next):
        traceparent = request.headers.get("traceparent")
        carrier = {"traceparent": traceparent} if traceparent else {}
        request.state.span = _trace.get_current_span(_get_propagator().extract(carrier))

        return await call_next(request)

    return fastapi_app
