/** Persian labels, enum display names, and date/age formatting helpers. */

import type {
  AllergySeverity,
  AnalysisStatus,
  ConditionStatus,
  ConversationType,
  DocumentType,
  ExtractionStatus,
  Gender,
  MedicationStatus,
  NoteSource,
  ResultFlag,
  TranscriptionStatus,
} from "@/lib/types";

export const genderLabels: Record<Gender, string> = {
  male: "مرد",
  female: "زن",
  other: "سایر",
  unknown: "نامشخص",
};

export const genderOptions = (Object.keys(genderLabels) as Gender[]).map(
  (value) => ({ value, label: genderLabels[value] })
);

export const conditionStatusLabels: Record<ConditionStatus, string> = {
  active: "فعال",
  resolved: "برطرف‌شده",
};

export const conditionStatusOptions = (
  Object.keys(conditionStatusLabels) as ConditionStatus[]
).map((value) => ({ value, label: conditionStatusLabels[value] }));

export const allergySeverityLabels: Record<AllergySeverity, string> = {
  mild: "خفیف",
  moderate: "متوسط",
  severe: "شدید",
  unknown: "نامشخص",
};

export const allergySeverityOptions = (
  Object.keys(allergySeverityLabels) as AllergySeverity[]
).map((value) => ({ value, label: allergySeverityLabels[value] }));

export const medicationStatusLabels: Record<MedicationStatus, string> = {
  active: "در حال مصرف",
  stopped: "قطع‌شده",
  completed: "تکمیل‌شده",
};

export const medicationStatusOptions = (
  Object.keys(medicationStatusLabels) as MedicationStatus[]
).map((value) => ({ value, label: medicationStatusLabels[value] }));

export const resultFlagLabels: Record<ResultFlag, string> = {
  normal: "طبیعی",
  abnormal: "خارج از محدوده",
  critical: "بحرانی",
};

export const noteSourceLabels: Record<NoteSource, string> = {
  manual: "دستی",
  voice: "صوتی",
  ai_assisted: "با کمک هوش مصنوعی",
};

export const documentTypeLabels: Record<DocumentType, string> = {
  lab_report: "آزمایش آزمایشگاه",
  imaging_report: "گزارش تصویربرداری",
  discharge_summary: "خلاصهٔ تخلیه",
  medical_note: "یادداشت بالینی",
  other: "سایر",
};

export const documentTypeOptions = (
  Object.keys(documentTypeLabels) as DocumentType[]
).map((value) => ({ value, label: documentTypeLabels[value] }));

export const extractionStatusLabels: Record<ExtractionStatus, string> = {
  pending: "در انتظار پردازش",
  processing: "در حال پردازش",
  completed: "متن استخراج شد",
  failed: "پردازش ناموفق",
};

export const conversationTypeLabels: Record<ConversationType, string> = {
  physician_note: "یادداشت صوتی پزشک",
  doctor_patient: "گفتگوی پزشک و بیمار",
};

export const conversationTypeOptions = (
  Object.keys(conversationTypeLabels) as ConversationType[]
).map((value) => ({
  value,
  label: conversationTypeLabels[value],
  description:
    value === "doctor_patient"
      ? "با تشخیص گوینده (دو نفره)"
      : "گفتار تک‌نفره — سریع‌تر",
}));

export const transcriptionStatusLabels: Record<TranscriptionStatus, string> = {
  pending: "در انتظار تبدیل به متن",
  processing: "در حال تبدیل به متن",
  completed: "تبدیل انجام شد",
  failed: "تبدیل ناموفق",
};

export const cleanupStatusLabels: Record<AnalysisStatus, string> = {
  pending: "بدون پاک‌سازی",
  completed: "پاک‌سازی شد",
  failed: "پاک‌سازی ناموفق",
};

/** Duration as m:ss (e.g. 1:23). */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

/** Human-readable file size, e.g. «۲۰۴٫۸ KB». */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} بایت`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const formatted = new Intl.NumberFormat("fa-IR", {
    maximumFractionDigits: 1,
  }).format(value);
  return `${formatted} ${units[unit]}`;
}

/** Persian (Jalali) calendar date, e.g. «۱۵ مرداد ۱۴۰۵». Empty → «—». */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(iso));
}

/** Persian (Jalali) date + time. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Age in completed years (null when no date of birth). */
export function calculateAge(dateOfBirth: string | null | undefined): number | null {
  if (!dateOfBirth) return null;
  const birth = new Date(dateOfBirth);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const monthDiff = now.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}

/** Today's date as yyyy-mm-dd (for date inputs / stop-medication payloads). */
export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

/** "" → null (for optional payload fields). */
export function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
