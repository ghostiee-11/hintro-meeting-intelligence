"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight, ChevronLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { ActionItem, ActionItemStatus } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/misc";
import { GroundingScore } from "@/components/badges";
import { relativeDue } from "@/lib/utils";

const COLUMNS: { status: ActionItemStatus; label: string; tone: string }[] = [
  { status: "PENDING", label: "Pending", tone: "bg-warning" },
  { status: "IN_PROGRESS", label: "In Progress", tone: "bg-primary" },
  { status: "COMPLETED", label: "Completed", tone: "bg-success" },
];

const NEXT: Record<ActionItemStatus, ActionItemStatus | null> = {
  PENDING: "IN_PROGRESS",
  IN_PROGRESS: "COMPLETED",
  COMPLETED: null,
};
const PREV: Record<ActionItemStatus, ActionItemStatus | null> = {
  PENDING: null,
  IN_PROGRESS: "PENDING",
  COMPLETED: "IN_PROGRESS",
};

export default function ActionItemsPage() {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignee, setAssignee] = useState("");
  const [overdueOnly, setOverdueOnly] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const fetcher = overdueOnly
      ? api.overdue({ limit: 100, assignee: assignee || undefined })
      : api.listActionItems({ limit: 100, assignee: assignee || undefined });
    fetcher
      .then((res) => setItems(res.items))
      .finally(() => setLoading(false));
  }, [assignee, overdueOnly]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  async function move(item: ActionItem, status: ActionItemStatus) {
    const prev = items;
    setItems((cur) => cur.map((i) => (i.id === item.id ? { ...i, status } : i)));
    try {
      await api.updateStatus(item.id, status);
      toast.success(`Moved to ${status.replace("_", " ").toLowerCase()}`);
    } catch {
      setItems(prev);
      toast.error("Could not update status");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Action items</h1>
          <p className="text-sm text-muted-foreground">Track ownership and keep work from slipping.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Filter by assignee"
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            className="w-44"
          />
          <Button
            variant={overdueOnly ? "default" : "outline"}
            size="sm"
            onClick={() => setOverdueOnly((v) => !v)}
            className="gap-1"
          >
            <AlertTriangle className="size-4" /> Overdue
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-72" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {COLUMNS.map((col) => {
            const colItems = items.filter((i) => i.status === col.status);
            return (
              <div key={col.status} className="flex flex-col gap-3">
                <div className="flex items-center gap-2 px-1">
                  <span className={`size-2.5 rounded-full ${col.tone}`} />
                  <h2 className="text-sm font-semibold">{col.label}</h2>
                  <Badge variant="outline">{colItems.length}</Badge>
                </div>
                <div className="flex flex-col gap-3">
                  {colItems.length === 0 && (
                    <div className="rounded-lg border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
                      Nothing here
                    </div>
                  )}
                  {colItems.map((item) => {
                    const due = relativeDue(item.dueDate);
                    const prev = PREV[item.status];
                    const next = NEXT[item.status];
                    return (
                      <Card key={item.id}>
                        <CardContent className="space-y-3 p-4">
                          <p className="text-sm font-medium leading-snug">{item.task}</p>
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            {item.assignee && <Badge variant="outline">{item.assignee}</Badge>}
                            <span className={due.overdue ? "text-danger" : "text-muted-foreground"}>
                              {due.label}
                            </span>
                          </div>
                          {item.source === "AI" && <GroundingScore score={item.groundingScore} />}
                          <div className="flex items-center justify-between gap-2 pt-1">
                            <Link
                              href={`/meetings/${item.meetingId}`}
                              className="text-xs text-muted-foreground hover:text-foreground"
                            >
                              View meeting
                            </Link>
                            <div className="flex gap-1">
                              {prev && (
                                <Button variant="ghost" size="icon" onClick={() => move(item, prev)} aria-label="Move back">
                                  <ChevronLeft className="size-4" />
                                </Button>
                              )}
                              {next && (
                                <Button variant="subtle" size="sm" onClick={() => move(item, next)} className="gap-1">
                                  {next === "COMPLETED" ? "Complete" : "Start"}
                                  <ArrowRight className="size-3" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
