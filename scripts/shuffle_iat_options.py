#!/usr/bin/env python3
"""Shuffle answer options for IAT mock papers.

The parser assumes the source PDFs list options as A/B/C/D where option A is the
correct answer in the original source. It extracts question blocks from text,
shuffles options, and rewrites the correct option label accordingly.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

QUESTION_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]\s*(.+)\s*$")
OPTION_RE = re.compile(r"^\s*([A-D])\s*[).:-]\s*(.+)\s*$", re.IGNORECASE)


@dataclass
class ParsedQuestion:
    question_no: int
    question: str
    options: dict[str, str]
    source_pdf: str


@dataclass
class ShuffledQuestion(ParsedQuestion):
    answer: str


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - runtime guard
        raise SystemExit(
            "Missing dependency 'pypdf'. Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(str(pdf_path))
    page_text: list[str] = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return "\n".join(page_text)


def parse_questions(text: str, source_pdf: str) -> list[ParsedQuestion]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed: list[ParsedQuestion] = []

    current_no: int | None = None
    question_buf: list[str] = []
    options: dict[str, list[str]] = {}
    current_option: str | None = None

    def flush() -> None:
        nonlocal current_no, question_buf, options, current_option
        if current_no is None:
            return

        materialized_options = {k: " ".join(v).strip() for k, v in options.items()}
        if len(materialized_options) == 4 and set(materialized_options) == {"A", "B", "C", "D"}:
            parsed.append(
                ParsedQuestion(
                    question_no=current_no,
                    question=" ".join(question_buf).strip(),
                    options=materialized_options,
                    source_pdf=source_pdf,
                )
            )

        current_no = None
        question_buf = []
        options = {}
        current_option = None

    for line in lines:
        q_match = QUESTION_RE.match(line)
        if q_match and not options:
            flush()
            current_no = int(q_match.group(1))
            question_buf = [q_match.group(2).strip()]
            continue

        opt_match = OPTION_RE.match(line)
        if opt_match and current_no is not None:
            label = opt_match.group(1).upper()
            options[label] = [opt_match.group(2).strip()]
            current_option = label
            continue

        if current_no is not None and not options:
            question_buf.append(line)
            continue

        if current_option is not None:
            options[current_option].append(line)

    flush()
    return parsed


def shuffle_question(
    item: ParsedQuestion,
    rng: random.Random,
    assumed_correct: str = "A",
) -> ShuffledQuestion:
    option_items = list(item.options.items())
    rng.shuffle(option_items)

    new_labels = ["A", "B", "C", "D"]
    remapped = {new_label: text for new_label, (_, text) in zip(new_labels, option_items)}

    answer = None
    for new_label, (old_label, _) in zip(new_labels, option_items):
        if old_label == assumed_correct:
            answer = new_label
            break

    if answer is None:
        raise ValueError(f"Could not remap assumed correct option '{assumed_correct}'")

    return ShuffledQuestion(
        question_no=item.question_no,
        question=item.question,
        options=remapped,
        source_pdf=item.source_pdf,
        answer=answer,
    )


def iter_pdf_files(path: Path) -> Iterable[Path]:
    if path.is_file() and path.suffix.lower() == ".pdf":
        yield path
        return

    for candidate in sorted(path.glob("*.pdf")):
        if candidate.is_file():
            yield candidate


def run(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)

    all_shuffled: list[ShuffledQuestion] = []
    stats: list[tuple[str, int, int]] = []

    for pdf_path in iter_pdf_files(args.input):
        text = extract_pdf_text(pdf_path)
        parsed = parse_questions(text, source_pdf=pdf_path.name)
        shuffled = [shuffle_question(p, rng, args.assumed_correct) for p in parsed]

        all_shuffled.extend(shuffled)
        stats.append((pdf_path.name, len(parsed), len(shuffled)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump([asdict(q) for q in all_shuffled], f, ensure_ascii=False, indent=2)

    for pdf_name, parsed_count, shuffled_count in stats:
        print(f"{pdf_name}: parsed={parsed_count}, shuffled={shuffled_count}")
    print(f"Wrote {len(all_shuffled)} questions to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("files"),
        help="PDF file or directory containing PDFs (default: files)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/shuffled_questions.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for reproducible shuffling",
    )
    parser.add_argument(
        "--assumed-correct",
        default="A",
        choices=["A", "B", "C", "D"],
        help="Original correct option label before shuffling",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
