"""
OSINT metrics tracking for monitoring and analytics.

Tracks success rates, latency, and errors for OSINT operations.
"""

import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class OSINTSource(str, Enum):
    """OSINT data sources."""

    GOOGLE_MAPS = "google_maps"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class OSINTMetric(BaseModel):
    """Single OSINT operation metric."""

    timestamp: datetime = Field(default_factory=datetime.now)
    business_name: str
    source: OSINTSource
    success: bool
    latency_ms: int
    error: Optional[str] = None
    dvs_score: Optional[float] = None


class OSINTMetricsCollector:
    """Collects and aggregates OSINT metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: list[OSINTMetric] = []
        self.max_metrics = 1000  # Keep last 1000 metrics in memory

    def record(
        self,
        business_name: str,
        source: OSINTSource,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None,
        dvs_score: Optional[float] = None,
    ) -> None:
        """
        Record OSINT operation metric.

        Args:
            business_name: Business name searched
            source: OSINT source used
            success: Whether operation succeeded
            latency_ms: Operation latency in milliseconds
            error: Error message if failed
            dvs_score: Digital Veracity Score if calculated
        """
        metric = OSINTMetric(
            business_name=business_name,
            source=source,
            success=success,
            latency_ms=latency_ms,
            error=error,
            dvs_score=dvs_score,
        )

        self.metrics.append(metric)

        # Trim old metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]

        # Log metric
        status = "SUCCESS" if success else "FAILED"
        logger.info(
            f"OSINT {source.value} {status} for '{business_name}' "
            f"({latency_ms}ms, DVS={dvs_score})"
        )

    def get_success_rate(self, source: Optional[OSINTSource] = None) -> float:
        """
        Calculate success rate for OSINT operations.

        Args:
            source: Optional source filter

        Returns:
            Success rate as percentage (0.0-100.0)
        """
        filtered_metrics = self.metrics
        if source:
            filtered_metrics = [m for m in self.metrics if m.source == source]

        if not filtered_metrics:
            return 0.0

        successful = sum(1 for m in filtered_metrics if m.success)
        return (successful / len(filtered_metrics)) * 100

    def get_average_latency(self, source: Optional[OSINTSource] = None) -> float:
        """
        Calculate average latency for OSINT operations.

        Args:
            source: Optional source filter

        Returns:
            Average latency in milliseconds
        """
        filtered_metrics = self.metrics
        if source:
            filtered_metrics = [m for m in self.metrics if m.source == source]

        if not filtered_metrics:
            return 0.0

        total_latency = sum(m.latency_ms for m in filtered_metrics)
        return total_latency / len(filtered_metrics)

    def get_average_dvs(self) -> float:
        """
        Calculate average DVS score.

        Returns:
            Average DVS score (0.0-1.0)
        """
        dvs_scores = [
            m.dvs_score for m in self.metrics if m.dvs_score is not None]

        if not dvs_scores:
            return 0.0

        return sum(dvs_scores) / len(dvs_scores)

    def get_stats(self) -> dict:
        """
        Get comprehensive OSINT statistics.

        Returns:
            Dict with success rates, latencies, and error counts
        """
        return {
            "total_operations": len(self.metrics),
            "overall_success_rate": self.get_success_rate(),
            "average_latency_ms": self.get_average_latency(),
            "average_dvs": self.get_average_dvs(),
            "by_source": {
                "google_maps": {
                    "success_rate": self.get_success_rate(OSINTSource.GOOGLE_MAPS),
                    "avg_latency_ms": self.get_average_latency(OSINTSource.GOOGLE_MAPS),
                },
                "instagram": {
                    "success_rate": self.get_success_rate(OSINTSource.INSTAGRAM),
                    "avg_latency_ms": self.get_average_latency(OSINTSource.INSTAGRAM),
                },
                "facebook": {
                    "success_rate": self.get_success_rate(OSINTSource.FACEBOOK),
                    "avg_latency_ms": self.get_average_latency(OSINTSource.FACEBOOK),
                },
            },
            "recent_errors": [
                {"source": m.source.value, "error": m.error, "timestamp": m.timestamp}
                for m in self.metrics[-10:]
                if not m.success and m.error
            ],
        }


# Global metrics collector
osint_metrics = OSINTMetricsCollector()
