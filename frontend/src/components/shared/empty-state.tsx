import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
}

/** Persian empty-state block (no data, no JS needed). */
export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      {Icon ? (
        <span className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Icon className="size-6" />
        </span>
      ) : null}
      <p className="font-medium">{title}</p>
      {description ? (
        <p className="text-sm text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}
