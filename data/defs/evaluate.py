"""The evaluation harness: labeled cases -> three retrieval arms -> a Markdown report.

A retrieval pipeline has no single correct output, only a measurable
quality level. Ordinary tests assert equality; this asserts
`quality >= threshold`. Three properties make this a pipeline rather than
a notebook: reproducible (the report names dataset and pipeline versions),
re-run on change (it is an asset with upstream deps), and comparable
(three arms over identical cases).
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dagster import AssetExecutionContext, MaterializeResult, asset
from sklearn.metrics import precision_recall_fscore_support

from defs.documents import silver_document_chunk
from lib import db
from lib.embedding import MODEL_ID, embed
from lib.logging import get_logger, log_event
from lib.settings import settings

logger = get_logger(__name__)


@dataclass
class ArmMetrics:
    """Precision/recall/F1 plus recall@k and MRR for one retrieval arm."""

    precision: float
    recall: float
    f1: float
    recall_at_k: float
    mrr: float


def _load_cases(path: Path) -> list[dict]:
    """Load labeled evaluation cases from a JSONL file."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _hash_text(text: str) -> str:
    """Short, stable hash used for dataset/pipeline versioning."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _score_arm(
    cases: list[dict], retrieved_ids_by_case: dict[str, list[str]], *, top_k: int
) -> ArmMetrics:
    """Compute precision/recall/F1/recall@k/MRR over binary (case, chunk) relevance.

    Args:
        cases: Labeled cases, each with ``case_id`` and ``expected_chunk_ids``.
        retrieved_ids_by_case: Map of ``case_id`` to the ranked chunk ids
            this arm retrieved.
        top_k: The cutoff used to compute recall@k.

    Returns:
        The arm's aggregate metrics.
    """
    y_true: list[int] = []
    y_pred: list[int] = []
    recall_hits = 0
    reciprocal_ranks: list[float] = []

    for case in cases:
        expected = set(case["expected_chunk_ids"])
        retrieved = retrieved_ids_by_case.get(case["case_id"], [])
        retrieved_set = set(retrieved[:top_k])

        # Binary relevance per unique chunk id seen (expected ∪ retrieved).
        for chunk_id in expected | retrieved_set:
            y_true.append(1 if chunk_id in expected else 0)
            y_pred.append(1 if chunk_id in retrieved_set else 0)

        if expected & retrieved_set:
            recall_hits += 1

        rank = next((i + 1 for i, cid in enumerate(retrieved) if cid in expected), None)
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

    if y_true:
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )
    else:
        precision = recall = f1 = 0.0

    recall_at_k = recall_hits / len(cases) if cases else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    return ArmMetrics(float(precision), float(recall), float(f1), recall_at_k, mrr)


def run_evaluation(*, dataset_path: Path, top_k: int, run_id: str) -> dict[str, ArmMetrics]:
    """Score three retrieval arms -- lexical-only, dense-only, hybrid RRF -- over identical cases.

    Args:
        dataset_path: Path to the labeled JSONL dataset.
        top_k: Number of results each arm retrieves per case.
        run_id: The caller-generated run id.

    Returns:
        A dict of arm name to :class:`ArmMetrics`.
    """
    cases = _load_cases(dataset_path)
    query_vectors = {case["case_id"]: embed([case["query"]])[0] for case in cases}

    lexical_ids: dict[str, list[str]] = {}
    dense_ids: dict[str, list[str]] = {}
    hybrid_ids: dict[str, list[str]] = {}

    for case in cases:
        qvec = query_vectors[case["case_id"]]
        lexical_ids[case["case_id"]] = [
            r["chunk_id"] for r in db.search_lexical_only(case["query"], top_k=top_k)
        ]
        dense_ids[case["case_id"]] = [
            r["chunk_id"] for r in db.search_dense_only(case["query"], qvec, top_k=top_k)
        ]
        hybrid_ids[case["case_id"]] = [
            r["chunk_id"] for r in db.search(case["query"], qvec, top_k=top_k)
        ]

    metrics = {
        "lexical_only": _score_arm(cases, lexical_ids, top_k=top_k),
        "dense_only": _score_arm(cases, dense_ids, top_k=top_k),
        "hybrid_rrf": _score_arm(cases, hybrid_ids, top_k=top_k),
    }

    dataset_version = _hash_text(dataset_path.read_text())
    pipeline_version = _hash_text(f"{MODEL_ID}|{settings.retrieval.rrf_k}|{top_k}")
    report_path = _write_report(
        metrics, cases=cases, dataset_version=dataset_version, pipeline_version=pipeline_version
    )

    for arm, m in metrics.items():
        db.record_eval_run(
            run_id=run_id, dataset_version=dataset_version, pipeline_version=pipeline_version,
            arm=arm, n_cases=len(cases), precision=m.precision, recall=m.recall, f1=m.f1,
            recall_at_k=m.recall_at_k, mrr=m.mrr, report_path=str(report_path),
        )

    log_event(logger, "info", "eval_completed", run_id=run_id, n_cases=len(cases),
              hybrid_f1=metrics["hybrid_rrf"].f1)
    return metrics


def _write_report(
    metrics: dict[str, ArmMetrics], *, cases: list[dict],
    dataset_version: str, pipeline_version: str,
) -> Path:
    """Write a Markdown report naming the dataset version, pipeline version, n, and each arm."""
    report_dir = Path(settings.eval.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = report_dir / f"retrieval_{stamp}.md"

    lines = [
        "# Retrieval evaluation report",
        "",
        f"- dataset_version: `{dataset_version}`",
        f"- pipeline_version: `{pipeline_version}`",
        f"- n_cases: {len(cases)}",
        f"- embedder: `{MODEL_ID}`",
        "",
        "| arm | precision | recall | f1 | recall@k | mrr |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for arm, m in metrics.items():
        lines.append(
            f"| {arm} | {m.precision:.3f} | {m.recall:.3f} | {m.f1:.3f} "
            f"| {m.recall_at_k:.3f} | {m.mrr:.3f} |"
        )

    path.write_text("\n".join(lines) + "\n")
    return path


@asset(key="eval_retrieval", deps=[silver_document_chunk])
def eval_retrieval(context: AssetExecutionContext) -> MaterializeResult:
    """Run the retrieval evaluation harness as a Dagster asset, re-run when the index changes."""
    start = time.perf_counter()
    run_id = uuid.uuid4().hex[:12]
    metrics = run_evaluation(
        dataset_path=Path(settings.eval.dataset_path), top_k=settings.retrieval.top_k, run_id=run_id
    )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return MaterializeResult(metadata={
        "duration_ms": duration_ms,
        "hybrid_rrf_f1": metrics["hybrid_rrf"].f1,
        "dense_only_f1": metrics["dense_only"].f1,
        "lexical_only_f1": metrics["lexical_only"].f1,
    })
