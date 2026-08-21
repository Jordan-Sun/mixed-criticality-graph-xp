"""Validate task-set definition files produced by experiment.py."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
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


def _inspect_task_set_file(path: Path, non_clairvoyant: bool = False) -> tuple[int, int, list[str], list[int]]:
    reader = _LineReader(path)
    (declared_set_count,) = reader.read_integers(("task_set_count",), "file header")
    if declared_set_count < 0:
        raise TaskSetFormatError("line 1: task-set count must be non-negative")

    violations: list[str] = []
    total_tasks = 0
    hi_counts: list[int] = []

    for set_index in range(declared_set_count):
        (task_count,) = reader.read_integers(("task_count",), f"task set {set_index}")
        if task_count < 0:
            raise TaskSetFormatError(
                f"line {reader.position}: task count for task set {set_index} must be non-negative"
            )

        hi_count = 0
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
                hi_count += 1
                if non_clairvoyant and c_s != c_lo:
                    violations.append(prefix + f"non-clairvoyant HI task must have C_s = C_lo; {values}")
            else:
                violations.append(prefix + f"criticality X must be 1 (LO) or 2 (HI); {values}")
        hi_counts.append(hi_count)

    if reader.position != len(reader.lines):
        extra_line = reader.position + 1
        raise TaskSetFormatError(f"line {extra_line}: extra data after the declared {declared_set_count} task sets")

    return declared_set_count, total_tasks, violations, hi_counts


def validate_task_set_file(path: Path, non_clairvoyant: bool = False) -> tuple[int, int, list[str]]:
    """Return the set count, task count, and all semantic violations in *path*."""
    set_count, task_count, violations, _ = _inspect_task_set_file(path, non_clairvoyant)
    return set_count, task_count, violations


def read_utilisations(path: Path, set_count: int) -> list[Decimal]:
    """Read target utilizations indexed by task-set ID from a generated CSV header."""
    try:
        csv_file = path.open(encoding="utf-8", newline="")
    except OSError as error:
        raise TaskSetFormatError(f"cannot read {path}: {error}") from error

    with csv_file:
        reader = csv.DictReader(csv_file, strict=True)
        if reader.fieldnames is None:
            raise TaskSetFormatError(f"CSV header file {path} is empty")
        missing_columns = {"ts_id", "U"} - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise TaskSetFormatError(f"CSV header file {path} is missing required column(s): {missing}")

        try:
            rows = list(reader)
        except csv.Error as error:
            raise TaskSetFormatError(f"cannot parse CSV header file {path}: {error}") from error

        utilisations: dict[int, Decimal] = {}
        for line_number, row in enumerate(rows, start=2):
            try:
                raw_id = Decimal(row["ts_id"])
                utilisation = Decimal(row["U"])
            except (InvalidOperation, TypeError) as error:
                raise TaskSetFormatError(
                    f"CSV header file {path}, line {line_number}: ts_id and U must be numeric"
                ) from error

            if not raw_id.is_finite() or raw_id != raw_id.to_integral_value():
                raise TaskSetFormatError(
                    f"CSV header file {path}, line {line_number}: ts_id must be an integer, got {row['ts_id']!r}"
                )
            task_set_id = int(raw_id)
            if task_set_id < 0 or task_set_id >= set_count:
                raise TaskSetFormatError(
                    f"CSV header file {path}, line {line_number}: ts_id {task_set_id} is outside 0..{set_count - 1}"
                )
            if task_set_id in utilisations:
                raise TaskSetFormatError(f"CSV header file {path}, line {line_number}: duplicate ts_id {task_set_id}")
            if not utilisation.is_finite():
                raise TaskSetFormatError(
                    f"CSV header file {path}, line {line_number}: U must be finite, got {row['U']!r}"
                )
            utilisations[task_set_id] = utilisation

    missing_ids = sorted(set(range(set_count)) - utilisations.keys())
    if missing_ids:
        preview = ", ".join(map(str, missing_ids[:5]))
        suffix = "..." if len(missing_ids) > 5 else ""
        raise TaskSetFormatError(f"CSV header file {path} is missing ts_id value(s): {preview}{suffix}")

    return [utilisations[task_set_id] for task_set_id in range(set_count)]


def _format_utilisation(utilisation: Decimal) -> str:
    percentage = format(utilisation * 100, "f").rstrip("0").rstrip(".")
    return f"{percentage or '0'}%"


def format_hi_distribution(utilisations: list[Decimal], hi_counts: list[int]) -> str:
    """Return an ASCII n_HI count and row-percentage table."""
    distribution: dict[Decimal, Counter[int]] = defaultdict(Counter)
    for utilisation, hi_count in zip(utilisations, hi_counts, strict=True):
        distribution[utilisation][hi_count] += 1

    if not distribution:
        return "n_HI distribution by utilization:\n(no task sets)"

    observed_hi_counts = sorted({hi_count for counts in distribution.values() for hi_count in counts})
    headers = ["Utilization", *(f"n_HI={hi_count}" for hi_count in observed_hi_counts), "Total"]
    rows: list[list[str]] = []
    for utilisation in sorted(distribution):
        counts = distribution[utilisation]
        total = sum(counts.values())
        cells = [f"{counts[hi_count]} ({counts[hi_count] / total:.1%})" for hi_count in observed_hi_counts]
        rows.append([_format_utilisation(utilisation), *cells, str(total)])

    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
    lines = ["n_HI distribution by utilization:"]
    lines.append("  ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True)))
    lines.append("  ".join("-" * width for width in widths))
    lines.extend("  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)) for row in rows)
    return "\n".join(lines)


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a generated task-set definition file.")
    parser.add_argument("input_file", type=Path, help="generated task-set .txt file")
    parser.add_argument(
        "--header-file",
        type=Path,
        help="companion CSV header file (defaults to a same-stem .csv when present)",
    )
    parser.add_argument(
        "--non-clairvoyant",
        action="store_true",
        help="also require C_s = C_lo for every HI task",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        set_count, task_count, violations, hi_counts = _inspect_task_set_file(
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

    header_file = args.header_file
    if header_file is None:
        inferred_header_file = args.input_file.with_suffix(".csv")
        if inferred_header_file.is_file():
            header_file = inferred_header_file

    if header_file is not None:
        try:
            utilisations = read_utilisations(header_file, set_count)
        except TaskSetFormatError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(format_hi_distribution(utilisations, hi_counts))

    print(f"Valid: {set_count} task set(s), {task_count} task(s) checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
