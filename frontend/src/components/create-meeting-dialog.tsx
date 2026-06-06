"use client";

import { useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileUp, Sparkles, Users, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Input, Label, Textarea } from "./ui/input";
import { Badge } from "./ui/badge";
import { api, ApiClientError } from "@/lib/api";
import { parseTranscript, uniqueSpeakers } from "@/lib/transcript";

const SAMPLE = `John: We should launch next Friday.
Alice: I will prepare the release notes by Wednesday.
Bob: We decided to use PostgreSQL for the new service.
Alice: Let's follow up on the marketing plan next week.`;

export function CreateMeetingDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [participants, setParticipants] = useState("");
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const segments = useMemo(() => parseTranscript(raw), [raw]);
  const speakers = useMemo(() => uniqueSpeakers(segments), [segments]);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setRaw(text);
    if (!title) setTitle(file.name.replace(/\.[^.]+$/, ""));
    toast.success(`Loaded ${file.name}`);
  }

  async function submit() {
    if (!title.trim()) {
      toast.error("Give the meeting a title");
      return;
    }
    if (segments.length === 0) {
      toast.error("Paste a transcript or some notes first");
      return;
    }
    setLoading(true);
    try {
      const meeting = await api.createMeeting({
        title: title.trim(),
        participants: participants
          .split(",")
          .map((p) => p.trim())
          .filter((p) => p.includes("@")),
        meetingDate: date ? new Date(date).toISOString() : new Date().toISOString(),
        transcript: segments,
      });
      toast.success("Meeting created");
      onCreated(meeting.id);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : "Failed to create meeting");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            className="max-h-[90dvh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-card p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-1 flex items-center justify-between">
              <h2 className="text-lg font-semibold">New meeting</h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="size-4" />
              </Button>
            </div>
            <p className="mb-5 text-sm text-muted-foreground">
              Paste a transcript in any format, or upload a file. We detect speakers and timestamps
              automatically.
            </p>

            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Title</Label>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Sprint Planning"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Date (optional)</Label>
                  <Input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label>Participants (optional, emails)</Label>
                <Input
                  value={participants}
                  onChange={(e) => setParticipants(e.target.value)}
                  placeholder="alice@example.com, bob@example.com"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Transcript</Label>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setRaw(SAMPLE)}>
                      Use sample
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} className="gap-1">
                      <FileUp className="size-3.5" /> Upload
                    </Button>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".txt,.vtt,.srt,.md,text/plain"
                      className="hidden"
                      onChange={onFile}
                    />
                  </div>
                </div>
                <Textarea
                  className="min-h-44"
                  value={raw}
                  onChange={(e) => setRaw(e.target.value)}
                  placeholder={
                    "Paste anything, e.g.\n\nAlice: I'll prepare the release notes.\n[00:35] Bob: Let's ship on Friday.\n\nWebVTT and SRT files work too."
                  }
                />
              </div>

              {/* Live parsed preview */}
              {segments.length > 0 && (
                <div className="rounded-md border border-border bg-muted/40 p-3">
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="primary">{segments.length} segments detected</Badge>
                    {speakers.length > 0 && (
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Users className="size-3.5" />
                        {speakers.slice(0, 6).join(", ")}
                        {speakers.length > 6 ? "..." : ""}
                      </span>
                    )}
                  </div>
                  <div className="max-h-36 space-y-1 overflow-y-auto">
                    {segments.slice(0, 8).map((s, i) => (
                      <div key={i} className="text-xs">
                        <span className="font-mono text-muted-foreground">{s.timestamp} </span>
                        <span className="font-medium">{s.speaker}: </span>
                        <span className="text-muted-foreground">{s.text}</span>
                      </div>
                    ))}
                    {segments.length > 8 && (
                      <p className="text-xs text-muted-foreground">+ {segments.length - 8} more</p>
                    )}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between gap-2 pt-1">
                <p className="text-xs text-muted-foreground">
                  <Sparkles className="mr-1 inline size-3.5" />
                  After creating, click Analyze to get grounded insights.
                </p>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button onClick={submit} disabled={loading || segments.length === 0}>
                    {loading ? "Creating..." : "Create meeting"}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
