import { ShieldCheck } from "lucide-react";
import { Badge } from "./ui/badge";
import { cn } from "@/lib/utils";
import type { ActionItemStatus, MeetingStatus } from "@/lib/types";

export function StatusBadge({ status }: { status: ActionItemStatus }) {
  const map = {
    PENDING: { variant: "warning" as const, label: "Pending" },
    IN_PROGRESS: { variant: "primary" as const, label: "In Progress" },
    COMPLETED: { variant: "success" as const, label: "Completed" },
  };
  const m = map[status];
  return <Badge variant={m.variant}>{m.label}</Badge>;
}

export function MeetingStatusBadge({ status }: { status: MeetingStatus }) {
  const map = {
    CREATED: { variant: "outline" as const, label: "Not analyzed" },
    ANALYZING: { variant: "warning" as const, label: "Analyzing" },
    ANALYZED: { variant: "success" as const, label: "Analyzed" },
    FAILED: { variant: "danger" as const, label: "Failed" },
  };
  const m = map[status];
  return <Badge variant={m.variant}>{m.label}</Badge>;
}

/** Visualizes the grounding confidence of an AI insight. */
export function GroundingScore({ score, className }: { score: number; className?: string }) {
  const pct = Math.round(score * 100);
  const tone =
    score >= 0.7 ? "text-success" : score >= 0.4 ? "text-warning" : "text-danger";
  const ring =
    score >= 0.7 ? "var(--success)" : score >= 0.4 ? "var(--warning)" : "var(--danger)";
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 text-xs font-medium", tone, className)}
      title={`Grounding confidence: ${pct}% (verified citations and lexical overlap)`}
    >
      <span
        className="inline-block size-3.5 rounded-full"
        style={{
          background: `conic-gradient(${ring} ${pct}%, var(--border) ${pct}%)`,
        }}
      />
      <ShieldCheck className="size-3.5" />
      {pct}% grounded
    </span>
  );
}
