"""Evaluate OCR quality by computing CER and WER.

Usage:
    python scripts/eval_cer.py [--dataset samples/ground_truth.json]

The dataset file should be a JSON array with objects containing
`id`, `ground_truth`, and `prediction` fields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Sequence


def levenshtein_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    """Compute Levenshtein distance between two sequences.

    Parameters
    ----------
    reference: Sequence[str]
        Reference tokens (characters or words).
    hypothesis: Sequence[str]
        Hypothesis tokens (characters or words).

    Returns
    -------
    int
        The minimum number of edits (insertions, deletions, substitutions).
    """
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    previous_row: List[int] = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, start=1):
        current_row = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            substitution_cost = 0 if ref_token == hyp_token else 1
            current_row.append(
                min(
                    previous_row[j] + 1,  # deletion
                    current_row[j - 1] + 1,  # insertion
                    previous_row[j - 1] + substitution_cost,  # substitution
                )
            )
        previous_row = current_row
    return previous_row[-1]


def compute_error_rates(records: Iterable[dict[str, str]]) -> tuple[float, float]:
    """Compute corpus-level CER and WER for a dataset."""
    total_char_errors = 0
    total_chars = 0
    total_word_errors = 0
    total_words = 0

    for record in records:
        ground_truth = record.get("ground_truth", "")
        prediction = record.get("prediction", "")

        total_chars += len(ground_truth)
        total_words += len(ground_truth.split())

        total_char_errors += levenshtein_distance(list(ground_truth), list(prediction))
        total_word_errors += levenshtein_distance(ground_truth.split(), prediction.split())

    char_error_rate = total_char_errors / total_chars if total_chars else 0.0
    word_error_rate = total_word_errors / total_words if total_words else 0.0
    return char_error_rate, word_error_rate


def load_dataset(path: Path) -> List[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array of records")
    return data


def format_percentage(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute CER and WER for OCR outputs.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("samples") / "ground_truth.json",
        help="Path to a JSON file with ground_truth/prediction pairs.",
    )
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    cer, wer = compute_error_rates(dataset)

    print(f"Loaded {len(dataset)} records from {args.dataset}")
    print(f"Character Error Rate (CER): {format_percentage(cer)}")
    print(f"Word Error Rate (WER): {format_percentage(wer)}")


if __name__ == "__main__":
    main()
