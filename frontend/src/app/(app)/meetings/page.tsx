"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CalendarDays, Plus, Search, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { MeetingSummary, Paginated } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, Skeleton, EmptyState } from "@/components/ui/misc";
import { MeetingStatusBadge } from "@/components/badges";
import { CreateMeetingDialog } from "@/components/create-meeting-dialog";
import { formatDate } from "@/lib/utils";

export default function MeetingsPage() {
  const router = useRouter();
  const [data, setData] = useState<Paginated<MeetingSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listMeetings({ page, limit: 9, search, status })
      .then(setData)
      .finally(() => setLoading(false));
  }, [page, search, status]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Meetings</h1>
          <p className="text-sm text-muted-foreground">Store transcripts and generate grounded insights.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="gap-2">
          <Plus className="size-4" /> New meeting
        </Button>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title..."
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        >
          <option value="">All statuses</option>
          <option value="CREATED">Not analyzed</option>
          <option value="ANALYZED">Analyzed</option>
          <option value="ANALYZING">Analyzing</option>
          <option value="FAILED">Failed</option>
        </Select>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((m) => (
              <Link key={m.id} href={`/meetings/${m.id}`}>
                <Card className="h-full transition-all hover:-translate-y-1 hover:shadow-md">
                  <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold leading-snug">{m.title}</h3>
                      <MeetingStatusBadge status={m.status} />
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <CalendarDays className="size-3.5" /> {formatDate(m.meetingDate)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="size-3.5" /> {m.participants.length}
                      </span>
                    </div>
                    <div className="mt-auto flex gap-4 text-xs text-muted-foreground">
                      <span>{m.segmentCount} segments</span>
                      <span>{m.actionItemCount} action items</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.meta.page} of {data.meta.totalPages} ({data.meta.total} total)
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.meta.totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      ) : (
        <EmptyState
          icon={<CalendarDays className="size-8" />}
          title="No meetings yet"
          description="Create your first meeting to generate grounded AI insights."
          action={<Button onClick={() => setDialogOpen(true)}>New meeting</Button>}
        />
      )}

      <CreateMeetingDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(id) => router.push(`/meetings/${id}`)}
      />
    </div>
  );
}
