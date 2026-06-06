"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import { AlertTriangle, CalendarDays, CheckCircle2, ListChecks, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Analytics } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";

const STATUS_COLORS: Record<string, string> = {
  PENDING: "var(--warning)",
  IN_PROGRESS: "var(--primary)",
  COMPLETED: "var(--success)",
};

export default function DashboardPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .analytics()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }
  if (!data) return null;

  const kpis = [
    { label: "Meetings", value: data.totals.meetings, icon: CalendarDays },
    { label: "Action items", value: data.totals.actionItems, icon: ListChecks },
    { label: "Overdue", value: data.totals.overdue, icon: AlertTriangle, danger: true },
    { label: "Completed", value: data.totals.completed, icon: CheckCircle2, success: true },
  ];

  const statusData = Object.entries(data.statusDistribution).map(([name, value]) => ({
    name,
    value,
  }));
  const hasActivity = data.recentActivity.some((a) => a.created > 0);

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Your meeting intelligence at a glance.</p>
        </div>
        <Link href="/meetings">
          <Button>New meeting</Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="flex items-center gap-4 p-5">
              <div
                className={`grid size-11 place-items-center rounded-lg ${
                  k.danger
                    ? "bg-danger/15 text-danger"
                    : k.success
                      ? "bg-success/15 text-success"
                      : "bg-primary/12 text-primary"
                }`}
              >
                <k.icon className="size-5" />
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums">{k.value}</p>
                <p className="text-xs text-muted-foreground">{k.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Action items created (14 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {hasActivity ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={data.recentActivity}>
                  <defs>
                    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d) => d.slice(5)}
                    stroke="var(--muted-foreground)"
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      color: "var(--foreground)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="created"
                    stroke="var(--primary)"
                    strokeWidth={2}
                    fill="url(#g)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-[240px] place-items-center text-sm text-muted-foreground">
                No recent activity yet.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {data.totals.actionItems > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
                    {statusData.map((s) => (
                      <Cell key={s.name} fill={STATUS_COLORS[s.name]} stroke="var(--card)" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-[240px] place-items-center text-sm text-muted-foreground">
                No action items yet.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-success" /> Average grounding score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <span className="text-4xl font-bold tabular-nums">
                {Math.round(data.totals.avgGroundingScore * 100)}%
              </span>
              <span className="pb-1 text-sm text-muted-foreground">
                of AI insights are grounded in cited transcript segments
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-linear-to-r from-primary to-accent"
                style={{ width: `${Math.round(data.totals.avgGroundingScore * 100)}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Workload by assignee</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.byAssignee.length === 0 && (
              <p className="text-sm text-muted-foreground">No assigned work yet.</p>
            )}
            {data.byAssignee.map((a) => (
              <div key={a.assignee} className="flex items-center justify-between text-sm">
                <span className="font-medium">{a.assignee}</span>
                <span className="text-muted-foreground">
                  {a.open} open
                  {a.overdue > 0 && <span className="ml-2 text-danger">{a.overdue} overdue</span>}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
