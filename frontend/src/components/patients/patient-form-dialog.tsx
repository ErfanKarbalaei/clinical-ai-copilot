"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";

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
import { emptyToNull, genderOptions } from "@/lib/format";
import type { Gender, Patient } from "@/lib/types";

interface PatientFormDialogProps {
  /** Present → edit mode; absent → create mode. */
  patient?: Patient;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const FORM_ID = "patient-form";

export function PatientFormDialog({
  patient,
  open,
  onOpenChange,
}: PatientFormDialogProps) {
  const router = useRouter();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [nationalCode, setNationalCode] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [gender, setGender] = useState<Gender>("unknown");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = patient !== undefined;

  // Reset the form each time the dialog opens.
  useEffect(() => {
    if (!open) return;
    setFirstName(patient?.first_name ?? "");
    setLastName(patient?.last_name ?? "");
    setNationalCode(patient?.national_code ?? "");
    setDateOfBirth(patient?.date_of_birth ?? "");
    setGender(patient?.gender ?? "unknown");
    setPhone(patient?.phone ?? "");
    setAddress(patient?.address ?? "");
    setError(null);
    setSubmitting(false);
  }, [open, patient]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      national_code: emptyToNull(nationalCode),
      date_of_birth: emptyToNull(dateOfBirth),
      gender,
      phone: emptyToNull(phone),
      address: emptyToNull(address),
    };
    try {
      if (isEdit) {
        await api.updatePatient(patient.id, payload);
      } else {
        await api.createPatient(payload);
      }
      onOpenChange(false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "ثبت اطلاعات با خطا مواجه شد."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "ویرایش اطلاعات بیمار" : "بیمار جدید"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "اطلاعات هویتی بیمار را ویرایش کنید."
              : "اطلاعات هویتی بیمار را وارد کنید. کد ملی باید دقیقاً ۱۰ رقم و یکتا باشد."}
          </DialogDescription>
        </DialogHeader>

        <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="first_name">نام *</Label>
              <Input
                id="first_name"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                required
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">نام خانوادگی *</Label>
              <Input
                id="last_name"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                required
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="national_code">کد ملی (۱۰ رقم)</Label>
              <Input
                id="national_code"
                value={nationalCode}
                onChange={(event) => setNationalCode(event.target.value)}
                inputMode="numeric"
                dir="ltr"
                pattern="\d{10}"
                placeholder="0012345678"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="date_of_birth">تاریخ تولد (میلادی)</Label>
              <Input
                id="date_of_birth"
                type="date"
                value={dateOfBirth}
                onChange={(event) => setDateOfBirth(event.target.value)}
                dir="ltr"
              />
            </div>
            <div className="space-y-2">
              <Label>جنسیت</Label>
              <Select
                items={genderOptions}
                value={gender}
                onValueChange={(value) => setGender(value as Gender)}
              >
                <SelectTrigger className="w-full" aria-label="جنسیت">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {genderOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">شماره تماس</Label>
              <Input
                id="phone"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                dir="ltr"
                inputMode="tel"
                placeholder="09121234567"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="address">نشانی</Label>
            <Textarea
              id="address"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
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
