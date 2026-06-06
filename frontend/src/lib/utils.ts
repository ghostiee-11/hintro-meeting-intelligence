import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "No date";
  const d = new Date(value);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeDue(value: string | null | undefined): { label: string; overdue: boolean } {
  if (!value) return { label: "No due date", overdue: false };
  const due = new Date(value).getTime();
  const now = Date.now();
  const diffDays = Math.round((due - now) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { label: `${Math.abs(diffDays)}d overdue`, overdue: true };
  if (diffDays === 0) return { label: "Due today", overdue: false };
  return { label: `Due in ${diffDays}d`, overdue: false };
}

export function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
