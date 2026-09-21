import Link from "next/link";
import {
  ActivityIcon,
  ChevronLeftIcon,
  CircleAlertIcon,
  ClipboardListIcon,
  FileTextIcon,
  FlaskConicalIcon,
  ScanIcon,
  TriangleAlertIcon,
} from "lucide-react";

import {
  AddAllergyButton,
  AllergyRowActions,
} from "@/components/patients/allergy-actions";
import {
  AddConditionButton,
  ConditionRowActions,
} from "@/components/patients/condition-actions";
import type { WorkspaceTab } from "@/components/patients/workspace-tabs";
import { CompactEmptyState } from "@/components/shared/compact-empty-state";
import { Badge } from "@/components/ui/badge";
import {
  allergySeverityLabels,
  documentTypeLabels,
  faNum,
  formatDate,
  medicationStatusLabels,
  resultFlagLabels,
} from "@/lib/format";
import type {
  Allergy,
  AllergySeverity,
  Condition,
  Document,
  DocumentType,
  LabResult,
  PatientMedication,
  ResultFlag,
} from "@/lib/types";
import { SectionCard } from "./section-card";

const LAB_GRID =
  "grid grid-cols-[minmax(0,1fr)_110px_120px_92px_88px] items-center gap-2";
const ROW_DIVIDE = "border-b border-border/50 last:border-0";

function ViewAllLink({
  patientId,
  tab,
}: {
  patientId: number;
  tab: Extract<WorkspaceTab, "medications" | "labs" | "documents">;
}) {
  return (
    <Link
      href={`/patients/${patientId}?tab=${tab}`}
      className="inline-flex items-center gap-0.5 text-[11px] font-medium text-brand hover:text-brand-strong"
    >
      مشاهدهٔ همه
      <ChevronLeftIcon className="size-3" />
    </Link>
  );
}

function flagClass(flag: ResultFlag | null): string {
  switch (flag) {
    case "critical":
      return "text-critical";
    case "abnormal":
      return "text-warning";
    case "normal":
      return "text-success";
    default:
      return "text-faint";
  }
}

function severityTextClass(severity: AllergySeverity): string {
  switch (severity) {
    case "severe":
      return "text-critical";
    case "moderate":
      return "text-warning";
    default:
      return "text-muted-foreground";
  }
}

function documentIcon(docType: DocumentType) {
  switch (docType) {
    case "lab_report":
      return <FlaskConicalIcon className="size-3.5" />;
    case "imaging_report":
      return <ScanIcon className="size-3.5" />;
    case "medical_note":
      return <ClipboardListIcon className="size-3.5" />;
    default:
      return <FileTextIcon className="size-3.5" />;
  }
}

/* ------------------------------------------------------------------ */
/* 1. Critical alerts — compact, prominent, immediately visible        */
/* ------------------------------------------------------------------ */

