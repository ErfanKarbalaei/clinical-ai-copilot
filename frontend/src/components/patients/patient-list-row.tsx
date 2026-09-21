import Link from "next/link";
import { ChevronLeftIcon, CircleAlertIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { calculateAge, faNum, formatDate, genderLabels } from "@/lib/format";
import type { Patient } from "@/lib/types";

/** Clinical status chips derived from the patient's existing overview data. */
export interface PatientRowStatus {
  severeAllergy: boolean;
  activeMedications: number;
  recordedProblems: number;
}

/**
 * Phase 3 patient directory row (~84px): identity (flexible, right) →
 * contact → last update → clinical status → action (left). Contact and
 * last-update columns are hidden below `xl` per the Pen responsive design;
 * on small screens the status chips wrap onto their own line so clinical
 * warnings stay visible.
 */
export function PatientListRow({
  patient,
  status,
}: {
  patient: Patient;
  status?: PatientRowStatus;
}) {
  const age = calculateAge(patient.date_of_birth);
  const meta = [
    age !== null ? `${faNum(age)} سال` : null,
    genderLabels[patient.gender],
  ]
    .filter(Boolean)
    .join(" · ");
  const initials = `${patient.first_name.charAt(0)} ${patient.last_name.charAt(0)}`;

  return (
    <li className="flex min-h-[84px] flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/50 px-4 last:border-0 hover:bg-surface-2/60">
      {/* identity — flexible, strongest visual anchor */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
          {initials}
        </span>
        <div className="min-w-0">
          <p className="truncate text-base leading-6 font-semibold">
            {patient.first_name} {patient.last_name}
          </p>
          <p className="truncate text-[13px] leading-5 text-muted-foreground">
            {meta}
          </p>
        </div>
      </div>

      {/* contact / identifiers (desktop) */}
      <div className="hidden shrink-0 flex-col items-start gap-1 xl:flex xl:w-[200px]">
        {patient.national_code ? (
          <span dir="ltr" className="font-mono text-xs text-muted-foreground tabular-nums">
            {patient.national_code}
          </span>
        ) : (
          <span className="text-xs text-faint">—</span>
        )}
        {patient.phone ? (
          <span dir="ltr" className="font-mono text-xs text-faint tabular-nums">
            {patient.phone}
          </span>
        ) : null}
      </div>

      {/* last update (desktop) */}
      <div className="hidden shrink-0 flex-col gap-0.5 xl:flex xl:w-[120px]">
        <span className="text-[10px] leading-4 text-faint">
          آخرین به‌روزرسانی
        </span>
        <span className="text-xs leading-5 text-muted-foreground">
          {formatDate(patient.updated_at)}
        </span>
      </div>

      {/* clinical status — semantic chips only, never overlapping */}
      {status ? (
        <div className="order-last flex w-full shrink-0 flex-wrap items-center gap-1.5 sm:order-none sm:w-[270px] sm:justify-end">
          {status.severeAllergy ? (
            <span className="inline-flex h-[26px] shrink-0 items-center gap-1.5 rounded-md border border-critical-border bg-critical-soft px-2.5 text-xs font-semibold text-critical">
              <CircleAlertIcon className="size-3.5 shrink-0" />
              حساسیت شدید
            </span>
          ) : null}
          {status.activeMedications > 0 ? (
            <span className="inline-flex h-[26px] shrink-0 items-center rounded-md bg-surface-2 px-2.5 text-xs font-medium text-muted-foreground">
              {faNum(status.activeMedications)} داروی فعال
            </span>
          ) : null}
          {status.recordedProblems > 0 ? (
            <span className="inline-flex h-[26px] shrink-0 items-center rounded-md bg-surface-2 px-2.5 text-xs font-medium text-muted-foreground">
              {faNum(status.recordedProblems)} مشکل ثبت‌شده
            </span>
          ) : null}
        </div>
      ) : null}

      {/* action */}
      <Button
        variant="outline"
        size="lg"
        className="shrink-0 gap-1 px-4 text-[13px]"
        render={<Link href={`/patients/${patient.id}`} />}
      >
        مشاهدهٔ پرونده
        <ChevronLeftIcon className="size-3.5" />
      </Button>
    </li>
  );
}
