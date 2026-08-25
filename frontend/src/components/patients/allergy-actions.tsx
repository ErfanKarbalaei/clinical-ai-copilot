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
import { ApiError, api } from "@/lib/api";
import { allergySeverityOptions } from "@/lib/format";
import type { Allergy, AllergySeverity } from "@/lib/types";

const FORM_ID = "allergy-form";

function AllergyFormDialog({
  patientId,
  allergy,
  open,
  onOpenChange,
}: {
  patientId: number;
  allergy?: Allergy;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [allergen, setAllergen] = useState("");
  const [reaction, setReaction] = useState("");
  const [severity, setSeverity] = useState<AllergySeverity>("unknown");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = allergy !== undefined;

  useEffect(() => {
    if (!open) return;
    setAllergen(allergy?.allergen ?? "");
    setReaction(allergy?.reaction ?? "");
    setSeverity(allergy?.severity ?? "unknown");
    setError(null);
    setSubmitting(false);
  }, [open, allergy]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload = {
      allergen: allergen.trim(),
      reaction: reaction.trim() === "" ? null : reaction.trim(),
      severity,
    };
    try {
      if (isEdit) {
        await api.updateAllergy(allergy.id, payload);
      } else {
        await api.createAllergy(patientId, payload);
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
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "ویرایش حساسیت" : "ثبت حساسیت جدید"}</DialogTitle>
          <DialogDescription>
            عامل حساسیت (دارو، غذا و…) و شدت واکنش را ثبت کنید.
          </DialogDescription>
        </DialogHeader>

        <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="allergen">عامل حساسیت *</Label>
            <Input
              id="allergen"
              value={allergen}
              onChange={(event) => setAllergen(event.target.value)}
              required
              maxLength={200}
              placeholder="مثال: پنی‌سیلین (Penicillin)"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="reaction">واکنش</Label>
            <Input
              id="reaction"
              value={reaction}
              onChange={(event) => setReaction(event.target.value)}
              maxLength={300}
              placeholder="مثال: کهیر، تنگی نفس"
            />
          </div>
          <div className="space-y-2">
            <Label>شدت</Label>
            <Select
              items={allergySeverityOptions}
              value={severity}
              onValueChange={(value) => setSeverity(value as AllergySeverity)}
            >
              <SelectTrigger className="w-full" aria-label="شدت">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {allergySeverityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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

/** «+» button in the allergies card header. */
export function AddAllergyButton({ patientId }: { patientId: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="ثبت حساسیت جدید"
        onClick={() => setOpen(true)}
      >
        <PlusIcon />
      </Button>
      <AllergyFormDialog patientId={patientId} open={open} onOpenChange={setOpen} />
    </>
  );
}

/** Per-row edit/delete actions for an allergy. */
export function AllergyRowActions({
  patientId,
  allergy,
}: {
  patientId: number;
  allergy: Allergy;
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

      <AllergyFormDialog
        patientId={patientId}
        allergy={allergy}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="حذف حساسیت"
        description={`حساسیت به «${allergy.allergen}» از پرونده بیمار حذف می‌شود.`}
        confirmLabel="حذف"
        onConfirm={async () => {
          await api.deleteAllergy(allergy.id);
          router.refresh();
        }}
      />
    </div>
  );
}
