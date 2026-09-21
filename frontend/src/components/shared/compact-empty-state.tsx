interface CompactEmptyStateProps {
  label: string;
  hint?: string;
}

/**
 * Dense clinical empty state (Phase 2) — one quiet line inside a section,
 * instead of a large centered block. Used for record sections that have no
 * data yet (allergies, medications, labs, documents, notes).
 */
export function CompactEmptyState({ label, hint }: CompactEmptyStateProps) {
  return (
    <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-xs leading-5 text-faint">
      {label}
      {hint ? <span className="text-[11px]"> · {hint}</span> : null}
    </p>
  );
}