function CriticalAlerts({ allergies }: { allergies: Allergy[] }) {
  const severe = allergies.filter((allergy) => allergy.severity === "severe");
  const others = allergies.filter((allergy) => allergy.severity !== "severe");

  if (severe.length === 0) {
    if (others.length === 0) return null;
    // no severe allergy — keep recorded allergies visible, without alarm
    return (
      <div className="flex items-center gap-2.5 rounded-xl border bg-card p-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground">
          <CircleAlertIcon className="size-4" />
        </span>
        <div className="min-w-0 ps-0.5">
          <p className="text-[13px] font-semibold leading-5">حساسیت‌های ثبت‌شده</p>
          <p className="truncate text-[11px] leading-4 text-muted-foreground">
            {others
              .map(
                (allergy) =>
                  `${allergy.allergen} (${allergySeverityLabels[allergy.severity]})`
              )
              .join("، ")}
          </p>
        </div>
      </div>
    );
  }

  const subline = [
    severe[0].reaction ? `واکنش: ${severe[0].reaction}` : null,
    severe.length > 1
      ? `آلرژی شدید دیگر: ${severe
          .slice(1)
          .map((allergy) => allergy.allergen)
          .join("، ")}`
      : null,
    others.length > 0
      ? `آلرژی دیگر: ${others
          .map(
            (allergy) =>
              `${allergy.allergen} (${allergySeverityLabels[allergy.severity]})`
          )
          .join("، ")}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-critical-border bg-critical-soft p-3">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-card text-critical">
        <TriangleAlertIcon className="size-4" />
      </span>
      <div className="min-w-0 ps-0.5">
        <p className="text-[13px] leading-5 font-semibold text-critical">
          حساسیت شدید — {severe[0].allergen}
        </p>
        {subline ? (
          <p className="truncate text-[11px] leading-4 text-muted-foreground">
            {subline}
          </p>
        ) : null}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 2. Active problems (conditions management lives here — no own tab)  */
/* ------------------------------------------------------------------ */

function ActiveProblems({
  patientId,
  conditions,
}: {
  patientId: number;
  conditions: Condition[];
}) {
  const active = conditions.filter((condition) => condition.status === "active");
  return (
    <SectionCard
      title="مشکلات فعال"
      count={active.length > 0 ? `${faNum(active.length)}` : undefined}
      action={<AddConditionButton patientId={patientId} />}
    >
      {active.length === 0 ? (
        <CompactEmptyState label="مشکل فعالی ثبت نشده است" />
      ) : (
        <ul>
          {active.map((condition) => (
            <li
              key={condition.id}
              className={`flex items-center gap-2.5 py-1.5 ${ROW_DIVIDE}`}
            >
              <span className="flex size-6.5 shrink-0 items-center justify-center rounded-md bg-surface-2 text-muted-foreground">
                <ActivityIcon className="size-3.5" />
              </span>
              <p className="min-w-0 flex-1 truncate text-[13px] leading-5 font-medium">
                {condition.name}
              </p>
              <span className="shrink-0 text-[11px] text-faint">
                {condition.onset_date
                  ? `از ${formatDate(condition.onset_date)}`
                  : ""}
              </span>
              <ConditionRowActions
                patientId={patientId}
                condition={condition}
              />
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ */
/* 3a. Allergies (management preserved — summary is its only surface)  */
/* ------------------------------------------------------------------ */

function AllergyList({
  patientId,
  allergies,
}: {
  patientId: number;
  allergies: Allergy[];
}) {
  return (
    <SectionCard
      title="حساسیت‌ها"
      count={allergies.length > 0 ? `${faNum(allergies.length)}` : undefined}
      action={<AddAllergyButton patientId={patientId} />}
    >
      {allergies.length === 0 ? (
        <CompactEmptyState label="بدون حساسیت ثبت‌شده" />
      ) : (
        <ul>
          {allergies.map((allergy) => (
            <li
              key={allergy.id}
              className={`flex items-center gap-2 py-1.5 ${ROW_DIVIDE}`}
            >
              <p className="min-w-0 flex-1 truncate text-[13px] leading-5 font-medium">
                {allergy.allergen}
              </p>
              <Badge
                variant="outline"
                className={severityTextClass(allergy.severity)}
              >
                {allergySeverityLabels[allergy.severity]}
              </Badge>
              <AllergyRowActions patientId={patientId} allergy={allergy} />
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ */
/* 3b. Active medications — dense rows with LTR/mono doses             */
/* ------------------------------------------------------------------ */

function ActiveMedications({
  patientId,
  medications,
}: {
  patientId: number;
  medications: PatientMedication[];
}) {
  const active = medications.filter((record) => record.status === "active");
  return (
    <SectionCard
      title="داروهای فعال"
      count={`${faNum(active.length)} از ${faNum(medications.length)}`}
      action={<ViewAllLink patientId={patientId} tab="medications" />}
    >
      {active.length === 0 ? (
        <CompactEmptyState
          label="داروی فعالی ثبت نشده است"
          hint="افزودن از تب داروها"
        />
      ) : (
        <ul>
          {active.map((record) => (
            <li
              key={record.id}
              className={`flex items-center gap-2 py-1.5 ${ROW_DIVIDE}`}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] leading-5 font-medium">
                  {record.medication.name}
                </p>
                {record.medication.generic_name ? (
                  <p
                    dir="ltr"
                    className="truncate text-right font-mono text-[10px] leading-4 text-faint"
                  >
                    {record.medication.generic_name}
                  </p>
                ) : null}
              </div>
              <span
                dir="ltr"
                className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground"
              >
                {record.dosage ?? "—"}
              </span>
              <span className="flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground">
                <span className="size-1.5 rounded-full bg-success" />
                {medicationStatusLabels[record.status]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ */
/* 4. Recent labs — semantic flags, tabular LTR values                 */
/* ------------------------------------------------------------------ */

function RecentLabs({
  patientId,
  labResults,
}: {
  patientId: number;
  labResults: LabResult[];
}) {
  const recent = labResults.slice(0, 5);
  return (
    <SectionCard
      title="آزمایش‌های اخیر"
      count={`${faNum(recent.length)} از ${faNum(labResults.length)}`}
      action={<ViewAllLink patientId={patientId} tab="labs" />}
    >
      {recent.length === 0 ? (
        <CompactEmptyState label="نتیجهٔ آزمایشی ثبت نشده است" />
      ) : (
        <>
          <div className={`${LAB_GRID} pb-1 text-[11px] text-faint`}>
            <span>آزمایش</span>
            <span>مقدار</span>
            <span>محدودهٔ مرجع</span>
            <span>وضعیت</span>
            <span>تاریخ</span>
          </div>
          <ul>
            {recent.map((lab) => (
              <li
                key={lab.id}
                className={`${LAB_GRID} py-1.5 ${ROW_DIVIDE}`}
              >
                <span className="truncate text-[13px] leading-5 font-medium">
                  {lab.test_name}
                </span>
                <span
                  dir="ltr"
                  className="truncate text-left font-mono text-[13px] font-semibold tabular-nums"
                >
                  {lab.value}
                  {lab.unit ? ` ${lab.unit}` : ""}
                </span>
                <span
                  dir="ltr"
                  className="truncate text-left font-mono text-[11px] text-faint tabular-nums"
                >
                  {lab.reference_range ?? "—"}
                </span>
                {lab.flag ? (
                  <span
                    className={`flex items-center gap-1.5 text-[11px] ${flagClass(lab.flag)}`}
                  >
                    <span className="size-1.5 shrink-0 rounded-full bg-current" />
                    {resultFlagLabels[lab.flag]}
                  </span>
                ) : (
                  <span className="text-[11px] text-faint">—</span>
                )}
                <span className="text-[11px] text-faint">
                  {lab.result_date ? formatDate(lab.result_date) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ */
/* 5. Recent documents — single-line scannable rows                    */
/* ------------------------------------------------------------------ */

function RecentDocuments({
  patientId,
  documents,
}: {
  patientId: number;
  documents: Document[];
}) {
  const recent = documents.slice(0, 3);
  return (
    <SectionCard
      title="اسناد و یادداشت‌های اخیر"
      count={`${faNum(recent.length)} از ${faNum(documents.length)}`}
      action={<ViewAllLink patientId={patientId} tab="documents" />}
    >
      {recent.length === 0 ? (
        <CompactEmptyState
          label="سندی بارگذاری نشده است"
          hint="بارگذاری از تب اسناد و یادداشت‌ها"
        />
      ) : (
        <ul>
          {recent.map((document) => (
            <li
              key={document.id}
              className={`flex items-center gap-2.5 py-1.5 ${ROW_DIVIDE}`}
            >
              <span className="flex size-6.5 shrink-0 items-center justify-center rounded-md bg-surface-2 text-muted-foreground">
                {documentIcon(document.doc_type)}
              </span>
              <p className="min-w-0 flex-1 truncate text-[13px] leading-5 font-medium">
                {document.title}
              </p>
              <span className="shrink-0 text-[11px] text-faint">
                {documentTypeLabels[document.doc_type]} ·{" "}
                {formatDate(document.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ */
/* Summary view — a physician's ~10-second review before the visit     */
/* ------------------------------------------------------------------ */

interface SummaryViewProps {
  patientId: number;
  conditions: Condition[];
  allergies: Allergy[];
  medications: PatientMedication[];
  labResults: LabResult[];
  documents: Document[];
}

export function SummaryView({
  patientId,
  conditions,
  allergies,
  medications,
  labResults,
  documents,
}: SummaryViewProps) {
  return (
    <div className="space-y-3">
      <CriticalAlerts allergies={allergies} />
      <ActiveProblems patientId={patientId} conditions={conditions} />
      {/* allergies + medications side by side on clinical desktop widths */}
      <div className="grid gap-3 lg:grid-cols-2">
        <AllergyList patientId={patientId} allergies={allergies} />
        <ActiveMedications patientId={patientId} medications={medications} />
      </div>
      <RecentLabs patientId={patientId} labResults={labResults} />
      <RecentDocuments patientId={patientId} documents={documents} />
    </div>
  );
}
