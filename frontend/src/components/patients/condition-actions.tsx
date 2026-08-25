"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";

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
import { conditionStatusOptions } from "@/lib/format";
import type { Condition, ConditionStatus } from "@/lib/types";

const FORM_ID = "condition-form";

function ConditionFormDialog({
  patientId,
  condition,
  open,
  onOpenChange,
}: {
  patientId: number;
  condition?: Condition;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [status, setStatus] = useState<ConditionStatus>("active");
  const [onsetDate, setOnsetDate] = useState("");
  const [resolvedDate, setResolvedDate] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = condition !== undefined;

  useEffect(() => {
    if (!open) return;
    setName(condition?.name ?? "");
    setStatus(condition?.status ?? "active");
    setOnsetDate(condition?.onset_date ?? "");
    setResolvedDate(condition?.resolved_date ?? "");
    setNotes(condition?.notes ?? "");
    setError(null);
    setSubmitting(false);
  }, [open, condition]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload = {
      name: name.trim(),
      status,
      onset_date: onsetDate === "" ? null : onsetDate,
      resolved_date: resolvedDate === "" ? null : resolvedDate,
      notes: notes.trim() === "" ? null : notes.trim(),
    };
    try {
      if (isEdit) {
        await api.updateCondition(condition.id, payload);
      } else {
        await api.createCondition(patientId, payload);
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
            {isEdit ? "ویرایش مشکل بالینی" : "ثبت مشکل بالینی جدید"}
          </DialogTitle>
          <DialogDescription>
            نام بیماری را دقیق و مطابق اصطلاح پزشکی وارد کنید.
          </DialogDescription>
        </DialogHeader>

        <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="condition_name">نام بیماری *</Label>
            <Input
              id="condition_name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={200}
              placeholder="مثال: دیابت نوع ۲ (Type 2 Diabetes)"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>وضعیت</Label>
              <Select
                items={conditionStatusOptions}
                value={status}
                onValueChange={(value) => setStatus(value as ConditionStatus)}
              >
                <SelectTrigger className="w-full" aria-label="وضعیت">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {conditionStatusOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="onset_date">تاریخ شروع (میلادی)</Label>
              <Input
                id="onset_date"
                type="date"
                value={onsetDate}
                onChange={(event) => setOnsetDate(event.target.value)}
                dir="ltr"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="resolved_date">تاریخ رفع (میلادی)</Label>
              <Input
                id="resolved_date"
                type="date"
                value={resolvedDate}
                onChange={(event) => setResolvedDate(event.target.value)}
                dir="ltr"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="condition_notes">یادداشت</Label>
            <Textarea
              id="condition_notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={2}
            />
          </div>

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

/** «+» button in the conditions card header. */
export function AddConditionButton({ patientId }: { patientId: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="ثبت مشکل بالینی جدید"
        onClick={() => setOpen(true)}
      >
        <PlusIcon />
      </Button>
      <ConditionFormDialog patientId={patientId} open={open} onOpenChange={setOpen} />
    </>
  );
}

/** Per-row edit/delete actions for a condition. */
export function ConditionRowActions({
  patientId,
  condition,
}: {
  patientId: number;
  condition: Condition;
}) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="flex items-center gap-1">
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

      <ConditionFormDialog
        patientId={patientId}
        condition={condition}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف مشکل بالینی"
        description={`«${condition.name}» از پرونده بیمار حذف می‌شود.`}
        confirmLabel="حذف"
        onConfirm={async () => {
          await api.deleteCondition(condition.id);
          router.refresh();
        }}
      />
    </div>
  );
}
