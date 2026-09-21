import Link from "next/link";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { faNum } from "@/lib/format";

interface PatientListPaginationProps {
  page: number;
  totalPages: number;
  total: number;
  query: string;
}

function pageHref(targetPage: number, query: string): string {
  const search = new URLSearchParams();
  if (query) search.set("q", query);
  if (targetPage > 1) search.set("page", String(targetPage));
  const qs = search.toString();
  return qs ? `/patients?${qs}` : "/patients";
}

/** Windowed page numbers: ۱ … (current−1) current (current+1) … last */
function pageSequence(page: number, totalPages: number): (number | "…")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }
  const pages = new Set<number>([1, totalPages, page - 1, page, page + 1]);
  const sorted = [...pages]
    .filter((value) => value >= 1 && value <= totalPages)
    .sort((a, b) => a - b);
  const sequence: (number | "…")[] = [];
  let previous = 0;
  for (const value of sorted) {
    if (value - previous > 1) sequence.push("…");
    sequence.push(value);
    previous = value;
  }
  return sequence;
}

/**
 * Phase 3 clinical pagination (~40px): page info on the right, prev /
 * numbered pages / next flowing to the left (RTL). Active page uses the
 * clinical teal treatment. Pure links — existing `?page=` semantics.
 */
export function PatientListPagination({
  page,
  totalPages,
  total,
  query,
}: PatientListPaginationProps) {
  if (totalPages <= 1) return null;
  const sequence = pageSequence(page, totalPages);

  return (
    <nav
      aria-label="صفحه‌بندی بیماران"
      className="flex flex-wrap items-center justify-between gap-3"
    >
      <p className="text-[13px] text-muted-foreground">
        صفحهٔ {faNum(page)} از {faNum(totalPages)} · {faNum(total)} بیمار
      </p>
      <div className="flex items-center gap-1">
        {page > 1 ? (
          <Link
            href={pageHref(page - 1, query)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border bg-card px-3 text-[13px] font-medium hover:bg-surface-2"
          >
            قبلی
            <ChevronRightIcon className="size-3.5 text-muted-foreground" />
          </Link>
        ) : (
          <span
            aria-disabled="true"
            className="inline-flex h-8 items-center gap-1.5 px-3 text-[13px] text-faint"
          >
            قبلی
            <ChevronRightIcon className="size-3.5" />
          </span>
        )}

        {sequence.map((item, index) =>
          item === "…" ? (
            <span key={`dots-${index}`} className="px-1 text-[13px] text-faint">
              …
            </span>
          ) : item === page ? (
            <span
              key={item}
              aria-current="page"
              className="inline-flex size-8 items-center justify-center rounded-lg border border-brand-border bg-brand-soft text-[13px] font-semibold text-brand"
            >
              {faNum(item)}
            </span>
          ) : (
            <Link
              key={item}
              href={pageHref(item, query)}
              className="inline-flex size-8 items-center justify-center rounded-lg text-[13px] text-muted-foreground hover:bg-surface-2 hover:text-foreground"
            >
              {faNum(item)}
            </Link>
          )
        )}

        {page < totalPages ? (
          <Link
            href={pageHref(page + 1, query)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] text-muted-foreground hover:bg-surface-2 hover:text-foreground"
          >
            <ChevronLeftIcon className="size-3.5" />
            بعدی
          </Link>
        ) : (
          <span
            aria-disabled="true"
            className="inline-flex h-8 items-center gap-1.5 px-3 text-[13px] text-faint"
          >
            <ChevronLeftIcon className="size-3.5" />
            بعدی
          </span>
        )}
      </div>
    </nav>
  );
}
