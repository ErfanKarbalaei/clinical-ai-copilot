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
 * Sticky clinical identity header (Phase 1 design): patient identity on the
 * right, highly visible clinical warning chips on the left — severe
 * allergies are never buried inside a card.
 */
export function PatientIdentityBar({
  patient,
  allergies,
  activeConditionCount,
}: PatientIdentityBarProps) {
  const age = calculateAge(patient.date_of_birth);
  const severe = allergies.filter((allergy) => allergy.severity === "severe");

  const metaParts = [
    age !== null ? `${faNum(age)} ساله` : null,
    genderLabels[patient.gender],
    patient.national_code ? `کد ملی ${patient.national_code}` : null,
  ].filter(Boolean);

  return (
    <div className="sticky top-13 z-30 border-b bg-card">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2 lg:px-6">
        {/* identity — right in RTL */}
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-9.5 shrink-0 items-center justify-center rounded-full bg-brand-soft text-[13px] font-semibold text-brand">
            {patient.first_name.charAt(0)} {patient.last_name.charAt(0)}
          </span>
          <div className="min-w-0">
            <h1 className="truncate text-base leading-6 font-semibold">
              {patient.first_name} {patient.last_name}
            </h1>
            <p className="flex flex-wrap items-center gap-x-1.5 text-xs leading-5 text-muted-foreground">
              <span>{metaParts.join(" · ")}</span>
              {patient.phone ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span dir="ltr" className="font-mono tabular-nums">
                    {patient.phone}
                  </span>
                </>
              ) : null}
            </p>
          </div>
        </div>

        {/* clinical warnings + record actions — left in RTL */}
        <div className="flex flex-wrap items-center gap-2">
          {severe.map((allergy) => (
            <span
              key={allergy.id}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-critical-border bg-critical-soft px-3 text-xs font-semibold text-critical"
            >
              <TriangleAlertIcon className="size-3.5 shrink-0" />
              آلرژی شدید: {allergy.allergen}
            </span>
          ))}
          {activeConditionCount > 0 ? (
            <span className="inline-flex h-8 items-center rounded-lg bg-surface-2 px-3 text-xs font-medium text-muted-foreground">
              {faNum(activeConditionCount)} مشکل فعال
            </span>
          ) : null}
          <span className="flex items-center gap-1.5">
            <EditPatientButton patient={patient} />
            <DeletePatientButton patient={patient} />
          </span>
        </div>
      </div>
    </div>
  );
}
