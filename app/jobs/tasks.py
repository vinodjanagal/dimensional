"""Background tasks executed by the Arq worker.

Each task receives `ctx` (the worker's shared context, populated in
`app.jobs.worker.on_startup`) followed by the arguments passed to
`enqueue_job`.
"""

import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID

from arq import Retry
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.jobs.config import (
    MAX_JOB_TRIES,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
)
from app.models import Formula, Job, Note, Quantity
from app.repositories import unit_repository
from app.services.expression import ExpressionError, evaluate_dimension

logger = logging.getLogger(__name__)


def is_retryable_error(exc: Exception) -> bool:
    """Identify transient infrastructure and PostgreSQL transaction errors."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    if isinstance(exc, DBAPIError):
        # 1. Connection was severed or dropped by pool
        if exc.connection_invalidated:
            return True

        # 2. Check SQLSTATE or driver pgcode
        original = exc.orig
        sqlstate = (
            getattr(original, "sqlstate", None)
            or getattr(original, "pgcode", None)
        )
        return bool(
            sqlstate
            and (
                sqlstate.startswith("08")
                or sqlstate in {"40001", "40P01", "55P03"}
            )
        )

    return False


async def update_job_state(
    sessionmaker,
    job_id: UUID,
    status: str,
    error: str | None = None,
    result: dict | None = None,
) -> None:
    """Persist job state in a fresh database session.

    Propagates exceptions so callers can handle or classify persistence failures.
    """
    async with sessionmaker() as db:
        job = await db.get(Job, job_id)
        if job is None:
            raise RuntimeError(f"Job {job_id} not found")

        job.status = status
        job.error = error

        if status == "running":
            job.started_at = datetime.now(timezone.utc)

        if result is not None:
            job.result = result

        # Clear stale results if not in terminal success state
        if status != "done":
            job.result = None

        if status in {"done", "failed"}:
            job.finished_at = datetime.now(timezone.utc)
        else:
            job.finished_at = None

        await db.commit()


async def _best_effort_update_state(
    sessionmaker,
    job_id: UUID,
    status: str,
    error: str | None = None,
) -> None:
    """Attempt to record failure/retry state without masking the primary exception if DB is down."""
    try:
        await update_job_state(sessionmaker, job_id, status=status, error=error)
    except Exception as db_exc:
        logger.warning(
            "job.state_persistence_failed",
            extra={
                "job_id": str(job_id),
                "target_status": status,
                "db_error": str(db_exc),
            },
        )


async def analyze_note(
    ctx: dict,
    note_id: int,
    user_id: int,
    job_id: str,
) -> dict:
    """Analyze a note's content and formulas with robust retry handling."""
    sessionmaker = ctx["db_sessionmaker"]
    started_at = perf_counter()
    job_try = ctx.get("job_try", 1)
    job_uuid = UUID(job_id)

    logger.info(
        "job.started",
        extra={
            "event": "job.started",
            "job_id": job_id,
            "job_type": "analyze_note",
            "note_id": note_id,
            "job_try": job_try,
        },
    )

    try:
        # 1. Mark running inside try so initial DB connection errors can be retried
        await update_job_state(sessionmaker, job_uuid, status="running")

        # 2. Validate payload consistency with persisted job
        async with sessionmaker() as db:
            job = await db.get(Job, job_uuid)
            if job is None:
                raise RuntimeError(f"Job {job_id} not found")
            if job.note_id != note_id or job.user_id != user_id:
                raise ValueError(
                    f"Job payload mismatch: expected note_id={job.note_id}, user_id={job.user_id}; "
                    f"got note_id={note_id}, user_id={user_id}"
                )

            # 3. Execute analysis (enforces note ownership)
            result = await _run_analysis(db, note_id, user_id)

        # 4. Success: must cleanly persist 'done'. Does NOT swallow DB failures.
        await update_job_state(
            sessionmaker,
            job_uuid,
            status="done",
            result=result,
        )

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "job.completed",
            extra={
                "event": "job.completed",
                "job_id": job_id,
                "duration_ms": duration_ms,
                "formula_count": result.get("formula_count"),
                "quantity_count": result.get("quantity_count"),
                "invalid_formula_count": len(result.get("invalid_formulas", [])),
            },
        )
        return result

    except Exception as exc:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        error_message = f"{type(exc).__name__}: {exc}"

        # 5. Check if transient infrastructure failure
        if is_retryable_error(exc) and job_try < MAX_JOB_TRIES:
            defer_seconds = min(
                RETRY_BASE_DELAY_SECONDS * (2 ** (job_try - 1)),
                RETRY_MAX_DELAY_SECONDS,
            )

            # Best-effort DB update so a dead DB doesn't block Arq from scheduling the retry
            await _best_effort_update_state(
                sessionmaker,
                job_uuid,
                status="retrying",
                error=error_message,
            )

            logger.warning(
                "job.retrying",
                extra={
                    "event": "job.retrying",
                    "job_id": job_id,
                    "job_try": job_try,
                    "max_tries": MAX_JOB_TRIES,
                    "defer_seconds": defer_seconds,
                    "error": error_message,
                },
            )
            raise Retry(defer=defer_seconds) from exc

        # 6. Permanent failure OR retries exhausted
        await _best_effort_update_state(
            sessionmaker,
            job_uuid,
            status="failed",
            error=error_message,
        )

        logger.exception(
            "job.failed",
            extra={
                "event": "job.failed",
                "job_id": job_id,
                "job_try": job_try,
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
            },
        )
        raise


async def _run_analysis(db, note_id: int, user_id: int) -> dict:
    """Compute the analysis result using database aggregations and verifying note ownership."""
    note = await db.scalar(
        select(Note).where(
            Note.id == note_id,
            Note.owner_id == user_id,
        )
    )
    if note is None:
        raise RuntimeError(f"Note {note_id} not found or not accessible")

    content = note.content or ""
    word_count = len(content.split())
    char_count = len(content)
    line_count = content.count("\n") + (1 if content else 0)

    # Formulas
    formulas_res = await db.execute(
        select(Formula).where(Formula.note_id == note_id)
    )
    formulas = list(formulas_res.scalars().all())

    # Build lookup over all units for expression evaluation
    all_units = await unit_repository.list_all(db)
    lookup = {u.symbol: tuple(u.dimension) for u in all_units}

    invalid_formulas: list[dict] = []
    for f in formulas:
        try:
            expr_dim = evaluate_dimension(f.expression, lookup.__getitem__)
        except ExpressionError as e:
            invalid_formulas.append(
                {"formula_id": f.id, "name": f.name, "reason": str(e)}
            )
            continue

        expected = tuple(f.result_unit.dimension)
        if expr_dim != expected:
            invalid_formulas.append(
                {
                    "formula_id": f.id,
                    "name": f.name,
                    "reason": (
                        f"dimension {list(expr_dim)} != "
                        f"declared unit {f.result_unit.symbol} "
                        f"{list(expected)}"
                    ),
                }
            )

    # Quantities: SQL aggregate COUNT directly on the database
    count_stmt = select(func.count(Quantity.id)).where(Quantity.note_id == note_id)
    quantity_count = (await db.scalar(count_stmt)) or 0

    return {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": line_count,
        "formula_count": len(formulas),
        "quantity_count": quantity_count,
        "invalid_formulas": invalid_formulas,
    }