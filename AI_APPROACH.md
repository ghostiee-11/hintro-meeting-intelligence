# AI Approach

This document explains how the service generates meeting insights and, more importantly, how it guarantees those insights are grounded in the transcript rather than hallucinated.

## Goal

Generate a summary, decisions, follow-ups, and action items from a transcript, where **every** generated insight carries at least one citation referencing the transcript segment it was derived from, and the system never invents attendees, action items, decisions, or outcomes.

## Prompt design

The transcript is sent to the model as an **explicitly indexed list**:

```
[#0] (00:10) John: We should launch next Friday.
[#1] (00:20) Alice: I will prepare release notes.
```

The model is instructed to:

- Use only information explicitly present in the transcript.
- Never invent attendees, action items, decisions, dates, or outcomes.
- Attach to every insight and action item a `citations` array of **integer segment indices** (`{ "segmentIndex": N }`).
- Omit any statement it cannot ground.
- Set `assignee` / `dueDate` only when explicitly stated.

Citing by integer index (rather than free-form timestamps or quotes) is deliberate: an index is far harder to fabricate plausibly and is trivially checkable against the segment list. This is the first line of defense.

## Structured output

The model is constrained to return JSON. With Gemini we request `application/json`; with Groq we use JSON mode. The raw output is then **normalized** defensively (`app/services/llm/json_util.py`): it tolerates fenced code blocks, bare-number citations, and snake_case keys, and discards malformed entries. We never assume the model returned perfect JSON.

## Citation strategy and grounding verification (the core)

After generation, a deterministic, LLM-free verifier (`app/services/grounding.py`) enforces grounding **by construction**:

1. **Resolve citations.** For each citation, look up its `segmentIndex` in the real transcript. If it does not resolve, the citation is dropped. Verified citations are linked to the actual `TranscriptSegment` row (and its true timestamp).
2. **Discard ungrounded insights.** Any insight or action item left with **zero** verified citations is discarded entirely and counted in `droppedCount`. This makes the rule "every insight has at least one citation" true by construction, not by hope.
3. **Score grounding.** Each surviving insight gets a `groundingScore` in `[0, 1]`:
   `0.5 * citationCoverage + 0.5 * bestLexicalOverlap`
   where coverage is verified/claimed citations, and overlap is the fraction of the insight's content words that appear in its best-matching cited segment (stopwords removed).
4. **Persist only verified output.** Insights, action items, and their verified citations are written in one transaction; the meeting status becomes `ANALYZED` (or `FAILED` on error).

The frontend surfaces this: each insight shows its grounding score, and clicking a citation chip highlights and scrolls to the exact source segment, so a reviewer can verify any claim in one click.

## Hallucination prevention approach (summary)

- Index-based citations the model cannot easily fake.
- Deterministic resolution of every citation against real segments.
- Hard discard of zero-citation insights.
- A grounding score that penalizes real-but-irrelevant citations via lexical overlap.
- Re-analysis replaces prior AI output but preserves manually created action items.

The net effect: unsupported or hallucinated content cannot reach a stored insight, which directly targets the assignment's grounding requirement.

## Output validation

- LLM JSON is parsed and normalized before use; unparseable output triggers the provider fallback.
- Dates are parsed safely; an unparseable `dueDate` becomes `null` rather than failing the request.
- All API inputs are validated by Pydantic (emails, required fields, enums, ISO dates).

## Provider resilience

`app/services/llm/service.py` tries Gemini first, then Groq, logging each attempt with the request trace id. If all configured providers fail, the analyze endpoint returns a typed `UPSTREAM_ERROR` and the meeting is marked `FAILED` rather than left hanging. Analysis results are persisted, so re-viewing a meeting never re-calls the LLM.

## Known limitations

- **Lexical overlap is a heuristic.** A correct paraphrase that shares few words with its source can receive a lower score. We keep such insights (with the visible low score) rather than dropping them, and log drops, so the behavior is transparent.
- **Grounding verifies provenance, not truth.** It confirms a statement is supported by the cited segment; it does not fact-check the speaker.
- **Index drift.** Citations are resolved at analysis time against the stored segment ordinals; transcripts are immutable after creation, so indices remain stable.
- **LLM quality varies by provider.** The fallback (Groq) may produce slightly different phrasing than Gemini; grounding verification is applied identically to both.
- **Embeddings are best-effort.** If no embedding key is configured, semantic search falls back to keyword search and the embedding step is skipped without failing analysis.
