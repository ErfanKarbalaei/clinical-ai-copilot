import Link from "next/link";
import {
  ActivityIcon,
  ArrowUpLeftIcon,
  ClipboardListIcon,
  ExternalLinkIcon,
  FileTextIcon,
  FlaskConicalIcon,
  MicIcon,
  PillIcon,
  CircleAlertIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { WorkspaceTab } from "@/components/patients/workspace-tabs";
import { api } from "@/lib/api";
import { faNum } from "@/lib/format";
import type { EvidenceItem } from "@/lib/types";

/** Human-readable type labels — internal evidence ids are never shown. */
const typeLabels: Record<EvidenceItem["source_type"], string> = {
  medication: "داروی فعال",
  allergy: "حساسیت",
  condition: "مشکل بالینی",
  lab: "آزمایش",
  document: "سند",
  clinical_note: "یادداشت بالینی",
  voice_note: "یادداشت صوتی",
};

const typeIcons: Record<EvidenceItem["source_type"], LucideIcon> = {
  medication: PillIcon,
  allergy: CircleAlertIcon,
  condition: ActivityIcon,
  lab: FlaskConicalIcon,
  document: FileTextIcon,
  clinical_note: ClipboardListIcon,
  voice_note: MicIcon,
};

/** Where each evidence type lives inside the patient record tabs. */
const typeTabs: Record<EvidenceItem["source_type"], WorkspaceTab> = {
  medication: "medications",
  allergy: "summary",
  condition: "summary",
  lab: "labs",
  document: "documents",
  clinical_note: "documents",
  voice_note: "documents",
};

interface EvidenceListProps {
  patientId: number;
  evidence: EvidenceItem[];
}

/**
 * First-class clinical evidence UX (Phase 1 design): each chip shows the
 * source type icon, a human-readable description, and a navigation action —
 * either opening the original document or jumping to the matching record
 * tab. Raw implementation ids (e.g. `MED-42`) are never displayed.
 */
export function EvidenceList({ patientId, evidence }: EvidenceListProps) {
  if (evidence.length === 0) return null;
  return (
    <div className="space-y-1.5 border-t border-brand-border pt-2.5">
      <p className="flex items-baseline gap-2 text-[11px] font-semibold text-muted-foreground">
        منابع استفاده‌شده
        <span className="rounded bg-card px-1.5 py-0.5 text-[10px] font-normal text-faint tabular-nums">
          {faNum(evidence.length)}
        </span>
      </p>
      <ul className="space-y-1">
        {evidence.map((item) => {
          const Icon = typeIcons[item.source_type] ?? ActivityIcon;
          return (
            <li
              key={item.source_id}
              className="flex items-center gap-2 rounded-lg border border-transparent bg-card px-2.5 py-1"
            >
              <Icon className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="shrink-0 text-[11px] text-faint">
                {typeLabels[item.source_type]}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs leading-5 font-medium">
                {item.description}
              </span>
              {item.document_id != null ? (
                <a
                  href={api.documentDownloadUrl(item.document_id)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex shrink-0 items-center gap-0.5 text-[11px] font-medium text-brand hover:text-brand-strong"
                  title="مشاهدهٔ سند اصلی"
                >
                  سند
                  <ExternalLinkIcon className="size-3" />
                </a>
              ) : (
                <Link
                  href={`/patients/${patientId}?tab=${typeTabs[item.source_type]}`}
                  className="inline-flex shrink-0 items-center gap-0.5 text-[11px] font-medium text-brand hover:text-brand-strong"
                  title="مشاهده در پروندهٔ بیمار"
                >
                  پرونده
                  <ArrowUpLeftIcon className="size-3" />
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
