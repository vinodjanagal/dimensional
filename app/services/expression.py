"""Parse and evaluate the dimension of a unit expression.

Accepted grammar (subset of Python expressions):

    expr    := term (('*' | '/') term)*
    term    := factor ('**' factor)*
    factor  := NAME | NUMBER | '(' expr ')' | ('+' | '-') factor

Names refer to unit symbols (kg, m, s, N, ...).
Numbers are dimensionless scalars.

We do not execute the expression. We parse it with Python's `ast`
module and walk the tree, computing a dimension vector at each node.
This is safe against code injection and correct-by-construction for
dimensional analysis.
"""

import ast
from typing import Callable

from app.services.dimension import (
    DIMENSIONLESS,
    Dimension,
    DimensionError,
    divide,
    multiply,
    power,
)


class ExpressionError(ValueError):
    """Raised when an expression is invalid or unsupported."""


def _unsupported(node: ast.AST) -> ExpressionError:
    return ExpressionError(
        f"Unsupported syntax: {type(node).__name__}. "
        f"Only names, numbers, '*', '/', '**', parentheses, "
        f"and unary +/- are allowed."
    )


def parse_expression(expression: str) -> ast.Expression:
    """Parse a string into a Python AST. Raises ExpressionError on failure."""
    try:
        return ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"Syntax error in expression: {e.msg}") from e


def evaluate_dimension(
    expression: str,
    lookup: Callable[[str], Dimension],
) -> Dimension:
    """Compute the dimension of `expression`.

    `lookup(symbol)` must return the dimension of the unit `symbol`.
    Raises ExpressionError on any invalid input.
    """
    tree = parse_expression(expression)
    return _visit(tree.body, lookup)


def _visit(node: ast.AST, lookup: Callable[[str], Dimension]) -> Dimension:
    # --- Name: unit symbol ---
    if isinstance(node, ast.Name):
        try:
            return lookup(node.id)
        except KeyError as e:
            raise ExpressionError(f"Unknown unit: {node.id!r}") from e

    # --- Constant: number (dimensionless) ---
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise _unsupported(node)
        return DIMENSIONLESS

    # --- Unary +/-: does not change dimension ---
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, (ast.UAdd, ast.USub)):
            return _visit(node.operand, lookup)
        raise _unsupported(node)

    # --- Binary operations ---
    if isinstance(node, ast.BinOp):
        left = _visit(node.left, lookup)

        # `**` needs a special path: the right side must be a number.
        if isinstance(node.op, ast.Pow):
            exponent = _integer_exponent(node.right)
            try:
                return power(left, exponent)
            except DimensionError as e:
                raise ExpressionError(str(e)) from e

        right = _visit(node.right, lookup)

        if isinstance(node.op, ast.Mult):
            return multiply(left, right)
        if isinstance(node.op, ast.Div):
            return divide(left, right)
        if isinstance(node.op, ast.Add):
            # Addition requires identical dimensions.
            if left != right:
                raise ExpressionError(
                    f"Cannot add {left} and {right}: dimensions differ"
                )
            return left
        if isinstance(node.op, ast.Sub):
            if left != right:
                raise ExpressionError(
                    f"Cannot subtract {right} from {left}: dimensions differ"
                )
            return left
        raise _unsupported(node)

    raise _unsupported(node)


def _integer_exponent(node: ast.AST) -> int:
    """Extract an integer exponent from a Pow's right operand.

    Only accepts a literal integer constant or unary-negative of one.
    Does not permit variables, floats, or nested expressions.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int)
    ):
        return -node.operand.value
    raise ExpressionError(
        "Exponent must be a literal integer (e.g. s ** 2 or s ** -1)"
    )