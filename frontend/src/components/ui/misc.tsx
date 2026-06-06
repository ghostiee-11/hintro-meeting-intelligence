import * as React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-md bg-muted shimmer", className)} />
  );
}

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-card/50 px-6 py-16 text-center">
      {icon && <div className="text-muted-foreground">{icon}</div>}
      <div>
        <p className="font-medium">{title}</p>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
