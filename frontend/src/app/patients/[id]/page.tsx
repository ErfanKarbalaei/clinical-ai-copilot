import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import {
  ActivityIcon,
  AlertCircleIcon,
  ArrowRightIcon,
  DownloadIcon,
  FileTextIcon,
  FileUpIcon,
  FlaskConicalIcon,
  HistoryIcon,
  MicIcon,
  PhoneIcon,
  PillIcon,
} from "lucide-react";

import {
  AddAllergyButton,
  AllergyRowActions,
} from "@/components/patients/allergy-actions";
import {
  AddConditionButton,
  ConditionRowActions,
} from "@/components/patients/condition-actions";
import {
  AddDocumentButton,
  DocumentRowActions,
  ViewExtractedTextButton,
} from "@/components/patients/document-actions";
import { ClinicalChat } from "@/components/patients/clinical-chat";
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
import {
  DeletePatientButton,
  EditPatientButton,
} from "@/components/patients/patient-actions";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ApiError, api } from "@/lib/api";
import {
  allergySeverityLabels,
  calculateAge,
  cleanupStatusLabels,
  conditionStatusLabels,
  conversationTypeLabels,
  documentTypeLabels,
  extractionStatusLabels,
  formatBytes,
  formatDate,
  formatDateTime,
  formatDuration,
  genderLabels,
  medicationStatusLabels,
  noteSourceLabels,
  resultFlagLabels,
  transcriptionStatusLabels,
} from "@/lib/format";
import type {
  AllergySeverity,
  ExtractionStatus,
  ResultFlag,
  TranscriptionStatus,
} from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = { title: "پروندهٔ بالینی بیمار" };

function severityBadgeClass(severity: AllergySeverity): string {
  switch (severity) {
    case "severe":
      return "text-destructive";
    case "moderate":
      return "text-amber-600 dark:text-amber-400";
    default:
      return "text-muted-foreground";
  }
}

function flagBadgeVariant(flag: ResultFlag): string {
  switch (flag) {
    case "critical":
      return "text-destructive";
    case "abnormal":
      return "text-amber-600 dark:text-amber-400";
    default:
      return "text-emerald-600 dark:text-emerald-400";
  }
}

function extractionStatusBadgeClass(status: ExtractionStatus): string {
  switch (status) {
    case "completed":
      return "text-emerald-600 dark:text-emerald-400";
    case "failed":
      return "text-destructive";
    case "processing":
      return "animate-pulse";
    default:
      return "";
  }
}

