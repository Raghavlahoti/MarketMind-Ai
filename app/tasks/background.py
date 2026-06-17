# ============================================================================
# MARKETMIND AI - BACKGROUND TASKS SCHEDULER INTERFACE
# ============================================================================

from typing import Any, Dict
from uuid import UUID


class BackgroundTaskManagerInterface:
    """Interface outlining scheduling and queueing operations for task execution."""

    async def enqueue_research_job(self, run_id: UUID, configuration: Dict[str, Any]) -> None:
        """Dispatches an asynchronous stock research task to Celery or worker threads."""
        raise NotImplementedError

    async def trigger_price_alerts_check(self, stock_id: UUID, current_price: float) -> None:
        """Enqueues check job verifying active user alert triggers against new prices."""
        raise NotImplementedError
