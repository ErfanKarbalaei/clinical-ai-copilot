/** Persian labels, enum display names, and date/age formatting helpers. */

import type {
  AllergySeverity,
  ConditionStatus,
  Gender,
  MedicationStatus,
  NoteSource,
  ResultFlag,
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
