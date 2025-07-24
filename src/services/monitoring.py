"""Monitoring and observability setup using OpenTelemetry and Prometheus."""

from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider
from prometheus_client import Counter, Gauge, Histogram

# Custom metrics
sync_counter = Counter(
    'gsc_sync_total',
    'Total sync operations',
    ['site_id', 'status']
)

query_histogram = Histogram(
    'gsc_query_duration_seconds',
    'Query duration in seconds',
    ['query_type']
)

active_syncs = Gauge(
    'gsc_active_syncs',
    'Number of active sync operations'
)

api_request_counter = Counter(
    'gsc_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status_code']
)

cache_hit_counter = Counter(
    'gsc_cache_hits_total',
    'Cache hit/miss counter',
    ['cache_level', 'hit']
)

db_connection_gauge = Gauge(
    'gsc_db_connections',
    'Number of database connections',
    ['db_type']
)


def setup_monitoring() -> None:
    """Setup OpenTelemetry and Prometheus monitoring."""
    # Create resource
    resource = Resource.create({
        "service.name": "gsc-db-refactor",
        "service.version": "2.0.0",
    })
    
    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(ConsoleSpanExporter())
    tracer_provider.add_span_processor(span_processor)
    set_tracer_provider(tracer_provider)
    
    # Setup metrics
    metric_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    set_meter_provider(meter_provider)
    
    # Instrument libraries
    HTTPXClientInstrumentor().instrument()
    SQLite3Instrumentor().instrument()


class MonitoredService:
    """Base class for services with monitoring."""
    
    def __init__(self, service_name: str):
        """Initialize monitored service."""
        self.tracer = trace.get_tracer(service_name)
        self.meter = metrics.get_meter(service_name)
        
        # Create service-specific metrics
        self.request_counter = self.meter.create_counter(
            f"{service_name}_requests_total",
            description=f"Total requests to {service_name}"
        )
        
        self.error_counter = self.meter.create_counter(
            f"{service_name}_errors_total",
            description=f"Total errors in {service_name}"
        )
        
        self.duration_histogram = self.meter.create_histogram(
            f"{service_name}_duration_seconds",
            description=f"Request duration for {service_name}"
        )
    
    def record_request(self, operation: str, status: str = "success") -> None:
        """Record a request metric."""
        self.request_counter.add(1, {"operation": operation, "status": status})
    
    def record_error(self, operation: str, error_type: str) -> None:
        """Record an error metric."""
        self.error_counter.add(1, {"operation": operation, "error_type": error_type})
    
    def create_span(self, name: str) -> trace.Span:
        """Create a new trace span."""
        return self.tracer.start_span(name)


class SyncMonitor(MonitoredService):
    """Monitor for sync operations."""
    
    def __init__(self):
        """Initialize sync monitor."""
        super().__init__("sync_service")
    
    def start_sync(self, site_id: int) -> None:
        """Record sync start."""
        active_syncs.inc()
        sync_counter.labels(site_id=site_id, status="started").inc()
    
    def complete_sync(self, site_id: int, success: bool = True) -> None:
        """Record sync completion."""
        active_syncs.dec()
        status = "success" if success else "failed"
        sync_counter.labels(site_id=site_id, status=status).inc()
    
    def record_sync_stats(self, site_id: int, stats: dict) -> None:
        """Record detailed sync statistics."""
        with self.create_span("record_sync_stats") as span:
            span.set_attribute("site_id", site_id)
            span.set_attribute("records_inserted", stats.get("inserted", 0))
            span.set_attribute("records_updated", stats.get("updated", 0))
            span.set_attribute("records_skipped", stats.get("skipped", 0))


class QueryMonitor(MonitoredService):
    """Monitor for database queries."""
    
    def __init__(self):
        """Initialize query monitor."""
        super().__init__("query_service")
    
    @query_histogram.labels(query_type='ranking_data').time()
    def monitor_ranking_query(self, func):
        """Decorator to monitor ranking queries."""
        async def wrapper(*args, **kwargs):
            with self.create_span("ranking_query") as span:
                span.set_attribute("site_id", kwargs.get("site_id"))
                span.set_attribute("date_range", str(kwargs.get("date_range")))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("result_count", len(result.get("data", [])))
                    self.record_request("ranking_query", "success")
                    return result
                except Exception as e:
                    span.record_exception(e)
                    self.record_error("ranking_query", type(e).__name__)
                    raise
        
        return wrapper


class CacheMonitor(MonitoredService):
    """Monitor for cache operations."""
    
    def __init__(self):
        """Initialize cache monitor."""
        super().__init__("cache_service")
    
    def record_hit(self, cache_level: str = "memory") -> None:
        """Record cache hit."""
        cache_hit_counter.labels(cache_level=cache_level, hit="true").inc()
    
    def record_miss(self, cache_level: str = "memory") -> None:
        """Record cache miss."""
        cache_hit_counter.labels(cache_level=cache_level, hit="false").inc()