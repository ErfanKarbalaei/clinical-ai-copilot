"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { PatientFormDialog } from "@/components/patients/patient-form-dialog";
import { api } from "@/lib/api";
import type { Patient } from "@/lib/types";

/** «افزودن بیمار» — opens the create dialog (Phase 3 primary action). */
export function AddPatientButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="lg" className="px-4" onClick={() => setOpen(true)}>
        <PlusIcon />
        افزودن بیمار
      </Button>
      <PatientFormDialog open={open} onOpenChange={setOpen} />
    </>
  );
}

/** Pencil button — opens the edit dialog for an existing patient. */
export function EditPatientButton({ patient }: { patient: Patient }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="ویرایش اطلاعات بیمار"
        title="ویرایش اطلاعات بیمار"
        onClick={() => setOpen(true)}
      >
        <PencilIcon />
      </Button>
      <PatientFormDialog patient={patient} open={open} onOpenChange={setOpen} />
    </>
  );
}

/** Delete button with confirmation — removes the patient and all related data. */
export function DeletePatientButton({ patient }: { patient: Patient }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  async function handleDelete() {
    await api.deletePatient(patient.id);
    router.push("/patients");
    router.refresh();
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        className="text-destructive hover:text-destructive"
        aria-label="حذف بیمار"
        title="حذف بیمار"
        onClick={() => setOpen(true)}
      >
        <Trash2Icon />
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="حذف بیمار"
        description={`حذف «${patient.first_name} ${patient.last_name}» همهٔ اطلاعات بالینی مرتبط (بیماری‌ها، داروها، حساسیت‌ها، اسناد و…) را نیز حذف می‌کند. این عمل بازگشت‌پذیر نیست.`}
        confirmLabel="حذف قطعی"
        onConfirm={handleDelete}
      />
    </>
  );
}
