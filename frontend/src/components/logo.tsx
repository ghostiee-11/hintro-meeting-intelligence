import { cn } from "@/lib/utils";

/**
 * Hintro logo. An abstract conversation waveform: five rounded bars that read as
 * both speech and signal, fitting a meeting-intelligence product.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground",
        className,
      )}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="2" y="9" width="3" height="6" rx="1.5" fill="currentColor" />
        <rect x="7" y="5" width="3" height="14" rx="1.5" fill="currentColor" />
        <rect x="12" y="2" width="3" height="20" rx="1.5" fill="currentColor" />
        <rect x="17" y="7" width="3" height="10" rx="1.5" fill="currentColor" />
        <rect x="22" y="10" width="2" height="4" rx="1" fill="currentColor" opacity="0.6" />
      </svg>
    </span>
  );
}

export function Logo({
  className,
  markClassName,
  wordClassName,
}: {
  className?: string;
  markClassName?: string;
  wordClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold", className)}>
      <LogoMark className={markClassName} />
      <span className={cn("text-lg tracking-tight", wordClassName)}>Hintro</span>
    </span>
  );
}
