"""Retrieval and context metrics against a golden set. No LLM calls.

Golden item (fields used here; see golden/README.md):
    {"qid": "Q001", "targets": [{"file": "a.pdf", "page": 3}], "evidence": ["verbatim quote", ...]}

Unit (a retrieved chunk, or a page passed to the answer step):
    {"chunk_id": "...", "source": "a.pdf", "page": 3, "content": "..."}

- ranked_metrics(item, ranked)   quality of a ranked list: page_hit@k, mrr, evid@k, gold@k
- context_metrics(item, context) what the answer step actually received: gold page present, evidence
                                 coverage, number of gold-page units, size
- proxy_check(scores, metrics)   which retrieval metric moves with answer score (workflow step 4)
- direction_agreement(...)       across two configs, does the metric move the same way as the score?

Why gold@k: with small chunks one page's answer is split over several chunks. "Was the gold page found
at all" (page_hit, MRR) can favor a method that brings fewer of those chunks, while answers depend on
how much of the page arrives. Compare both before trusting either.
"""

import statistics
import unicodedata


def nfc(text: str) -> str:
    """File names can arrive in NFD (e.g. Korean names on macOS); compare in NFC."""
    return unicodedata.normalize("NFC", text)


def squash(text: str) -> str:
    """NFKC, then drop all whitespace and control/format characters. Extracted text breaks lines and
    spaces differently from copied quotes, so quotes are matched on this form."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if not ch.isspace() and unicodedata.category(ch) not in ("Cc", "Cf"))


def evidence_segments(quotes: list[str], min_len: int = 8) -> list[str]:
    """Split quotes into lines. Lines shorter than min_len after squash are too generic to match on."""
    segments = []
    for quote in quotes:
        segments += [s for s in (squash(line) for line in quote.splitlines()) if len(s) >= min_len]
    return segments


def target_pages(item: dict) -> set[tuple[str, int]]:
    # A question may list several pages (same content in two places, or two documents needed).
    # Any one of them counts as a page hit; evidence coverage shows whether all were found.
    return {(nfc(t["file"]), t["page"]) for t in item.get("targets", [])}


def is_gold(unit: dict, targets: set) -> bool:
    return (nfc(unit["source"]), unit["page"]) in targets


def coverage(segments: list[str], units: list[dict]) -> float | None:
    """Share of evidence segments found verbatim (after squash) in any unit. None if no evidence."""
    if not segments:
        return None
    contents = [squash(u["content"]) for u in units]
    return sum(1 for s in segments if any(s in c for c in contents)) / len(segments)


def ranked_metrics(item: dict, ranked: list[dict], ks=(1, 3, 5, 10)) -> dict:
    """Metrics of a ranked retrieval list. mrr is over the whole list given."""
    targets = target_pages(item)
    hits = [is_gold(u, targets) for u in ranked]
    first = hits.index(True) + 1 if True in hits else None
    segments = evidence_segments(item.get("evidence", []))
    row = {"first_rank": first, "mrr": 1 / first if first else 0.0}
    for k in ks:
        row[f"page_hit@{k}"] = int(first is not None and first <= k)
        row[f"gold@{k}"] = sum(hits[:k])
        row[f"evid@{k}"] = coverage(segments, ranked[:k])
    return row


def context_metrics(item: dict, context: list[dict]) -> dict:
    """Metrics of the units actually passed to the answer step (e.g. RunLog's `context` column)."""
    targets = target_pages(item)
    evid = coverage(evidence_segments(item.get("evidence", [])), context)
    return {
        "page_hit": int(any(is_gold(u, targets) for u in context)),
        "gold": sum(is_gold(u, targets) for u in context),
        "evid": evid,
        "evid_full": None if evid is None else int(evid == 1),
        "units": len(context),
        "chars": sum(len(u["content"]) for u in context),
    }


def proxy_check(scores: dict, metrics: dict[str, dict]) -> dict[str, float | None]:
    """Pearson r between each retrieval metric and the answer score, over questions that have both.

    scores:  {qid: answer score} from one graded run (answerable questions only)
    metrics: {metric name: {qid: value}} for the same run
    Use the metric with the highest r as the proxy for LLM-free comparisons. This is a cross-question
    check on one config; once two configs have answer runs, confirm with direction_agreement.
    """
    result = {}
    for name, values in metrics.items():
        qids = [q for q in scores if values.get(q) is not None]
        try:
            result[name] = round(statistics.correlation(
                [float(values[q]) for q in qids], [float(scores[q]) for q in qids]), 3)
        except statistics.StatisticsError:  # fewer than two points, or a constant column
            result[name] = None
    return result


def direction_agreement(metric_a: dict, metric_b: dict, score_a: dict, score_b: dict) -> dict | None:
    """Across two configs A and B: among questions whose answer score changed, how often did the metric
    move the same way? Low agreement means the metric is not a usable proxy for this kind of change."""
    qids = score_a.keys() & score_b.keys() & metric_a.keys() & metric_b.keys()
    pairs = [(metric_b[q] - metric_a[q], score_b[q] - score_a[q]) for q in qids if score_a[q] != score_b[q]]
    if not pairs:
        return None
    return {
        "score_changed": len(pairs),
        "same_direction": sum(1 for dm, ds in pairs if dm * ds > 0),
        "opposite_direction": sum(1 for dm, ds in pairs if dm * ds < 0),
        "metric_unchanged": sum(1 for dm, _ in pairs if dm == 0),
    }
