"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import {
  LoaderIcon,
  PencilIcon,
  PlusIcon,
  ShieldAlertIcon,
  SquareIcon,
  Trash2Icon,
} from "lucide-react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { medicationStatusOptions, todayIsoDate } from "@/lib/format";
import type {
  AiMedicationSafetyResult,
  MedicationStatus,
  PatientMedication,
} from "@/lib/types";

const FORM_ID = "medication-form";

function SafetySection({
  title,
  items,
  className,
}: {
  title: string;
  items: string[];
  className?: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className={`space-y-1 ${className ?? ""}`}>
      <p className="text-xs font-medium">{title}</p>
      <ul className="list-inside list-disc space-y-0.5 text-xs leading-5">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function MedicationFormDialog({
  patientId,
  record,
  open,
  onOpenChange,
}: {
  patientId: number;
  record?: PatientMedication;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [medicationName, setMedicationName] = useState("");
  const [dosage, setDosage] = useState("");
  const [frequency, setFrequency] = useState("");
  const [status, setStatus] = useState<MedicationStatus>("active");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [safetyResult, setSafetyResult] = useState<AiMedicationSafetyResult | null>(
    null
  );
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [safetyError, setSafetyError] = useState<string | null>(null);

  const isEdit = record !== undefined;

  useEffect(() => {
    if (!open) return;
    setMedicationName(record?.medication.name ?? "");
    setDosage(record?.dosage ?? "");
    setFrequency(record?.frequency ?? "");
    setStatus(record?.status ?? "active");
    setStartDate(record?.start_date ?? "");
    setEndDate(record?.end_date ?? "");
    setNotes(record?.notes ?? "");
    setError(null);
    setSubmitting(false);
    setSafetyResult(null);
    setSafetyError(null);
    setSafetyLoading(false);
  }, [open, record]);

  // AI decision support — never blocks the save flow (physician decides).
  async function runSafetyCheck() {
    const name = medicationName.trim();
    if (!name || safetyLoading) return;
    setSafetyLoading(true);
    setSafetyError(null);
    setSafetyResult(null);
    try {
      const result = await api.aiMedicationSafetyCheck(patientId, {
        medications: [{ name, dose: dosage.trim() === "" ? null : dosage.trim() }],
      });
      setSafetyResult(result);
    } catch (cause) {
      setSafetyError(
        cause instanceof ApiError
          ? cause.message
          : "تحلیل ایمنی دارو انجام نشد."
      );
    } finally {
      setSafetyLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (isEdit) {
        await api.updatePatientMedication(record.id, {
          dosage: dosage.trim() === "" ? null : dosage.trim(),
          frequency: frequency.trim() === "" ? null : frequency.trim(),
          status,
          start_date: startDate === "" ? null : startDate,
          end_date: endDate === "" ? null : endDate,
          notes: notes.trim() === "" ? null : notes.trim(),
        });
      } else {
        await api.createPatientMedication(patientId, {
          medication_name: medicationName.trim(),
          dosage: dosage.trim() === "" ? null : dosage.trim(),
          frequency: frequency.trim() === "" ? null : frequency.trim(),
          start_date: startDate === "" ? null : startDate,
          notes: notes.trim() === "" ? null : notes.trim(),
        });
      }
      onOpenChange(false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "ثبت با خطا مواجه شد."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "ویرایش داروی بیمار" : "افزودن دارو برای بیمار"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? `دارو: ${record?.medication.name} — دوز، تناوب و وضعیت را ویرایش کنید.`
              : "نام دارو را وارد کنید؛ اگر قبلاً ثبت شده باشد از همان استفاده می‌شود."}
          </DialogDescription>
        </DialogHeader>

        <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="medication_name">نام دارو *</Label>
            {isEdit ? (
              <Input id="medication_name" value={medicationName} disabled />
            ) : (
              <Input
                id="medication_name"
                value={medicationName}
                onChange={(event) => setMedicationName(event.target.value)}
                required
                maxLength={200}
                placeholder="مثال: Metformin 500"
              />
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="dosage">دوز</Label>
              <Input
                id="dosage"
                value={dosage}
                onChange={(event) => setDosage(event.target.value)}
                maxLength={100}
                placeholder="مثال: 500 mg"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="frequency">تناوب مصرف</Label>
              <Input
                id="frequency"
                value={frequency}
                onChange={(event) => setFrequency(event.target.value)}
                maxLength={100}
                placeholder="مثال: دو بار در روز"
              />
            </div>
            {isEdit ? (
              <div className="space-y-2">
                <Label>وضعیت</Label>
                <Select
                  items={medicationStatusOptions}
                  value={status}
                  onValueChange={(value) =>
                    setStatus(value as MedicationStatus)
                  }
                >
                  <SelectTrigger className="w-full" aria-label="وضعیت">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {medicationStatusOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="start_date">تاریخ شروع (میلادی)</Label>
              <Input
                id="start_date"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                dir="ltr"
              />
            </div>
            {isEdit ? (
              <div className="space-y-2">
                <Label htmlFor="end_date">تاریخ پایان (میلادی)</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  dir="ltr"
                />
              </div>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="medication_notes">توضیحات / دستور مصرف</Label>
            <Textarea
              id="medication_notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={2}
            />
          </div>

          {!isEdit ? (
            <div className="space-y-2 rounded-lg border p-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={runSafetyCheck}
                disabled={medicationName.trim() === "" || safetyLoading}
              >
                {safetyLoading ? (
                  <LoaderIcon className="animate-spin" />
                ) : (
                  <ShieldAlertIcon />
                )}
                {safetyLoading ? "در حال بررسی…" : "بررسی ایمنی دارو"}
              </Button>
              <p className="text-xs text-muted-foreground">
                تحلیل هوش مصنوعیِ تداخل با داروها، آلرژی‌ها و شرایط فعلی بیمار —
                اختیاری و بدون مانع شدن برای ذخیره.
              </p>

              {safetyError ? (
                <p className="text-sm text-destructive">{safetyError}</p>
              ) : null}

              {safetyResult ? (
                <div className="ai-content space-y-3 rounded-lg p-3">
                  <div className="flex items-start gap-1.5">
                    <ShieldAlertIcon className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <div className="space-y-3">
                      <p className="text-[10px] font-medium text-muted-foreground">
                        تحلیل هوش مصنوعی — کمک به تصمیم، نه حکم نهایی
                      </p>
                      <p className="text-sm font-medium leading-6">
                        {safetyResult.overall_assessment}
                      </p>
                      <SafetySection
                        title="تداخل‌ها"
                        items={safetyResult.interactions}
                        className="text-amber-700 dark:text-amber-400"
                      />
                      <SafetySection
                        title="نکات خاص این بیمار"
                        items={safetyResult.patient_factors}
                      />
                      <SafetySection
                        title="اطلاعات ناقص"
                        items={safetyResult.missing_information}
                      />
                      {safetyResult.uncertainty ? (
                        <p className="text-xs italic leading-5 text-muted-foreground">
                          عدم‌قطعیت: {safetyResult.uncertainty}
                        </p>
                      ) : null}
                      <p className="text-[11px] leading-5 text-muted-foreground">
                        {safetyResult.disclaimer}
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            انصراف
          </Button>
          <Button type="submit" form={FORM_ID} disabled={submitting}>
            {submitting ? "در حال ذخیره…" : "ذخیره"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** «+» button in the medications card header. */
export function AddMedicationButton({ patientId }: { patientId: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="افزودن دارو"
        onClick={() => setOpen(true)}
      >
        <PlusIcon />
      </Button>
      <MedicationFormDialog patientId={patientId} open={open} onOpenChange={setOpen} />
    </>
  );
}

/** Per-row actions: quick stop (for active), edit, delete. */
export function MedicationRowActions({
  patientId,
  record,
}: {
  patientId: number;
  record: PatientMedication;
}) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [stopOpen, setStopOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="flex items-center gap-1">
      {record.status === "active" ? (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="قطع دارو"
          title="قطع دارو (حذف نمی‌شود)"
          onClick={() => setStopOpen(true)}
        >
          <SquareIcon />
        </Button>
      ) : null}
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="ویرایش"
        onClick={() => setEditOpen(true)}
      >
        <PencilIcon />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="حذف"
        onClick={() => setDeleteOpen(true)}
        className="text-destructive hover:text-destructive"
      >
        <Trash2Icon />
      </Button>

      <MedicationFormDialog
        patientId={patientId}
        record={record}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <ConfirmDialog
        open={stopOpen}
        onOpenChange={setStopOpen}
        title="قطع دارو"
        description={`«${record.medication.name}» به وضعیت قطع‌شده می‌رود؛ سابقهٔ آن در پرونده باقی می‌ماند.`}
        confirmLabel="قطع دارو"
        onConfirm={async () => {
          await api.updatePatientMedication(record.id, {
            status: "stopped",
            end_date: todayIsoDate(),
          });
          router.refresh();
        }}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف رکورد دارو"
        description={`رکورد «${record.medication.name}» به‌طور کامل از پرونده حذف می‌شود. اگر قصد فقط قطع دارو را دارید، از دکمهٔ قطع استفاده کنید.`}
        confirmLabel="حذف قطعی"
        onConfirm={async () => {
          await api.deletePatientMedication(record.id);
          router.refresh();
        }}
      />
    </div>
  );
}
