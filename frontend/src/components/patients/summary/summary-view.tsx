import Link from "next/link";
import {
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
import { EmptyState } from "@/components/shared/empty-state";
import { Badge } from "@/components/ui/badge";
import type { WorkspaceTab } from "@/components/patients/workspace-tabs";
import {
  allergySeverityLabels,
  documentTypeLabels,
  faNum,
  formatDate,
  formatDateTime,
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
import { SectionHeader } from "./section-header";

const MED_GRID =
  "grid grid-cols-[minmax(0,1fr)_110px_100px_84px] items-center gap-2";
const LAB_GRID =
  "grid grid-cols-[minmax(0,1fr)_110px_120px_92px_88px] items-center gap-2";

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
      className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-strong"
    >
      مشاهدهٔ همه
      <ChevronLeftIcon className="size-3.5" />
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
/* 1. Critical alerts — severe allergies, calm but impossible to miss  */
/* ------------------------------------------------------------------ */

function CriticalAlerts({ allergies }: { allergies: Allergy[] }) {
  const severe = allergies.filter((allergy) => allergy.severity === "severe");
  const others = allergies.filter((allergy) => allergy.severity !== "severe");

  if (severe.length === 0) {
    if (others.length === 0) return null;
    // no severe allergy — keep recorded allergies visible, without alarm
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border bg-surface-2 px-3.5 py-2.5">
        <div className="min-w-0 text-end">
          <p className="text-sm font-semibold">حساسیت‌های ثبت‌شده</p>
          <p className="truncate text-xs text-muted-foreground">
            {others
              .map(
                (allergy) =>
                  `${allergy.allergen} (${allergySeverityLabels[allergy.severity]})`
              )
              .join("، ")}
          </p>
        </div>
        <CircleAlertIcon className="size-[18px] shrink-0 text-muted-foreground" />
      </div>
    );
  }

  const subline = [
    severe[0].reaction ? `واکنش ثبت‌شده: ${severe[0].reaction}` : null,
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
    <div className="flex items-center justify-between gap-3 rounded-lg border border-critical-border bg-critical-soft px-3.5 py-2.5">
      <div className="min-w-0 text-end">
        <p className="text-sm font-semibold text-critical">
          آلرژی شدید: {severe[0].allergen}
        </p>
        {subline ? (
          <p className="truncate text-xs text-muted-foreground">{subline}</p>
        ) : null}
      </div>
      <TriangleAlertIcon className="size-[18px] shrink-0 text-critical" />
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
    <section className="space-y-1.5">
      <SectionHeader
        title="مشکلات فعال"
        count={active.length > 0 ? `${faNum(active.length)} مورد` : undefined}
        action={<AddConditionButton patientId={patientId} />}
      />
      {active.length === 0 ? (
        <EmptyState title="مشکل بالینی فعالی ثبت نشده است" />
      ) : (
        <ul>
          {active.map((condition) => (
            <li
              key={condition.id}
              className="flex items-center gap-3 border-b border-border/60 px-1.5 py-2 last:border-0 hover:bg-surface-2/60"
            >
              <p className="min-w-0 flex-1 truncate text-[13px] font-medium">
                {condition.name}
              </p>
              <span className="shrink-0 text-xs text-faint">
                {condition.onset_date ? `از ${formatDate(condition.onset_date)}` : ""}
              </span>
              <ConditionRowActions
                patientId={patientId}
                condition={condition}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 2b. Allergies (management preserved — summary is its only surface)  */
/* ------------------------------------------------------------------ */

function AllergyList({
  patientId,
  allergies,
}: {
  patientId: number;
  allergies: Allergy[];
}) {
  return (
    <section className="space-y-1.5">
      <SectionHeader
        title="حساسیت‌ها"
        count={
          allergies.length > 0 ? `${faNum(allergies.length)} مورد` : undefined
        }
        action={<AddAllergyButton patientId={patientId} />}
      />
      {allergies.length === 0 ? (
        <EmptyState title="حساسیتی ثبت نشده است" />
      ) : (
        <ul>
          {allergies.map((allergy) => (
            <li
              key={allergy.id}
              className="flex items-center gap-3 border-b border-border/60 px-1.5 py-2 last:border-0 hover:bg-surface-2/60"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium">
                  {allergy.allergen}
                </p>
                {allergy.reaction ? (
                  <p className="truncate text-xs text-faint">
                    واکنش: {allergy.reaction}
                  </p>
                ) : null}
              </div>
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
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 3. Active medications — dense table with LTR/mono technical values  */
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
    <section className="space-y-1.5">
      <SectionHeader
        title="داروهای فعال"
        count={`${faNum(active.length)} از ${faNum(medications.length)}`}
        action={<ViewAllLink patientId={patientId} tab="medications" />}
      />
      {active.length === 0 ? (
        <EmptyState
          title="داروی فعالی ثبت نشده است"
          description="در تب «داروها» می‌توانید داروی جدیدی اضافه کنید."
        />
      ) : (
        <>
          <div className={`${MED_GRID} px-1.5 text-[11px] text-faint`}>
            <span>نام دارو</span>
            <span>دوز</span>
            <span>شروع</span>
            <span>وضعیت</span>
          </div>
          <ul>
            {active.map((record) => (
              <li
                key={record.id}
                className={`${MED_GRID} border-b border-border/60 px-1.5 py-2 last:border-0 hover:bg-surface-2/60`}
              >
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium">
                    {record.medication.name}
                  </p>
                  {record.medication.generic_name ? (
                    <p
                      dir="ltr"
                      className="truncate text-right font-mono text-[10px] text-faint"
                    >
                      {record.medication.generic_name}
                    </p>
                  ) : null}
                </div>
                <span
                  dir="ltr"
                  className="truncate font-mono text-[13px] tabular-nums"
                >
                  {record.dosage ?? "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  {record.start_date ? formatDate(record.start_date) : "—"}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="size-1.5 shrink-0 rounded-full bg-success" />
                  {medicationStatusLabels[record.status]}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 4. Recent labs — semantic flags, tabular LTR values                */
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
    <section className="space-y-1.5">
      <SectionHeader
        title="آزمایش‌های اخیر"
        count={`${faNum(recent.length)} از ${faNum(labResults.length)}`}
        action={<ViewAllLink patientId={patientId} tab="labs" />}
      />
      {recent.length === 0 ? (
        <EmptyState title="نتیجهٔ آزمایشی ثبت نشده است" />
      ) : (
        <>
          <div className={`${LAB_GRID} px-1.5 text-[11px] text-faint`}>
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
                className={`${LAB_GRID} border-b border-border/60 px-1.5 py-2 last:border-0 hover:bg-surface-2/60`}
              >
                <span className="truncate text-[13px] font-medium">
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
                    className={`flex items-center gap-1.5 text-xs ${flagClass(lab.flag)}`}
                  >
                    <span className="size-1.5 shrink-0 rounded-full bg-current" />
                    {resultFlagLabels[lab.flag]}
                  </span>
                ) : (
                  <span className="text-xs text-faint">—</span>
                )}
                <span className="text-xs text-faint">
                  {lab.result_date ? formatDate(lab.result_date) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 5. Recent documents                                                */
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
    <section className="space-y-1.5">
      <SectionHeader
        title="اسناد و یادداشت‌های اخیر"
        count={`${faNum(recent.length)} از ${faNum(documents.length)}`}
        action={<ViewAllLink patientId={patientId} tab="documents" />}
      />
      {recent.length === 0 ? (
        <EmptyState
          title="سندی بارگذاری نشده است"
          description="گزارش آزمایش، تصویر یا فایل بالینی بیمار را در تب «اسناد و یادداشت‌ها» بارگذاری کنید."
        />
      ) : (
        <ul>
          {recent.map((document) => (
            <li
              key={document.id}
              className="flex items-center gap-3 border-b border-border/60 px-1.5 py-2 last:border-0 hover:bg-surface-2/60"
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-surface-2 text-muted-foreground">
                {documentIcon(document.doc_type)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium">
                  {document.title}
                </p>
                <p className="truncate text-xs text-faint">
                  {documentTypeLabels[document.doc_type]} ·{" "}
                  {formatDateTime(document.created_at)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
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
    <div className="space-y-4">
      <CriticalAlerts allergies={allergies} />
      <ActiveProblems patientId={patientId} conditions={conditions} />
      <AllergyList patientId={patientId} allergies={allergies} />
      <ActiveMedications
        patientId={patientId}
        medications={medications}
      />
      <RecentLabs patientId={patientId} labResults={labResults} />
      <RecentDocuments patientId={patientId} documents={documents} />
    </div>
  );
}
