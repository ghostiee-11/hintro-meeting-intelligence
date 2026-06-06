"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { BarChart3, CalendarDays, ListChecks, LogOut, Search } from "lucide-react";
import { cn, initials } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { ThemeToggle } from "./theme-toggle";
import { Button } from "./ui/button";
import { Logo } from "./logo";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/meetings", label: "Meetings", icon: CalendarDays },
  { href: "/action-items", label: "Action Items", icon: ListChecks },
  { href: "/search", label: "Search", icon: Search },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="grid min-h-dvh place-items-center text-sm text-muted-foreground">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-card/40 p-4 md:flex">
        <Link href="/dashboard" className="mb-8 px-2">
          <Logo />
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary/12 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto flex items-center gap-3 rounded-md border border-border p-3">
          <div className="grid size-9 shrink-0 place-items-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
            {initials(user.name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <Button variant="ghost" size="icon" aria-label="Log out" onClick={logout}>
            <LogOut className="size-4" />
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border glass px-6 py-3">
          <nav className="flex gap-1 md:hidden">
            {nav.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "grid size-9 place-items-center rounded-md",
                    active ? "bg-primary/12 text-primary" : "text-muted-foreground",
                  )}
                >
                  <item.icon className="size-4" />
                </Link>
              );
            })}
          </nav>
          <div className="hidden text-sm text-muted-foreground md:block">
            Grounded meeting intelligence
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={logout} className="md:hidden">
              Sign out
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
      </div>
    </div>
  );
}
