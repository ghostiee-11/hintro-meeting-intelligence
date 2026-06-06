"""Parse free-form transcripts (pasted text, files, VTT/SRT) into structured segments.

Mirrors the frontend parser so meetings can be logged from Telegram or the web with
the same natural formats.
"""

import re

_TS = r"(\d{1,2}:\d{2}(?::\d{2})?)"


def _auto_ts(index: int) -> str:
    total = index * 30
    return f"{total // 60:02d}:{total % 60:02d}"


def _norm_ts(ts: str) -> str:
    clean = re.split(r"[.,]", ts)[0]
    parts = clean.split(":")
    if len(parts) == 3 and parts[0] == "00":
        return f"{parts[1]}:{parts[2]}"
    return clean


def parse_transcript(raw: str) -> list[dict]:
    text = (raw or "").strip()
    if not text:
        return []
    if "-->" in text:
        return _parse_timecoded(text)
    return _parse_lines(text)


def _parse_lines(text: str) -> list[dict]:
    segments: list[dict] = []
    last_speaker = "Speaker"
    for line in (line_.strip() for line_ in text.splitlines()):
        if not line:
            continue
        rest = line
        ts: str | None = None
        speaker: str | None = None

        lead = re.match(rf"^\[?{_TS}\]?\s*[-–]?\s*", rest)
        if lead:
            ts = lead.group(1)
            rest = rest[lead.end() :]

        paren = re.match(rf"^([^:]{{1,40}})\s*\({_TS}\)\s*:\s*", rest)
        if paren:
            speaker = paren.group(1).strip()
            ts = ts or paren.group(2)
            rest = rest[paren.end() :]
        else:
            colon = re.match(r"^([A-Za-z][\w .'-]{0,39}):\s+(.*)$", rest)
            if colon:
                speaker = colon.group(1).strip()
                rest = colon.group(2)

        if not rest:
            continue
        speaker = speaker or last_speaker
        last_speaker = speaker
        segments.append(
            {
                "timestamp": _norm_ts(ts) if ts else _auto_ts(len(segments)),
                "speaker": speaker,
                "text": rest,
            }
        )
    return segments


def _parse_timecoded(text: str) -> list[dict]:
    text = re.sub(r"(?m)^WEBVTT.*$", "", text)
    blocks = [b.strip() for b in re.split(r"\r?\n\r?\n", text) if b.strip()]
    segments: list[dict] = []
    last_speaker = "Speaker"
    for block in blocks:
        lines = [line.strip() for line in block.splitlines()]
        cue = next((line for line in lines if "-->" in line), None)
        if not cue:
            continue
        m = re.match(rf"^{_TS}", cue)
        ts = _norm_ts(m.group(1)) if m else _auto_ts(len(segments))
        body = " ".join(line for line in lines if "-->" not in line and not line.isdigit()).strip()
        if not body:
            continue
        speaker = last_speaker
        voice = re.match(r"^<v\s+([^>]+)>(.*)$", body)
        if voice:
            speaker = voice.group(1).strip()
            body = voice.group(2).replace("</v>", "").strip()
        else:
            colon = re.match(r"^([A-Za-z][\w .'-]{0,39}):\s+(.*)$", body)
            if colon:
                speaker = colon.group(1).strip()
                body = colon.group(2)
        body = re.sub(r"<[^>]+>", "", body).strip()
        if not body:
            continue
        last_speaker = speaker
        segments.append({"timestamp": ts, "speaker": speaker, "text": body})
    return segments
