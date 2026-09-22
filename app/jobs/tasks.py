"""Background tasks executed by the Arq worker.

Each task receives `ctx` (the worker's shared context, populated in
`app.jobs.worker.on_startup`) followed by the arguments passed to
`enqueue_job`.

Tasks are responsible for updating the Job row's status as they
progress: queued -> running -> done | failed.
"""

from datetime import datetime, timezone
from uuid import UUID

from app.models import Formula, Job
from app.repositories import formula_repository, unit_repository
from app.services.expression import ExpressionError, evaluate_dimension


async def analyze_note(
    ctx: dict,
    note_id: int,
    user_id: int,
    job_id: str,
) -> dict:
    """Analyze a note's content and attached objects.

    Returns a dict with counts and a re-validation report for every
    formula attached to the note.
    """
    sessionmaker = ctx["db_sessionmaker"]

    async with sessionmaker() as db:
        job = await db.get(Job, UUID(job_id))
        if job is None:
            # The row vanished between enqueue and execution. Nothing
            # useful we can do here — log and exit.
            raise RuntimeError(f"Job {job_id} not found")

        # Transition: queued -> running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            result = await _run_analysis(db, note_id)
            job.status = "done"
            job.result = result
        except Exception as exc:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()

        return result


async def _run_analysis(db, note_id: int) -> dict:
    """Compute the analysis result. Pure-ish: DB reads, no writes."""
    from sqlalchemy import select

    from app.models import Note, Quantity

    note = await db.get(Note, note_id)
    if note is None:
        raise RuntimeError(f"Note {note_id} not found")

    content = note.content or ""
    word_count = len(content.split())
    char_count = len(content)
    line_count = content.count("\n") + (1 if content else 0)

    # Formulas
    formulas = (
        await db.execute(select(Formula).where(Formula.note_id == note_id))
    ).scalars().all()

    # Build a lookup over all units for expression evaluation
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

    # Quantities
    quantity_count = (
        await db.execute(
            select(Quantity).where(Quantity.note_id == note_id)
        )
    ).scalars().all()

    return {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": line_count,
        "formula_count": len(formulas),
        "quantity_count": len(quantity_count),
        "invalid_formulas": invalid_formulas,
    }