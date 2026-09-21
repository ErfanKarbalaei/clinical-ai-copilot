import { notFound, redirect } from "next/navigation";
import {
  ActivityIcon,
  DownloadIcon,
  FileTextIcon,
  FileUpIcon,
  FlaskConicalIcon,
  MicIcon,
  PillIcon,
} from "lucide-react";

import {
  AddDocumentButton,
  DocumentRowActions,
  ViewExtractedTextButton,
} from "@/components/patients/document-actions";
import {
  AddMedicationButton,
  MedicationRowActions,
} from "@/components/patients/medication-actions";
import {
  AddVoiceNoteButton,
  ViewCleanedNoteButton,
  ViewTranscriptButton,
  VoiceNoteRowActions,
} from "@/components/patients/voice-note-actions";
import { ClinicalChat } from "@/components/patients/clinical-chat";
import { PatientIdentityBar } from "@/components/patients/patient-identity-bar";
import {
  SectionCard,
} from "@/components/patients/summary/section-card";
import { SummaryView } from "@/components/patients/summary/summary-view";
import {
  WorkspaceTabs,
  parseWorkspaceTab,
} from "@/components/patients/workspace-tabs";
import { AppShell } from "@/components/shared/app-shell";
import { CompactEmptyState } from "@/components/shared/compact-empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ApiError, api } from "@/lib/api";
import {
  cleanupStatusLabels,
  conversationTypeLabels,
  documentTypeLabels,
  extractionStatusLabels,
  faNum,
  formatBytes,
  formatDate,
  formatDateTime,
  formatDuration,
  medicationStatusLabels,
  noteSourceLabels,
  resultFlagLabels,
  transcriptionStatusLabels,
} from "@/lib/format";
import type {
  ClinicalNote,
  Document,
  ExtractionStatus,
  PatientContext,
  PatientMedication,
  PatientTimeline,
  ResultFlag,
  TranscriptionStatus,
  VoiceNote,
} from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = { title: "پروندهٔ بالینی بیمار" };

const MED_GRID =
  "grid grid-cols-[minmax(0,1fr)_110px_100px_100px] items-center gap-2";
const LAB_GRID =
  "grid grid-cols-[minmax(0,1fr)_110px_120px_92px_88px] items-center gap-2";
const ROW_DIVIDE = "border-b border-border/50 last:border-0";

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

function extractionStatusBadgeClass(status: ExtractionStatus): string {
  switch (status) {
    case "completed":
      return "text-success";
    case "failed":
      return "text-critical";
    case "processing":
      return "animate-pulse";
    default:
      return "";
  }
}

function transcriptionStatusBadgeClass(status: TranscriptionStatus): string {
  switch (status) {
    case "completed":
      return "text-success";
    case "failed":
      return "text-critical";
    case "processing":
      return "animate-pulse";
    default:
      return "";
  }
}

function timelineIcon(eventType: string) {
  switch (eventType) {
    case "document_uploaded":
      return <FileUpIcon className="size-3.5" />;
    case "lab_result":
      return <FlaskConicalIcon className="size-3.5" />;
    case "voice_note_recorded":
      return <MicIcon className="size-3.5" />;
    case "note_created":
      return <FileTextIcon className="size-3.5" />;
    case "medication_started":
    case "medication_stopped":
      return <PillIcon className="size-3.5" />;
    default:
      return <ActivityIcon className="size-3.5" />;
  }
}

/* --- tab views (all existing functionality, visually unified) --- */

