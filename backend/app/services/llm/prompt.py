from dataclasses import dataclass


@dataclass
class IndexedSegment:
    index: int
    timestamp: str
    speaker: str
    text: str


def build_analysis_prompt(
    title: str, participants: list[str], segments: list[IndexedSegment]
) -> str:
    """Builds the analysis prompt.

    The transcript is presented as an explicitly indexed list so the model can
    only cite by integer index. Indices are far harder to hallucinate than free
    text and are trivially verifiable afterwards. This prompt is the first line of
    defense; deterministic verification still runs after generation.
    """
    transcript = "\n".join(f"[#{s.index}] ({s.timestamp}) {s.speaker}: {s.text}" for s in segments)
    people = ", ".join(participants) if participants else "none provided"

    return f"""You are a meticulous meeting analyst. Analyze the transcript below and extract structured insights.

MEETING: {title}
STATED PARTICIPANTS: {people}

TRANSCRIPT (each line is prefixed with its segment index in the form [#N]):
{transcript}

STRICT GROUNDING RULES:
- Use ONLY information explicitly present in the transcript.
- Do NOT invent attendees, action items, decisions, dates, or meeting outcomes.
- Do NOT add any information not explicitly stated.
- Every summary point, decision, follow-up, and action item MUST include at least one citation.
- A citation is the integer index N of the transcript segment that supports the statement.
- Only cite segments that genuinely support the statement. If you cannot ground a statement, omit it.
- For action items, set "assignee" only if the transcript clearly names who is responsible, else null.
- For action items, set "dueDate" (ISO 8601) only if a concrete date or deadline is stated, else null.

Produce a JSON object with these keys:
- "summary": array of {{ "text", "citations": [{{ "segmentIndex" }}] }}
- "decisions": array of {{ "text", "citations": [...] }}
- "followUps": array of {{ "text", "citations": [...] }}
- "actionItems": array of {{ "task", "assignee", "dueDate", "citations": [...] }}

Return ONLY the JSON object."""
