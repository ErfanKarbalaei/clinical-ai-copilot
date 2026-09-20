import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  count?: string;
  action?: ReactNode;
}

/** Compact clinical section header: title + count (right), action (left). */
export function SectionHeader({ title, count, action }: SectionHeaderProps) {
  return (
    <div className="flex min-h-6 items-center justify-between gap-2">
      <div className="flex items-baseline gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {count ? <span className="text-xs text-faint">{count}</span> : null}
      </div>
      {action}
    </div>
  );
}
