import { TriangleAlertIcon } from "lucide-react";

import {
  DeletePatientButton,
  EditPatientButton,
} from "@/components/patients/patient-actions";
import { calculateAge, faNum, genderLabels } from "@/lib/format";
import type { Allergy, Patient } from "@/lib/types";

interface PatientIdentityBarProps {
  patient: Patient;
  allergies: Allergy[];
  activeConditionCount: number;
}

/**
 * Sticky clinical identity header (Phase 2 polish): the patient name is the
 * strongest visual anchor of the workspace; age/gender follow directly,
 * technical identifiers (national ID / phone) stay visually distinct as LTR
 * mono values, and severe-allergy warning chips stay immediately visible —
 * none of it taller than a clinical header needs to be.
 */
export function PatientIdentityBar({
  patient,
  allergies,
  activeConditionCount,
}: PatientIdentityBarProps) {
  const age = calculateAge(patient.date_of_birth);
  const severe = allergies.filter((allergy) => allergy.severity === "severe");

  return (
    <div className="sticky top-13 z-30 border-b bg-card">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 px-4 py-2 lg:px-6">
        {/* identity — right in RTL */}
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand">
            {patient.first_name.charAt(0)} {patient.last_name.charAt(0)}
          </span>
          <div className="min-w-0">
            <h1 className="truncate text-lg leading-7 font-bold">
              {patient.first_name} {patient.last_name}
            </h1>
            <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] leading-4">
              <span className="text-xs font-medium text-muted-foreground">
                {[
                  age !== null ? `${faNum(age)} ساله` : null,
                  genderLabels[patient.gender],
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {patient.national_code ? (
                <span dir="ltr" className="font-mono text-faint tabular-nums">
                  {patient.national_code}
                </span>
              ) : null}
              {patient.phone ? (
                <span dir="ltr" className="font-mono text-faint tabular-nums">
                  {patient.phone}
                </span>
              ) : null}
            </p>
          </div>
        </div>

        {/* clinical warnings + record actions — left in RTL */}
        <div className="flex flex-wrap items-center gap-1.5">
          {severe.map((allergy) => (
            <span
              key={allergy.id}
              className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-critical-border bg-critical-soft px-2.5 text-[11px] font-semibold text-critical"
            >
              <TriangleAlertIcon className="size-3.5 shrink-0" />
              آلرژی شدید: {allergy.allergen}
            </span>
          ))}
          {activeConditionCount > 0 ? (
            <span className="inline-flex h-7 items-center rounded-lg bg-surface-2 px-2.5 text-[11px] font-medium text-muted-foreground">
              {faNum(activeConditionCount)} مشکل فعال
            </span>
          ) : null}
          <span className="flex items-center gap-0.5">
            <EditPatientButton patient={patient} />
            <DeletePatientButton patient={patient} />
          </span>
        </div>
      </div>
    </div>
  );
}
