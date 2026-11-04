"""Formula service.

The critical invariant: a formula is only stored if its expression
is dimensionally consistent with its declared result unit. Any
violation is caught *before* the INSERT statement is issued.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Formula, Note, User
from app.repositories import formula_repository, unit_repository
from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.services.expression import ExpressionError, evaluate_dimension
from app.auth.permissions import get_owned_note as _get_owned_note


async def list_formulas(
    db: AsyncSession, note_id: int, user: User
) -> list[Formula]:
    await _get_owned_note(db, note_id, user)
    return await formula_repository.list_for_note(db, note_id)


async def create_formula(
    db: AsyncSession,
    note_id: int,
    user: User,
    name: str,
    expression: str,
    result_unit_symbol: str,
) -> Formula:
    # 1. Note must exist and belong to the caller
    await _get_owned_note(db, note_id, user)

    # 2. Result unit must exist
    result_unit = await unit_repository.get_by_symbol(db, result_unit_symbol)
    if result_unit is None:
        raise NotFoundError(f"Unknown unit: {result_unit_symbol!r}")

    # 3. Name must be unique within the note
    existing = await formula_repository.get_by_name(db, note_id, name)
    if existing is not None:
        raise ConflictError(
            f"A formula named {name!r} already exists in this note"
        )

    # 4. Build lookup of every unit symbol → dimension
    all_units = await unit_repository.list_all(db)
    lookup = {u.symbol: tuple(u.dimension) for u in all_units}

    # 5. Compute expression dimension; reject invalid expressions
    try:
        expr_dim = evaluate_dimension(expression, lookup.__getitem__)
    except ExpressionError as e:
        raise ValidationError(str(e)) from e

    # 6. Dimensional consistency check — the whole point of the endpoint
    expected_dim = tuple(result_unit.dimension)
    if expr_dim != expected_dim:
        raise ValidationError(
            f"Expression has dimension {list(expr_dim)}, "
            f"but unit {result_unit_symbol!r} has {list(expected_dim)}"
        )

    # 7. All checks passed — write the row
    formula = Formula(
        note_id=note_id,
        name=name,
        expression=expression,
        result_unit_id=result_unit.id,
    )

    try:
        formula = await formula_repository.create(db, formula)
        await db.commit()
        await db.refresh(formula, ["result_unit"])
        return formula
    except IntegrityError as e:
        await db.rollback()
        #Unique constraint on (note_id, name) - meaning name collided with concurrent insert
        raise ConflictError(f"A formula named {name!r} already exists in this note") from e

    except Exception:
        await db.rollback()
        raise