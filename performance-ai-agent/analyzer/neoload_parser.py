"""Reusable parser for NeoLoad HTML and ZIP reports."""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


def _text(value: str) -> str:
    return " ".join(value.split())


def _number(value: str) -> float | int | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    parsed = float(match.group())
    return int(parsed) if parsed.is_integer() else parsed


def _duration_seconds(value: str) -> float | None:
    match = re.fullmatch(r"\s*(\d+):(\d{2})(?::(\d{2}))?\s*", value)
    if not match:
        return None
    groups = match.groups()
    if groups[2] is None:
        return float(int(groups[0]) * 60 + int(groups[1]))
    return float(int(groups[0]) * 3600 + int(groups[1]) * 60 + int(groups[2]))


def _html_files(source: Path) -> Iterable[tuple[str, str]]:
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if member.filename.lower().endswith((".html", ".htm")) and not member.is_dir():
                    yield member.filename, archive.read(member).decode("utf-8", errors="replace")
        return

    if source.is_dir():
        for html_file in sorted(source.rglob("*")):
            if html_file.is_file() and html_file.suffix.lower() in {".html", ".htm"}:
                yield str(html_file.relative_to(source)), html_file.read_text(
                    encoding="utf-8", errors="replace"
                )
        return

    if source.suffix.lower() in {".html", ".htm"}:
        yield source.name, source.read_text(encoding="utf-8", errors="replace")
        for sibling in source.parent.glob("*.html"):
            if sibling != source:
                yield sibling.name, sibling.read_text(encoding="utf-8", errors="replace")
        return

    raise ValueError("NeoLoad input must be an HTML file or ZIP archive")


def _table_rows(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    return rows


def _metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    labels = {
        "project": "project",
        "scenario": "scenario_name",
        "start date": "start_time",
        "end date": "end_time",
        "duration": "duration",
        "status": "status",
        "load policy": "load_policy",
    }
    for row in soup.find_all("tr"):
        cells = [_text(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
        for index, cell in enumerate(cells[:-1]):
            key = labels.get(cell.lower().rstrip(":"))
            if key:
                result[key] = cells[index + 1]
    return result


def _labeled_metrics(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    metrics = {}
    for row in soup.find_all("tr"):
        cells = [_text(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
        if not cells:
            continue
        for index in range(len(cells) - 1):
            label = cells[index].lower().rstrip(":")
            if label in {
                "total pages", "total requests", "total users launched",
                "total iterations completed", "total throughput",
                "total request errors", "error rate",
                "average pages/s", "average requests/s", "average request response time",
                "average page response time", "average throughput",
            }:
                metrics[label] = cells[index + 1]
    return metrics


def _transactions(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    transactions = []
    for table in soup.find_all("table"):
        rows = _table_rows(table)
        if len(rows) < 2:
            continue
        header = [re.sub(r"\s+", " ", row).lower() for row in rows[0]]
        normalized = " ".join(header)
        if not {"min", "avg", "max"} <= set(header):
            continue
        if not any(token in normalized for token in ("count", "perc 95", "error")):
            continue

        def index(name: str) -> int | None:
            try:
                return header.index(name)
            except ValueError:
                return None

        count_index = index("count")
        for row in rows[1:]:
            if len(row) <= 5:
                continue
            # Some NeoLoad summary tables place the label in a separate row above
            # numeric values. Those rows are not transaction records.
            if _number(row[0]) is not None:
                continue
            count = _number(row[count_index]) if count_index is not None and count_index < len(row) else None
            if count is None:
                continue
            name = row[0]
            if not name:
                continue
            # NeoLoad hierarchy labels use virtual-user, container-blue, and container
            # classes. Only leaf `container` rows are executable transactions.
            transaction_row_index = rows[1:].index(row) + len(rows[:1])
            source_tr = table.find_all("tr")[transaction_row_index]
            label = source_tr.find("div", class_=lambda value: value and "tablelabel" in value)
            classes = label.get("class", []) if label else []
            if (
                not label
                or "virtualuser" in classes
                or "container-blue" in classes
                or "container" not in classes
            ):
                continue
            name = re.sub(r"_\d+$", "", name)
            if name.lower() in {"init", "actions", "end", "then", "else", "loop"}:
                continue
            get = lambda position: _number(row[position]) if position is not None and position < len(row) else None
            pct95 = index("perc 95")
            pct99 = index("perc 99")
            errors = index("err")
            error_pct = index("% of err")
            transactions.append({
                "name": name,
                "execution_count": count,
                "min_response_time_s": get(index("min")),
                "avg_response_time_s": get(index("avg")),
                "max_response_time_s": get(index("max")),
                "p95_response_time_s": get(pct95),
                "p99_response_time_s": get(pct99),
                "error_count": get(errors),
                "error_pct": get(error_pct),
                "source": "NeoLoad HTML",
            })
    return transactions


def parse_neoload(source: str | Path) -> dict:
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Report not found: {source}")

    html_documents = list(_html_files(source))
    combined = "\n".join(html for _, html in html_documents)
    metadata = {}
    summary_metrics = {}
    transactions = []

    for filename, html in html_documents:
        current_metadata = _metadata(html)
        if filename.lower().endswith(("summary.html", "index.html")) or current_metadata:
            metadata.update({key: value for key, value in current_metadata.items() if value})
        summary_metrics.update(_labeled_metrics(html))
        transactions.extend(_transactions(html))

    excluded_transaction_names = {"init", "actions", "end"}
    unique = {}
    for transaction in transactions:
        normalized_name = _text(transaction["name"]).lower()
        if normalized_name in excluded_transaction_names:
            continue
        unique[transaction["name"]] = transaction
    transactions = list(unique.values())

    duration = _duration_seconds(metadata.get("duration", ""))
    total_requests = _number(summary_metrics.get("total requests", ""))
    total_errors = _number(summary_metrics.get("total request errors", ""))
    average_users = _number(summary_metrics.get("total users launched", ""))
    execution_count = sum(int(t["execution_count"] or 0) for t in transactions)

    return {
        "report_type": "NeoLoad",
        "scenario_name": metadata.get("scenario_name"),
        "project": metadata.get("project"),
        "status": metadata.get("status"),
        "start_time": metadata.get("start_time"),
        "end_time": metadata.get("end_time"),
        "duration_seconds": duration,
        "max_virtual_users": average_users,
        "total_virtual_users_launched": average_users,
        "total_iterations_completed": _number(summary_metrics.get("total iterations completed", "")),
        "total_transactions": execution_count,
        "total_requests": total_requests,
        "failed_transactions": int(total_errors or 0),
        "error_rate_pct": _number(summary_metrics.get("error rate", "")),
        "average_tps": _number(summary_metrics.get("average requests/s", "")),
        "average_requests_per_second": _number(summary_metrics.get("average requests/s", "")),
        "average_response_time_s": _number(summary_metrics.get("average request response time", "")),
        "total_throughput_mb": _number(summary_metrics.get("total throughput", "")),
        "average_throughput_mbps": _number(summary_metrics.get("average throughput", "")),
        "transactions": transactions,
        "raw_source_files": [filename for filename, _ in html_documents],
    }