function transcriptionStatusBadgeClass(status: TranscriptionStatus): string {
  switch (status) {
    case "completed":
      return "text-emerald-600 dark:text-emerald-400";
    case "failed":
      return "text-destructive";
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

interface PatientDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function PatientDetailPage({
  params,
}: PatientDetailPageProps) {
  const { id } = await params;
  const patientId = Number(id);
  if (!Number.isInteger(patientId) || patientId <= 0) notFound();

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
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <ErrorState
          message={cause instanceof ApiError ? cause.message : "خطای ناشناخته"}
        />
      </main>
    );
  }

  const { patient, conditions, allergies, documents, voice_notes: voiceNotes } =
    context;
  // the context carries the full medication history; the card shows active ones
  const active_medications = context.medications.filter(
    (record) => record.status === "active"
  );
  const recent_lab_results = context.lab_results.slice(0, 5);
  const recent_clinical_notes = context.clinical_notes.slice(0, 5);
  const age = calculateAge(patient.date_of_birth);

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-8">
      <Button variant="ghost" size="sm" render={<Link href="/patients" />}>
        <ArrowRightIcon />
        بازگشت به فهرست بیماران
      </Button>

      {/* --- profile --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">
            {patient.first_name} {patient.last_name}
          </CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{genderLabels[patient.gender]}</Badge>
            {age !== null ? <Badge variant="secondary">{age} ساله</Badge> : null}
            {patient.national_code ? (
              <Badge variant="outline">
                <span dir="ltr" className="font-mono">
                  {patient.national_code}
                </span>
              </Badge>
            ) : null}
          </CardDescription>
          <CardAction>
            <div className="flex items-center gap-2">
              <EditPatientButton patient={patient} />
              <DeletePatientButton patient={patient} />
            </div>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-muted-foreground">
          <span>
            تاریخ تولد: {formatDate(patient.date_of_birth)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <PhoneIcon className="size-4" />
            {patient.phone ? (
              <span dir="ltr" className="font-mono">
                {patient.phone}
              </span>
            ) : (
              "—"
            )}
          </span>
          {patient.address ? <span>نشانی: {patient.address}</span> : null}
        </CardContent>
      </Card>

      {/* --- unified clinical timeline --- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <HistoryIcon className="size-4 text-muted-foreground" />
            تایم‌لاین بالینی
          </CardTitle>
          <CardDescription>
            {timeline.total > 0
              ? `${timeline.total} رویداد — جدیدترین اول`
              : "رویدادی ثبت نشده است"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {timeline.items.length === 0 ? (
            <EmptyState
              title="رویداد بالینی ثبت نشده است"
              description="با ثبت دارو، سند، یادداشت یا آزمایش، رویدادها به‌صورت خودکار به تایم‌لاین اضافه می‌شوند."
            />
          ) : (
            <ol className="border-s ps-7">
              {timeline.items.map((item, index) => (
                <li
                  key={`${item.source_type}-${item.source_id}-${item.event_type}-${index}`}
                  className="relative pb-5 last:pb-0"
                >
                  <span className="absolute -start-[35px] top-0 flex size-[22px] items-center justify-center rounded-full bg-muted text-muted-foreground">
                    {timelineIcon(item.event_type)}
                  </span>
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                    <p className="font-medium">{item.title}</p>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(item.date)}
                    </span>
                  </div>
                  {item.description ? (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {item.description}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* --- conditions --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ActivityIcon className="size-4 text-muted-foreground" />
              مشکلات بالینی
            </CardTitle>
            <CardDescription>
              {conditions.length > 0
                ? `${conditions.length} مورد — فعال‌ها در ابتدا`
                : "موردی ثبت نشده است"}
            </CardDescription>
            <CardAction>
              <AddConditionButton patientId={patient.id} />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-1">
            {conditions.length === 0 ? (
              <EmptyState title="مشکل بالینی ثبت نشده است" />
            ) : (
              conditions.map((condition) => (
                <div
                  key={condition.id}
                  className="flex items-start justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-muted/50"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate font-medium">{condition.name}</p>
                    <p className="text-xs text-muted-foreground">
                      شروع: {formatDate(condition.onset_date)}
                      {condition.status === "resolved"
                        ? ` — رفع: ${formatDate(condition.resolved_date)}`
                        : ""}
                    </p>
                    {condition.notes ? (
                      <p className="text-xs text-muted-foreground">
                        {condition.notes}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge
                      variant={condition.status === "active" ? "secondary" : "outline"}
                    >
                      {conditionStatusLabels[condition.status]}
                    </Badge>
                    <ConditionRowActions patientId={patient.id} condition={condition} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- allergies --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircleIcon className="size-4 text-muted-foreground" />
              حساسیت‌ها
            </CardTitle>
            <CardDescription>
              {allergies.length > 0
                ? `${allergies.length} مورد — شدیدترها در ابتدا`
                : "موردی ثبت نشده است"}
            </CardDescription>
            <CardAction>
              <AddAllergyButton patientId={patient.id} />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-1">
            {allergies.length === 0 ? (
              <EmptyState title="حساسیتی ثبت نشده است" />
            ) : (
              allergies.map((allergy) => (
                <div
                  key={allergy.id}
                  className="flex items-start justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-muted/50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{allergy.allergen}</p>
                    {allergy.reaction ? (
                      <p className="text-xs text-muted-foreground">
                        واکنش: {allergy.reaction}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge
                      variant="outline"
                      className={severityBadgeClass(allergy.severity)}
                    >
                      {allergySeverityLabels[allergy.severity]}
                    </Badge>
                    <AllergyRowActions patientId={patient.id} allergy={allergy} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- active medications --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <PillIcon className="size-4 text-muted-foreground" />
              داروهای فعال
            </CardTitle>
            <CardDescription>
              {active_medications.length > 0
                ? `${active_medications.length} داروی در حال مصرف`
                : "داروی فعالی ثبت نشده است"}
            </CardDescription>
            <CardAction>
              <AddMedicationButton patientId={patient.id} />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-1">
            {active_medications.length === 0 ? (
              <EmptyState
                title="داروی فعالی ثبت نشده است"
                description="با دکمهٔ + داروی جدیدی اضافه کنید."
              />
            ) : (
              active_medications.map((record) => (
                <div
                  key={record.id}
                  className="flex items-start justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-muted/50"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate font-medium">
                      {record.medication.name}
                      {record.medication.generic_name ? (
                        <span className="text-xs font-normal text-muted-foreground">
                          {" "}
                          ({record.medication.generic_name})
                        </span>
                      ) : null}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {record.dosage ?? ""}
                      {record.dosage && record.frequency ? " — " : ""}
                      {record.frequency ?? ""}
                      {record.start_date ? ` — از ${formatDate(record.start_date)}` : ""}
                    </p>
                    {record.notes ? (
                      <p className="text-xs text-muted-foreground">{record.notes}</p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="secondary">
                      {medicationStatusLabels[record.status]}
                    </Badge>
                    <MedicationRowActions patientId={patient.id} record={record} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- documents --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileUpIcon className="size-4 text-muted-foreground" />
              اسناد
            </CardTitle>
            <CardDescription>
              {documents.length > 0
                ? `${documents.length} سند — جدیدترین اول`
                : "سندی بارگذاری نشده است"}
            </CardDescription>
            <CardAction>
              <AddDocumentButton patientId={patient.id} />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-1">
            {documents.length === 0 ? (
              <EmptyState
                title="سندی بارگذاری نشده است"
                description="گزارش آزمایش، تصویر یا فایل بالینی بیمار را بارگذاری کنید."
              />
            ) : (
              documents.map((document) => (
                <div
                  key={document.id}
                  className="flex items-start justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-muted/50"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate font-medium">{document.title}</p>
                    <p className="text-xs text-muted-foreground" dir="ltr">
                      {document.file_name} — {formatBytes(document.file_size_bytes)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {documentTypeLabels[document.doc_type]} —{" "}
                      {formatDateTime(document.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
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
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- voice notes (Persian speech-to-text) --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MicIcon className="size-4 text-muted-foreground" />
              یادداشت‌های صوتی
            </CardTitle>
            <CardDescription>
              {voiceNotes.length > 0
                ? `${voiceNotes.length} مورد — گفتار فارسی، متن خام حفظ می‌شود`
                : "موردی ثبت نشده است"}
            </CardDescription>
            <CardAction>
              <AddVoiceNoteButton patientId={patient.id} />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-1">
            {voiceNotes.length === 0 ? (
              <EmptyState
                title="یادداشت صوتی ثبت نشده است"
                description="با دکمهٔ میکروفون، گفتار خود را ضبط یا فایل صوتی بارگذاری کنید."
              />
            ) : (
              voiceNotes.map((voiceNote) => (
                <div
                  key={voiceNote.id}
                  className="flex items-start justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-muted/50"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate font-medium">
                      {voiceNote.title ?? "بدون عنوان"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {conversationTypeLabels[voiceNote.conversation_type]} —{" "}
                      {formatDuration(voiceNote.duration_seconds)} —{" "}
                      {formatDateTime(voiceNote.created_at)}
                    </p>
                    {voiceNote.transcript ? (
                      <p className="line-clamp-1 text-xs text-muted-foreground">
                        {voiceNote.transcript.split("\n")[0]}
                      </p>
                    ) : null}
                    {voiceNote.transcription_status === "failed" &&
                    voiceNote.error_message ? (
                      <p className="line-clamp-1 text-xs text-destructive">
                        {voiceNote.error_message}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge
                      variant="outline"
                      className={transcriptionStatusBadgeClass(
                        voiceNote.transcription_status
                      )}
                    >
                      {transcriptionStatusLabels[voiceNote.transcription_status]}
                    </Badge>
                    {voiceNote.cleanup_status === "completed" ? (
                      <Badge
                        variant="outline"
                        className="text-sky-600 dark:text-sky-400"
                      >
                        {cleanupStatusLabels[voiceNote.cleanup_status]}
                      </Badge>
                    ) : null}
                    <ViewCleanedNoteButton voiceNote={voiceNote} />
                    <ViewTranscriptButton voiceNote={voiceNote} />
                    <VoiceNoteRowActions voiceNote={voiceNote} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- recent labs --- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FlaskConicalIcon className="size-4 text-muted-foreground" />
              نتایج آزمایش اخیر
            </CardTitle>
            <CardDescription>۵ نتیجهٔ آخر</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {recent_lab_results.length === 0 ? (
              <EmptyState title="نتیجهٔ آزمایشی ثبت نشده است" />
            ) : (
              recent_lab_results.map((lab) => (
                <div
                  key={lab.id}
                  className="flex items-center justify-between gap-2 rounded-lg px-2 py-2 hover:bg-muted/50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {lab.test_name}:
                      <span className="font-mono" dir="ltr">
                        {" "}
                        {lab.value}
                      </span>
                      {lab.unit ? (
                        <span className="text-xs text-muted-foreground">
                          {" "}
                          {lab.unit}
                        </span>
                      ) : null}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(lab.result_date)}
                      {lab.reference_range
                        ? ` — محدودهٔ طبیعی: ${lab.reference_range}`
                        : ""}
                    </p>
                  </div>
                  {lab.flag ? (
                    <Badge variant="outline" className={flagBadgeVariant(lab.flag)}>
                      {resultFlagLabels[lab.flag]}
                    </Badge>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* --- recent notes --- */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileTextIcon className="size-4 text-muted-foreground" />
              یادداشت‌های بالینی اخیر
            </CardTitle>
            <CardDescription>۵ یادداشت آخر</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {recent_clinical_notes.length === 0 ? (
              <EmptyState title="یادداشتی ثبت نشده است" />
            ) : (
              recent_clinical_notes.map((note) => (
                <div key={note.id} className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{note.title}</p>
                    <Badge variant="outline">{noteSourceLabels[note.source]}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(note.created_at)}
                    </span>
                  </div>
                  <p className="text-sm leading-7 text-muted-foreground">
                    {note.content}
                  </p>
                  <Separator />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* --- clinical AI assistant (decision support, grounded in context) --- */}
      <ClinicalChat patientId={patient.id} />
    </main>
  );
}
