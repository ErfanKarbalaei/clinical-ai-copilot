/**
 * Typed client for the backend REST API (`/api/v1`).
 *
 * Used from both server components (initial data) and client components
 * (mutations), always with `cache: "no-store"` so data is fresh.
 */

import type {
  Allergy,
  AllergyPayload,
  Condition,
  ConditionPayload,
  Patient,
  PatientCreatePayload,
  PatientListResponse,
  PatientMedication,
  PatientMedicationCreatePayload,
  PatientMedicationUpdatePayload,
  PatientOverview,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("ارتباط با سرور برقرار نشد.", 0);
  }

  if (!response.ok) {
    let detail = `خطای سرور (کد ${response.status})`;
    if (response.status === 422) {
      detail = "داده‌های ارسالی معتبر نیست.";
    } else {
      try {
        const body = await response.json();
        if (typeof body?.detail === "string") detail = body.detail;
      } catch {
        // keep the generic message
      }
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function withQuery(
  base: string,
  params: Record<string, string | number | undefined>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${base}?${query}` : base;
}

export const api = {
  // --- patients ---
  listPatients(params: { q?: string; limit?: number; offset?: number } = {}) {
    return request<PatientListResponse>(withQuery("/patients", params));
  },
  createPatient(payload: PatientCreatePayload) {
    return request<Patient>("/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updatePatient(id: number, payload: Partial<PatientCreatePayload>) {
    return request<Patient>(`/patients/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deletePatient(id: number) {
    return request<void>(`/patients/${id}`, { method: "DELETE" });
  },
  getPatientOverview(id: number) {
    return request<PatientOverview>(`/patients/${id}/overview`);
  },

  // --- conditions ---
  createCondition(patientId: number, payload: ConditionPayload) {
    return request<Condition>(`/patients/${patientId}/conditions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateCondition(conditionId: number, payload: Partial<ConditionPayload>) {
    return request<Condition>(`/conditions/${conditionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteCondition(conditionId: number) {
    return request<void>(`/conditions/${conditionId}`, { method: "DELETE" });
  },

  // --- allergies ---
  createAllergy(patientId: number, payload: AllergyPayload) {
    return request<Allergy>(`/patients/${patientId}/allergies`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateAllergy(allergyId: number, payload: Partial<AllergyPayload>) {
    return request<Allergy>(`/allergies/${allergyId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteAllergy(allergyId: number) {
    return request<void>(`/allergies/${allergyId}`, { method: "DELETE" });
  },

  // --- patient medications ---
  createPatientMedication(
    patientId: number,
    payload: PatientMedicationCreatePayload
  ) {
    return request<PatientMedication>(`/patients/${patientId}/medications`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updatePatientMedication(
    recordId: number,
    payload: PatientMedicationUpdatePayload
  ) {
    return request<PatientMedication>(`/patient-medications/${recordId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deletePatientMedication(recordId: number) {
    return request<void>(`/patient-medications/${recordId}`, {
      method: "DELETE",
    });
  },
};
