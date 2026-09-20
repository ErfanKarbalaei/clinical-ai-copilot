import Link from "next/link";

import { formatDate } from "@/lib/format";

const TABS = [
  { key: "summary", label: "خلاصه" },
  { key: "timeline", label: "تایم‌لاین" },
  { key: "medications", label: "داروها" },
  { key: "labs", label: "آزمایش‌ها" },
  { key: "documents", label: "اسناد و یادداشت‌ها" },
] as const;

export type WorkspaceTab = (typeof TABS)[number]["key"];

/** Validate the `?tab=` search param — unknown values fall back to summary. */
export function parseWorkspaceTab(
  value: string | undefined
): WorkspaceTab {
  return (TABS.some((tab) => tab.key === value)
    ? value
    : "summary") as WorkspaceTab;
}

interface WorkspaceTabsProps {
  patientId: number;
  active: WorkspaceTab;
  updatedAt: string;
}

/** Internal patient-record tabs (Phase 1 design) — tabs flow from the right. */
export function WorkspaceTabs({
  patientId,
  active,
  updatedAt,
}: WorkspaceTabsProps) {
  return (
    <div className="flex items-end justify-between border-b bg-card px-4 lg:px-6">
      <nav
        className="flex items-end gap-4 lg:gap-6"
        aria-label="بخش‌های پرونده"
      >
        {TABS.map((tab) => {
          const isActive = tab.key === active;
          return (
            <Link
              key={tab.key}
              href={`/patients/${patientId}?tab=${tab.key}`}
              aria-current={isActive ? "page" : undefined}
              className={`relative pt-2 pb-2.5 text-[13px] transition-colors ${
                isActive
                  ? "font-semibold text-brand"
                  : "font-medium text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
              {isActive ? (
                <span
                  aria-hidden="true"
                  className="absolute inset-x-0 bottom-0 mx-auto h-0.5 w-5 rounded-full bg-brand"
                />
              ) : null}
            </Link>
          );
        })}
      </nav>
      <p className="hidden pb-2.5 text-xs text-faint sm:block">
        به‌روزرسانی پرونده: {formatDate(updatedAt)}
      </p>
    </div>
  );
}
