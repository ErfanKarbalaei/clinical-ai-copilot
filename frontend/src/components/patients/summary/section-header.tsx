import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  count?: string;
  action?: ReactNode;
}

/** Compact clinical section header: title + count chip (right), action (left). */
export function SectionHeader({ title, count, action }: SectionHeaderProps) {
  return (
    <div className="flex min-h-6 items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <h2 className="text-[13px] font-semibold leading-5">{title}</h2>
        {count ? (
          <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] leading-4 font-medium text-faint tabular-nums">
            {count}
          </span>
        ) : null}
      </div>
      {action}
    </div>
  );
}
