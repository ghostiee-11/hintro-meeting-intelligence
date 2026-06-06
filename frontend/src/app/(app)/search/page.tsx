"use client";

import { useState } from "react";
import Link from "next/link";
import { Search as SearchIcon, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { SearchHit } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/misc";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    try {
      setHits(await api.search(q.trim()));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Semantic search</h1>
        <p className="text-sm text-muted-foreground">
          Ask in natural language across every meeting transcript.
        </p>
      </div>

      <form onSubmit={run} className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            placeholder="What did we decide about the launch?"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </form>

      {hits === null ? (
        <EmptyState
          icon={<Sparkles className="size-8" />}
          title="Search across your meetings"
          description="Embeddings find the moment you mean, even when the words differ. Falls back to keyword search when embeddings are unavailable."
        />
      ) : hits.length === 0 ? (
        <EmptyState icon={<SearchIcon className="size-8" />} title="No matches" description="Try a different phrasing." />
      ) : (
        <div className="space-y-3">
          {hits.map((h) => (
            <Link key={h.segmentId} href={`/meetings/${h.meetingId}`}>
              <Card className="transition-all hover:-translate-y-0.5 hover:shadow-md">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{h.meetingTitle}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={h.mode === "semantic" ? "primary" : "outline"}>{h.mode}</Badge>
                      <span>{Math.round(h.score * 100)}% match</span>
                    </div>
                  </div>
                  <p className="mt-2 text-sm">
                    <span className="font-mono text-xs text-muted-foreground">{h.timestamp} </span>
                    <span className="font-medium">{h.speaker}: </span>
                    {h.text}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