function TimelineView({ timeline }: { timeline: PatientTimeline }) {
  return (
    <SectionCard
      title="تایم‌لاین بالینی"
      count={timeline.total > 0 ? `${faNum(timeline.total)} رویداد` : undefined}
    >
      {timeline.items.length === 0 ? (
        <CompactEmptyState
          label="رویداد بالینی ثبت نشده است"
          hint="با ثبت دارو، سند یا یادداشت، رویدادها به‌صورت خودکار اضافه می‌شوند"
        />
      ) : (
        <ol className="border-s ps-6">
          {timeline.items.map((item, index) => (
            <li
              key={`${item.source_type}-${item.source_id}-${item.event_type}-${index}`}
              className="relative pb-4 last:pb-0"
            >
              <span className="absolute -start-[31px] top-0 flex size-[22px] items-center justify-center rounded-full bg-surface-2 text-muted-foreground">
                {timelineIcon(item.event_type)}
              </span>
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <p className="text-[13px] leading-5 font-medium">{item.title}</p>
                <span className="text-[11px] text-faint">
                  {formatDateTime(item.date)}
                </span>
              </div>
              {item.description ? (
                <p className="mt-0.5 text-[11px] leading-4 text-muted-foreground">
                  {item.description}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}

function MedicationsView({
  patientId,
  medications,
}: {
  patientId: number;
  medications: PatientMedication[];
}) {
  // active first, then the historical records
  const sorted = [...medications].sort(
    (a, b) =>
      (a.status === "active" ? 0 : 1) - (b.status === "active" ? 0 : 1)
  );
  return (
    <SectionCard
      title="داروها"
      count={
        medications.length > 0 ? `${faNum(medications.length)} رکورد` : undefined
      }
      action={<AddMedicationButton patientId={patientId} />}
    >
      {sorted.length === 0 ? (
        <CompactEmptyState
          label="دارویی ثبت نشده است"
          hint="با دکمهٔ + داروی جدیدی اضافه کنید"
        />
      ) : (
        <>
          <div className={`${MED_GRID} pb-1 text-[11px] text-faint`}>
            <span>نام دارو</span>
            <span>دوز</span>
            <span>شروع</span>
            <span>وضعیت</span>
          </div>
          <ul>
            {sorted.map((record) => (
              <li
                key={record.id}
                className={`${MED_GRID} py-1.5 ${ROW_DIVIDE}`}
              >
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div className="min-w-0">
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
                  <MedicationRowActions patientId={patientId} record={record} />
                </div>
                <span
                  dir="ltr"
                  className="truncate font-mono text-xs tabular-nums"
                >
                  {record.dosage ?? "—"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {record.start_date ? formatDate(record.start_date) : "—"}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <span
                    className={`size-1.5 shrink-0 rounded-full ${
                      record.status === "active" ? "bg-success" : "bg-faint"
                    }`}
                  />
                  {medicationStatusLabels[record.status]}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionCard>
  );
}

function LabsView({
  labResults,
}: {
  labResults: PatientContext["lab_results"];
}) {
  return (
    <SectionCard
      title="آزمایش‌ها"
      count={
        labResults.length > 0 ? `${faNum(labResults.length)} نتیجه` : undefined
      }
    >
      {labResults.length === 0 ? (
        <CompactEmptyState
          label="نتیجهٔ آزمایشی ثبت نشده است"
          hint="نتایج از اسناد بارگذاری‌شده استخراج می‌شوند"
        />
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
            {labResults.map((lab) => (
              <li key={lab.id} className={`${LAB_GRID} py-1.5 ${ROW_DIVIDE}`}>
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

function DocumentsView({
  patientId,
  documents,
  voiceNotes,
  clinicalNotes,
}: {
  patientId: number;
  documents: Document[];
  voiceNotes: VoiceNote[];
  clinicalNotes: ClinicalNote[];
}) {
  return (
    <div className="space-y-3">
      {/* --- documents --- */}
      <SectionCard
        title="اسناد"
        count={
          documents.length > 0 ? `${faNum(documents.length)} سند` : undefined
        }
        action={<AddDocumentButton patientId={patientId} />}
      >
        {documents.length === 0 ? (
          <CompactEmptyState
            label="سندی بارگذاری نشده است"
            hint="گزارش آزمایش، تصویر یا فایل بالینی بیمار را بارگذاری کنید"
          />
        ) : (
          <ul>
            {documents.map((document) => (
              <li
                key={document.id}
                className={`flex items-start justify-between gap-2 py-2 ${ROW_DIVIDE}`}
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="truncate text-[13px] leading-5 font-medium">
                    {document.title}
                  </p>
                  <p className="text-[11px] leading-4 text-faint" dir="ltr">
                    {document.file_name} —{" "}
                    {formatBytes(document.file_size_bytes)}
                  </p>
                  <p className="text-[11px] leading-4 text-faint">
                    {documentTypeLabels[document.doc_type]} ·{" "}
                    {formatDate(document.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className={extractionStatusBadgeClass(
                      document.extraction_status
                    )}
                  >
                    {extractionStatusLabels[document.extraction_status]}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="دانلود فایل اصلی"
                    title="دانلود فایل اصلی"
                    render={
                      <a
                        href={api.documentDownloadUrl(document.id)}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                  >
                    <DownloadIcon />
                  </Button>
                  <ViewExtractedTextButton document={document} />
                  <DocumentRowActions document={document} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      {/* --- voice notes (Persian speech-to-text) --- */}
      <SectionCard
        title="یادداشت‌های صوتی"
        count={
          voiceNotes.length > 0 ? `${faNum(voiceNotes.length)} مورد` : undefined
        }
        action={<AddVoiceNoteButton patientId={patientId} />}
      >
        {voiceNotes.length === 0 ? (
          <CompactEmptyState
            label="یادداشت صوتی ثبت نشده است"
            hint="گفتار خود را ضبط یا فایل صوتی بارگذاری کنید"
          />
        ) : (
          <ul>
            {voiceNotes.map((voiceNote) => (
              <li
                key={voiceNote.id}
                className={`flex items-start justify-between gap-2 py-2 ${ROW_DIVIDE}`}
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="truncate text-[13px] leading-5 font-medium">
                    {voiceNote.title ?? "بدون عنوان"}
                  </p>
                  <p className="text-[11px] leading-4 text-faint">
                    {conversationTypeLabels[voiceNote.conversation_type]} ·{" "}
                    {formatDuration(voiceNote.duration_seconds)} ·{" "}
                    {formatDate(voiceNote.created_at)}
                  </p>
                  {voiceNote.transcript ? (
                    <p className="line-clamp-1 text-[11px] leading-4 text-muted-foreground">
                      {voiceNote.transcript.split("\n")[0]}
                    </p>
                  ) : null}
                  {voiceNote.transcription_status === "failed" &&
                  voiceNote.error_message ? (
                    <p className="line-clamp-1 text-[11px] leading-4 text-critical">
                      {voiceNote.error_message}
                    </p>
                  ) : null}
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className={transcriptionStatusBadgeClass(
                      voiceNote.transcription_status
                    )}
                  >
                    {transcriptionStatusLabels[voiceNote.transcription_status]}
                  </Badge>
                  {voiceNote.cleanup_status === "completed" ? (
                    <Badge variant="outline" className="text-brand">
                      {cleanupStatusLabels[voiceNote.cleanup_status]}
                    </Badge>
                  ) : null}
                  <ViewCleanedNoteButton voiceNote={voiceNote} />
                  <ViewTranscriptButton voiceNote={voiceNote} />
                  <VoiceNoteRowActions voiceNote={voiceNote} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      {/* --- clinical notes --- */}
      <SectionCard
        title="یادداشت‌های بالینی"
        count={
          clinicalNotes.length > 0
            ? `${faNum(clinicalNotes.length)} یادداشت`
            : undefined
        }
      >
        {clinicalNotes.length === 0 ? (
          <CompactEmptyState label="یادداشتی ثبت نشده است" />
        ) : (
          <div className="space-y-3">
            {clinicalNotes.map((note) => (
              <div key={note.id} className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[13px] leading-5 font-medium">
                    {note.title}
                  </p>
                  <Badge variant="outline">
                    {noteSourceLabels[note.source]}
                  </Badge>
                  <span className="text-[11px] text-faint">
                    {formatDate(note.created_at)}
                  </span>
                </div>
                <p className="text-[13px] leading-6 text-muted-foreground">
                  {note.content}
                </p>
                <Separator className="last:hidden" />
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

/* -------------------------------------------------------------------- */

interface PatientDetailPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

export default async function PatientDetailPage({
  params,
  searchParams,
}: PatientDetailPageProps) {
  const [{ id }, { tab: tabParam }] = await Promise.all([params, searchParams]);
  const patientId = Number(id);
  if (!Number.isInteger(patientId) || patientId <= 0) notFound();
  const tab = parseWorkspaceTab(tabParam);

  let context: Awaited<ReturnType<typeof api.getPatientContext>>;
  let timeline: Awaited<ReturnType<typeof api.getPatientTimeline>>;
  try {
    [context, timeline] = await Promise.all([
      api.getPatientContext(patientId),
      api.getPatientTimeline(patientId),
    ]);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 401) redirect("/login");
    if (cause instanceof ApiError && cause.status === 404) notFound();
    return (
      <div className="flex min-h-svh flex-1 flex-col">
        <AppShell />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
          <ErrorState
            message={cause instanceof ApiError ? cause.message : "خطای ناشناخته"}
          />
        </main>
      </div>
    );
  }

  const {
    patient,
    conditions,
    allergies,
    medications,
    lab_results: labResults,
    documents,
    voice_notes: voiceNotes,
    clinical_notes: clinicalNotes,
  } = context;

  return (
    <div className="flex min-h-svh flex-1 flex-col">
      <AppShell />
      <PatientIdentityBar
        patient={patient}
        allergies={allergies}
        activeConditionCount={
          conditions.filter((condition) => condition.status === "active").length
        }
      />

      {/* clinical workspace: record (right — source of truth) + copilot
          (left — interpretation). In RTL the first grid column is on the
          right, so the record column comes first in the DOM. */}
      <div className="grid flex-1 grid-cols-1 items-start xl:grid-cols-[minmax(0,1fr)_min(36%,520px)]">
        <div className="min-w-0">
          <WorkspaceTabs
            patientId={patient.id}
            active={tab}
            updatedAt={patient.updated_at}
          />
          <div className="px-4 py-3.5 lg:px-5">
            {tab === "summary" ? (
              <SummaryView
                patientId={patient.id}
                conditions={conditions}
                allergies={allergies}
                medications={medications}
                labResults={labResults}
                documents={documents}
              />
            ) : tab === "timeline" ? (
              <TimelineView timeline={timeline} />
            ) : tab === "medications" ? (
              <MedicationsView
                patientId={patient.id}
                medications={medications}
              />
            ) : tab === "labs" ? (
              <LabsView labResults={labResults} />
            ) : (
              <DocumentsView
                patientId={patient.id}
                documents={documents}
                voiceNotes={voiceNotes}
                clinicalNotes={clinicalNotes}
              />
            )}
          </div>
        </div>

        {/* AI copilot — full-height supporting panel on the left */}
        <aside className="order-first min-w-0 xl:order-none">
          <ClinicalChat
            patientId={patient.id}
            patientName={`${patient.first_name} ${patient.last_name}`}
          />
        </aside>
      </div>
    </div>
  );
}
