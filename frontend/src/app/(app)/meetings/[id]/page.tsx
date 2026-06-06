"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CalendarDays,
  Loader2,
  Quote,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { api, analyzeStreamUrl } from "@/lib/api";
import type { Insight, MeetingDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/misc";
import { GroundingScore, MeetingStatusBadge, StatusBadge } from "@/components/badges";
import { formatDate, cn } from "@/lib/utils";

export default function MeetingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<number | null>(null);
  const segmentRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const load = useCallback(() => {
    api
      .getMeeting(id)
      .then(setMeeting)
      .catch(() => toast.error("Could not load meeting"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => load(), [load]);

  const focusSegment = (ordinal: number | null | undefined) => {
    if (ordinal === null || ordinal === undefined) return;
    setHighlight(ordinal);
    segmentRefs.current[ordinal]?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => setHighlight((h) => (h === ordinal ? null : h)), 2200);
  };

  const analyze = () => {
    setAnalyzing(true);
    setStage("Starting");
    const es = new EventSource(analyzeStreamUrl(id));
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { stage: string; message?: string; error?: string };
        if (data.stage === "error") {
          toast.error(data.error || "Analysis failed");
          es.close();
          setAnalyzing(false);
          setStage(null);
          load();
          return;
        }
        setStage(data.message || data.stage);
        if (data.stage === "done") {
          es.close();
          setAnalyzing(false);
          setStage(null);
          toast.success("Analysis complete");
          load();
        }
      } catch {
        /* ignore keep-alive */
      }
    };
    es.onerror = () => {
      es.close();
      setAnalyzing(false);
      setStage(null);
    };
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }
  if (!meeting) return null;

  const hasInsights =
    meeting.insights.length > 0 || meeting.actionItems.some((a) => a.source === "AI");

  return (
    <div className="space-y-6">
      <Link
        href="/meetings"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Back to meetings
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{meeting.title}</h1>
            <MeetingStatusBadge status={meeting.status} />
          </div>
          <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <CalendarDays className="size-4" /> {formatDate(meeting.meetingDate)}
            </span>
            <span className="flex items-center gap-1">
              <Users className="size-4" /> {meeting.participants.join(", ") || "No participants"}
            </span>
          </div>
        </div>
        <Button onClick={analyze} disabled={analyzing} className="gap-2">
          {analyzing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
          {analyzing ? "Analyzing..." : hasInsights ? "Re-analyze" : "Analyze meeting"}
        </Button>
      </div>

      {analyzing && stage && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/8 px-4 py-3 text-sm"
        >
          <Loader2 className="size-4 animate-spin text-primary" />
          <span className="font-medium">{stage}</span>
          <span className="text-muted-foreground">Streaming live progress...</span>
        </motion.div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Transcript */}
        <Card className="h-fit lg:sticky lg:top-20">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Transcript
              <span className="text-xs font-normal text-muted-foreground">
                {meeting.transcript.length} segments
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {meeting.transcript.map((seg) => (
              <div
                key={seg.id}
                ref={(el) => {
                  segmentRefs.current[seg.ordinal] = el;
                }}
                className={cn(
                  "rounded-md border border-transparent px-3 py-2 transition-colors",
                  highlight === seg.ordinal
                    ? "border-primary/40 bg-primary/10"
                    : "hover:bg-muted/60",
                )}
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{seg.timestamp}</span>
                  <span className="font-medium text-foreground">{seg.speaker}</span>
                  <span className="ml-auto rounded bg-muted px-1.5 font-mono">#{seg.ordinal}</span>
                </div>
                <p className="mt-1 text-sm">{seg.text}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Insights */}
        <div className="space-y-6">
          {!hasInsights && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <Sparkles className="size-8 text-muted-foreground" />
                <p className="font-medium">No analysis yet</p>
                <p className="text-sm text-muted-foreground">
                  Run analysis to extract grounded summaries, decisions, follow-ups, and action
                  items, each with verifiable citations.
                </p>
              </CardContent>
            </Card>
          )}

          <InsightGroup title="Summary" insights={meeting.insights.filter((i) => i.type === "SUMMARY")} onCite={focusSegment} />
          <InsightGroup title="Decisions" insights={meeting.insights.filter((i) => i.type === "DECISION")} onCite={focusSegment} />
          <InsightGroup title="Follow-ups" insights={meeting.insights.filter((i) => i.type === "FOLLOW_UP")} onCite={focusSegment} />

          {meeting.actionItems.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Action items</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {meeting.actionItems.map((a) => (
                  <div key={a.id} className="rounded-md border border-border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium">{a.task}</p>
                      <StatusBadge status={a.status} />
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {a.assignee && <Badge variant="outline">{a.assignee}</Badge>}
                      {a.source === "AI" && <GroundingScore score={a.groundingScore} />}
                      {a.citations.map((c, i) => (
                        <CitationChip key={i} timestamp={c.timestamp} onClick={() => onCiteSegment(c.segmentIndex, focusSegment)} />
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function onCiteSegment(
  segmentIndex: number | null | undefined,
  focus: (o: number | null | undefined) => void,
) {
  focus(segmentIndex);
}

function InsightGroup({
  title,
  insights,
  onCite,
}: {
  title: string;
  insights: Insight[];
  onCite: (ordinal: number | null | undefined) => void;
}) {
  if (insights.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {insights.map((insight) => (
          <div key={insight.id} className="space-y-2">
            <p className="text-sm leading-relaxed">{insight.text}</p>
            <div className="flex flex-wrap items-center gap-2">
              <GroundingScore score={insight.groundingScore} />
              {insight.citations.map((c, i) => (
                <CitationChip key={i} timestamp={c.timestamp} onClick={() => onCite(c.segmentIndex)} />
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CitationChip({ timestamp, onClick }: { timestamp: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
      title="Jump to the cited transcript segment"
    >
      <Quote className="size-3" />
      {timestamp}
    </button>
  );
}
