export interface ParsedSegment {
  timestamp: string;
  speaker: string;
  text: string;
}

const TS = "(\\d{1,2}:\\d{2}(?::\\d{2})?)";

/**
 * Parses a free-form transcript into structured segments so any user can paste a
 * real transcript (Zoom/Meet/Otter/Teams export, plain notes, or VTT/SRT) instead
 * of a rigid format. Detects speakers and timestamps; fills sensible defaults when
 * they are missing (sequential timestamps, carried-over speaker).
 */
export function parseTranscript(raw: string): ParsedSegment[] {
  const text = raw.trim();
  if (!text) return [];
  if (/-->/.test(text)) return parseTimecoded(text);
  return parseLines(text);
}

function autoTimestamp(index: number): string {
  const total = index * 30;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function normalizeTs(ts: string): string {
  // Strip a leading hour of 00 and milliseconds for compact display.
  const clean = ts.split(/[.,]/)[0];
  const parts = clean.split(":");
  if (parts.length === 3 && parts[0] === "00") return `${parts[1]}:${parts[2]}`;
  return clean;
}

function parseLines(text: string): ParsedSegment[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const segments: ParsedSegment[] = [];
  let lastSpeaker = "Speaker";

  for (const line of lines) {
    let rest = line;
    let ts: string | undefined;
    let speaker: string | undefined;

    // Leading [00:10] or 00:10 (optionally followed by a dash).
    const lead = rest.match(new RegExp(`^\\[?${TS}\\]?\\s*[-–]?\\s*`));
    if (lead) {
      ts = lead[1];
      rest = rest.slice(lead[0].length);
    }

    // "Speaker (00:10):" form.
    const withParen = rest.match(new RegExp(`^([^:]{1,40})\\s*\\(${TS}\\)\\s*:\\s*`));
    if (withParen) {
      speaker = withParen[1].trim();
      if (!ts) ts = withParen[2];
      rest = rest.slice(withParen[0].length);
    } else {
      // "Speaker: text" form (short, name-like speaker only).
      const withColon = rest.match(/^([A-Za-z][\w .'-]{0,39}):\s+(.*)$/);
      if (withColon) {
        speaker = withColon[1].trim();
        rest = withColon[2];
      }
    }

    if (!rest) continue;
    if (!speaker) speaker = lastSpeaker;
    lastSpeaker = speaker;

    segments.push({
      timestamp: ts ? normalizeTs(ts) : autoTimestamp(segments.length),
      speaker,
      text: rest,
    });
  }

  return segments;
}

/** Handles WebVTT and SRT: cues separated by blank lines, a line containing -->. */
function parseTimecoded(text: string): ParsedSegment[] {
  const blocks = text
    .replace(/^WEBVTT.*$/m, "")
    .split(/\r?\n\r?\n/)
    .map((b) => b.trim())
    .filter(Boolean);

  const segments: ParsedSegment[] = [];
  let lastSpeaker = "Speaker";

  for (const block of blocks) {
    const blockLines = block.split(/\r?\n/).map((l) => l.trim());
    const cueLine = blockLines.find((l) => l.includes("-->"));
    if (!cueLine) continue;
    const tsMatch = cueLine.match(new RegExp(`^${TS}`));
    const ts = tsMatch ? normalizeTs(tsMatch[1]) : autoTimestamp(segments.length);

    let body = blockLines
      .filter((l) => !l.includes("-->") && !/^\d+$/.test(l))
      .join(" ")
      .trim();
    if (!body) continue;

    let speaker = lastSpeaker;
    const voice = body.match(/^<v\s+([^>]+)>(.*)$/);
    if (voice) {
      speaker = voice[1].trim();
      body = voice[2].replace(/<\/v>/g, "").trim();
    } else {
      const colon = body.match(/^([A-Za-z][\w .'-]{0,39}):\s+(.*)$/);
      if (colon) {
        speaker = colon[1].trim();
        body = colon[2];
      }
    }
    body = body.replace(/<[^>]+>/g, "").trim();
    if (!body) continue;
    lastSpeaker = speaker;
    segments.push({ timestamp: ts, speaker, text: body });
  }

  return segments;
}

/** Unique speaker names detected, useful for showing who was in the meeting. */
export function uniqueSpeakers(segments: ParsedSegment[]): string[] {
  return [...new Set(segments.map((s) => s.speaker))];
}
