import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { SectionHeader } from "./section-header";

interface SectionCardProps {
  title: string;
  count?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Compact grouped clinical section: header + dense rows on a card surface. */
export function SectionCard({
  title,
  count,
  action,
  children,
  className,
}: SectionCardProps) {
  return (
    <section className={cn("rounded-xl border bg-card p-3", className)}>
      <SectionHeader title={title} count={count} action={action} />
      <div className="mt-1.5">{children}</div>
    </section>
  );
}
