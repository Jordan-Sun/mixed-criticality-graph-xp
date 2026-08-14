"""Validate task-set definition files produced by experiment.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


class TaskSetFormatError(ValueError):
    """Raised when a task-set file does not follow the generated text format."""


class _LineReader:
    def __init__(self, path: Path) -> None:
        try:
            self.lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise TaskSetFormatError(f"cannot read {path}: {error}") from error
        self.position = 0

    def read_integers(self, field_names: tuple[str, ...], context: str) -> tuple[int, ...]:
        if self.position >= len(self.lines):
            raise TaskSetFormatError(f"unexpected end of file while reading {context}")

        line_number = self.position + 1
        line = self.lines[self.position]
        self.position += 1
        fields = line.split()
        if len(fields) != len(field_names):
            expected = " ".join(field_names)
            raise TaskSetFormatError(
                f"line {line_number}: expected {len(field_names)} integers "
                f"({expected}) for {context}, got {len(fields)}"
            )

        try:
            return tuple(int(field) for field in fields)
        except ValueError as error:
            raise TaskSetFormatError(f"line {line_number}: expected integers for {context}, got {line!r}") from error


def validate_task_set_file(path: Path, non_clairvoyant: bool = False) -> tuple[int, int, list[str]]:
    """Return the set count, task count, and all semantic violations in *path*."""
    reader = _LineReader(path)
    (declared_set_count,) = reader.read_integers(("task_set_count",), "file header")
    if declared_set_count < 0:
        raise TaskSetFormatError("line 1: task-set count must be non-negative")

    violations: list[str] = []
    total_tasks = 0

    for set_index in range(declared_set_count):
        (task_count,) = reader.read_integers(("task_count",), f"task set {set_index}")
        if task_count < 0:
            raise TaskSetFormatError(
                f"line {reader.position}: task count for task set {set_index} must be non-negative"
            )

        for task_index in range(task_count):
            context = f"task set {set_index}, task {task_index}"
            period, deadline, criticality = reader.read_integers(("T", "D", "X"), context)
            c_lo, c_hi, c_s = reader.read_integers(("C_lo", "C_hi", "C_s"), context)
            total_tasks += 1

            values = f"task=(T={period}, D={deadline}, X={criticality}, C_lo={c_lo}, C_hi={c_hi}, C_s={c_s})"
            prefix = f"task set {set_index}, task {task_index}: "

            if not c_s <= c_lo <= c_hi <= period:
                violations.append(prefix + f"expected C_s <= C_lo <= C_hi <= T; {values}")

            if criticality == 1:
                if c_s != 0:
                    violations.append(prefix + f"LO task must have C_s = 0; {values}")
            elif criticality == 2:
                if non_clairvoyant and c_s != c_lo:
                    violations.append(prefix + f"non-clairvoyant HI task must have C_s = C_lo; {values}")
            else:
                violations.append(prefix + f"criticality X must be 1 (LO) or 2 (HI); {values}")

    if reader.position != len(reader.lines):
        extra_line = reader.position + 1
        raise TaskSetFormatError(f"line {extra_line}: extra data after the declared {declared_set_count} task sets")

    return declared_set_count, total_tasks, violations


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a generated task-set definition file.")
    parser.add_argument("input_file", type=Path, help="generated task-set .txt file")
    parser.add_argument(
        "--non-clairvoyant",
        action="store_true",
        help="also require C_s = C_lo for every HI task",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        set_count, task_count, violations = validate_task_set_file(
            args.input_file, non_clairvoyant=args.non_clairvoyant
        )
    except TaskSetFormatError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        print(
            f"Validation failed: {len(violations)} violation(s) in {set_count} task set(s) and {task_count} task(s).",
            file=sys.stderr,
        )
        return 1

    print(f"Valid: {set_count} task set(s), {task_count} task(s) checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
