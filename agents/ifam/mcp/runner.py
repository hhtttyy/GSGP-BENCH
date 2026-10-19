#!/usr/bin/env python3
"""Independent IFAM benchmark runner.

This module is deliberately outside the MCP boundary. It joins exported
predictions with held-out truth, enforces split/leakage rules, and computes
metrics. It never ranks models and never writes a certification level.

Usage:
  python3 runner.py \
    --predictions export.json \
    --truth pheno/phenotype.truth.txt \
    --split splits/repeat-1.json \
    --fit-phenotype pheno/phenotype.fit.txt \
    --out evaluation.json

Predictions may be an MCP export JSON (with a "predictions" array) or a
tab-separated file with sample_id and genetic_value columns.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


class EvaluationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise EvaluationError("EMPTY_FILE", f"{path} is empty")
    header = lines[0].split("\t")
    rows = [line.split("\t") for line in lines[1:] if line.strip()]
    return header, rows


def _read_truth(path: Path, column: int) -> dict[str, float]:
    header, rows = _read_tsv(path)
    if column < 1 or column > len(header):
        raise EvaluationError("TRUTH_COLUMN_INVALID", f"truth column {column} is outside the header")
    truth: dict[str, float] = {}
    for row in rows:
        if len(row) < len(header):
            raise EvaluationError("TRUTH_MALFORMED", f"short truth row near {row[:1]}")
        sample_id = row[0].strip()
        if not sample_id:
            raise EvaluationError("TRUTH_MALFORMED", "empty sample ID in truth")
        if sample_id in truth:
            raise EvaluationError("TRUTH_DUPLICATE_ID", f"duplicate truth ID {sample_id}")
        raw = row[column - 1].strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise EvaluationError("TRUTH_NON_NUMERIC", f"truth {sample_id} is not numeric: {raw!r}") from exc
        if not math.isfinite(value):
            raise EvaluationError("TRUTH_NON_NUMERIC", f"truth {sample_id} is not finite")
        truth[sample_id] = value
    return truth


def _read_fit_phenotype(path: Path, column: int) -> dict[str, float | None]:
    header, rows = _read_tsv(path)
    if column < 1 or column > len(header):
        raise EvaluationError("FIT_COLUMN_INVALID", f"fit phenotype column {column} is outside the header")
    values: dict[str, float | None] = {}
    for row in rows:
        if len(row) < len(header):
            raise EvaluationError("FIT_PHENOTYPE_MALFORMED", "short fit phenotype row")
        sample_id = row[0].strip()
        raw = row[column - 1].strip()
        if raw.upper() == "NA":
            values[sample_id] = None
        else:
            try:
                value = float(raw)
            except ValueError as exc:
                raise EvaluationError("FIT_PHENOTYPE_NON_NUMERIC", f"fit phenotype {sample_id} is not numeric or NA") from exc
            values[sample_id] = value if math.isfinite(value) else None
    return values


def _read_predictions(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("predictions"), list):
            raw = payload["predictions"]
        elif isinstance(payload, list):
            raw = payload
        else:
            raise EvaluationError("PREDICTIONS_MALFORMED", "JSON predictions must be an array or export object")
        result = []
        for item in raw:
            if not isinstance(item, dict) or "sample_id" not in item or "genetic_value" not in item:
                raise EvaluationError("PREDICTIONS_MALFORMED", "each prediction needs sample_id and genetic_value")
            result.append(item)
        return result

    header, rows = _read_tsv(path)
    lower = [h.lower() for h in header]
    try:
        id_index = lower.index("sample_id")
        value_index = lower.index("genetic_value")
    except ValueError as exc:
        raise EvaluationError(
            "PREDICTIONS_MALFORMED",
            "TSV predictions need sample_id and genetic_value columns",
        ) from exc
    return [
        {"sample_id": row[id_index], "genetic_value": row[value_index]}
        for row in rows
        if len(row) > max(id_index, value_index)
    ]


def _read_split(path: Path) -> tuple[str, list[str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EvaluationError("SPLIT_INVALID", "split must be a JSON object")
    split_id = payload.get("split_id")
    training = payload.get("training_ids")
    validation = payload.get("validation_ids")
    if not isinstance(split_id, str) or not split_id:
        raise EvaluationError("SPLIT_INVALID", "split_id is required")
    if not isinstance(training, list) or not isinstance(validation, list):
        raise EvaluationError("SPLIT_INVALID", "training_ids and validation_ids must be arrays")
    training = [str(x) for x in training]
    validation = [str(x) for x in validation]
    if not training or not validation:
        raise EvaluationError("SPLIT_INVALID", "training_ids and validation_ids must be non-empty")
    if len(set(training)) != len(training) or len(set(validation)) != len(validation):
        raise EvaluationError("SPLIT_INVALID", "split IDs must be unique")
    overlap = set(training) & set(validation)
    if overlap:
        raise EvaluationError("VALIDATION_LEAKAGE", f"training/validation overlap: {sorted(overlap)[:5]}")
    return split_id, training, validation


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        raise EvaluationError("INSUFFICIENT_OBSERVATIONS", "Pearson r needs at least two observations")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    sxx = sum(v * v for v in dx)
    syy = sum(v * v for v in dy)
    if sxx == 0 or syy == 0:
        raise EvaluationError("ZERO_VARIANCE", "Pearson r is undefined with constant input")
    sxy = sum(a * b for a, b in zip(dx, dy))
    return sxy / math.sqrt(sxx * syy)


def _slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        raise EvaluationError("INSUFFICIENT_OBSERVATIONS", "bias slope needs at least two observations")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        raise EvaluationError("ZERO_VARIANCE", "bias slope is undefined with constant predictions")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return sxy / sxx


def _auc(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise EvaluationError("AUC_UNDEFINED", "AUC needs both positive and negative truth values")
    # Mann-Whitney U with average ranks for ties.
    ordered = sorted(zip(scores, labels), key=lambda item: item[0])
    ranks: list[float] = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        average_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = average_rank
        i = j
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, ordered) if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def evaluate(
    predictions_path: Path,
    truth_path: Path,
    split_path: Path,
    truth_column: int = 2,
    fit_phenotype_path: Path | None = None,
    fit_column: int = 2,
    predictions_sha256: str | None = None,
    truth_sha256: str | None = None,
    split_sha256: str | None = None,
) -> dict[str, Any]:
    split_id, training_ids, validation_ids = _read_split(split_path)
    truth = _read_truth(truth_path, truth_column)
    predictions = _read_predictions(predictions_path)

    prediction_map: dict[str, float] = {}
    for item in predictions:
        sample_id = str(item["sample_id"])
        if sample_id in prediction_map:
            raise EvaluationError("PREDICTION_DUPLICATE_ID", f"duplicate prediction ID {sample_id}")
        try:
            value = float(item["genetic_value"])
        except (TypeError, ValueError) as exc:
            raise EvaluationError("PREDICTION_NON_NUMERIC", f"prediction {sample_id} is not numeric") from exc
        if not math.isfinite(value):
            raise EvaluationError("PREDICTION_NON_NUMERIC", f"prediction {sample_id} is not finite")
        prediction_map[sample_id] = value

    validation_set = set(validation_ids)
    extra_truth = set(truth) - validation_set
    if extra_truth:
        raise EvaluationError(
            "TRUTH_OUTSIDE_VALIDATION",
            f"truth contains {len(extra_truth)} IDs outside the validation split",
        )
    missing_truth = validation_set - set(truth)
    if missing_truth:
        raise EvaluationError("TRUTH_INCOMPLETE", f"truth is missing {len(missing_truth)} validation IDs")
    missing_predictions = validation_set - set(prediction_map)
    if missing_predictions:
        raise EvaluationError(
            "PREDICTIONS_INCOMPLETE",
            f"predictions are missing {len(missing_predictions)} validation IDs",
        )
    training_overlap = set(training_ids) & set(prediction_map)
    if not training_overlap:
        # Not an error; predictions may be exported only for validation IDs.
        pass

    if fit_phenotype_path is not None:
        fit_values = _read_fit_phenotype(fit_phenotype_path, fit_column)
        leaked = [sample_id for sample_id in validation_ids if fit_values.get(sample_id) is not None]
        if leaked:
            raise EvaluationError(
                "VALIDATION_LEAKAGE",
                f"{len(leaked)} validation IDs still have a numeric fit phenotype",
            )
    else:
        fit_values = None

    xs = [prediction_map[sample_id] for sample_id in validation_ids]
    ys = [truth[sample_id] for sample_id in validation_ids]
    pearson = _pearson(xs, ys)
    metrics: dict[str, float | None] = {
        "pearson_r": pearson,
        "r2": pearson * pearson,
        "prediction_bias_slope": _slope(xs, ys),
        "auc": None,
    }
    labels = []
    auc_reason = None
    if all(value in (0.0, 1.0) for value in ys):
        labels = [int(value) for value in ys]
        if 0 < sum(labels) < len(labels):
            metrics["auc"] = _auc(labels, xs)
        else:
            auc_reason = "AUC requires both binary classes"
    else:
        auc_reason = "truth is not binary 0/1"

    return {
        "schema_version": "ifam.evaluation.v1",
        "evidence_level": "exploratory",
        "split_id": split_id,
        "metrics": metrics,
        "n_validation": len(validation_ids),
        "n_training": len(training_ids),
        "checks": {
            "split_disjoint": True,
            "truth_within_validation": True,
            "predictions_complete": True,
            "fit_phenotype_masked": fit_values is not None,
            "truth_binary": auc_reason is None,
        },
        "warnings": [auc_reason] if auc_reason else [],
        "provenance": {
            "predictions_sha256": predictions_sha256,
            "truth_sha256": truth_sha256,
            "split_sha256": split_sha256,
            "truth_column": truth_column,
            "fit_column": fit_column,
        },
    }


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent IFAM evaluation runner")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--truth", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--fit-phenotype")
    parser.add_argument("--truth-column", type=int, default=2)
    parser.add_argument("--fit-column", type=int, default=2)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    try:
        report = evaluate(
            Path(args.predictions),
            Path(args.truth),
            Path(args.split),
            truth_column=args.truth_column,
            fit_phenotype_path=Path(args.fit_phenotype) if args.fit_phenotype else None,
            fit_column=args.fit_column,
            predictions_sha256=_sha256(Path(args.predictions)),
            truth_sha256=_sha256(Path(args.truth)),
            split_sha256=_sha256(Path(args.split)),
        )
    except (EvaluationError, OSError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, EvaluationError) else "INPUT_ERROR"
        message = exc.message if isinstance(exc, EvaluationError) else str(exc)
        print(json.dumps({"schema_version": "ifam.evaluation.error.v1", "error": {"code": code, "message": message}}, indent=2))
        return 1

    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
