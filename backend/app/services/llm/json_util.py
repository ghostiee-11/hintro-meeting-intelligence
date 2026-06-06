import json
import re
from typing import Any

from app.services.llm.schema import RawActionItem, RawAnalysis, RawCitation, RawInsight

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Extracts the first JSON object from a possibly fenced or chatty response."""
    trimmed = text.strip()
    fenced = _FENCE.search(trimmed)
    candidate = fenced.group(1) if fenced else trimmed
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(candidate[start : end + 1])


def _norm_citations(value: Any) -> list[RawCitation]:
    if not isinstance(value, list):
        return []
    out: list[RawCitation] = []
    for c in value:
        if isinstance(c, bool):
            continue
        if isinstance(c, int):
            out.append(RawCitation(segment_index=c))
        elif isinstance(c, dict) and "segmentIndex" in c:
            try:
                out.append(RawCitation(segment_index=int(c["segmentIndex"])))
            except (TypeError, ValueError):
                continue
        elif isinstance(c, dict) and "segment_index" in c:
            try:
                out.append(RawCitation(segment_index=int(c["segment_index"])))
            except (TypeError, ValueError):
                continue
    return out


def _norm_insights(value: Any) -> list[RawInsight]:
    if not isinstance(value, list):
        return []
    out: list[RawInsight] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        out.append(RawInsight(text=text.strip(), citations=_norm_citations(item.get("citations"))))
    return out


def _norm_action_items(value: Any) -> list[RawActionItem]:
    if not isinstance(value, list):
        return []
    out: list[RawActionItem] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        task = item.get("task")
        if not isinstance(task, str) or not task.strip():
            continue
        assignee = item.get("assignee")
        due_date = item.get("dueDate") or item.get("due_date")
        out.append(
            RawActionItem(
                task=task.strip(),
                assignee=assignee if isinstance(assignee, str) and assignee.strip() else None,
                due_date=due_date if isinstance(due_date, str) and due_date.strip() else None,
                citations=_norm_citations(item.get("citations")),
            )
        )
    return out


def normalize_analysis(raw: Any) -> RawAnalysis:
    """Coerces any reasonable model output into a strict RawAnalysis."""
    obj = raw if isinstance(raw, dict) else {}
    return RawAnalysis(
        summary=_norm_insights(obj.get("summary")),
        decisions=_norm_insights(obj.get("decisions")),
        follow_ups=_norm_insights(
            obj.get("followUps") or obj.get("follow_ups") or obj.get("followups")
        ),
        action_items=_norm_action_items(obj.get("actionItems") or obj.get("action_items")),
    )
