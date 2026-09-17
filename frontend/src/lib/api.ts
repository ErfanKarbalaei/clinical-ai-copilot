/**
 * Typed client for the backend REST API (`/api/v1`).
 *
 * Used from both server components (initial data) and client components
 * (mutations), always with `cache: "no-store"` so data is fresh.
 */

import type {
  Allergy,
  AllergyPayload,
  AiMedicationSafetyCheckPayload,
  AiMedicationSafetyResult,
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
  SendMessagePayload,
  SendMessageResult,
  ChatTurn,
  ClinicalNoteFromVoicePayload,
  Condition,
  ConditionPayload,
  Document,
  Patient,
  PatientContext,
  PatientCreatePayload,
  PatientListResponse,
  PatientMedication,
  PatientMedicationCreatePayload,
  PatientMedicationUpdatePayload,
  PatientOverview,
  PatientTimeline,
  VoiceNote,
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
  // For FormData bodies the Content-Type header must NOT be set manually —
  // the browser generates it including the multipart boundary.
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers,
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
  getPatientContext(id: number) {
    return request<PatientContext>(`/patients/${id}/context`);
  },
  getPatientTimeline(id: number) {
    return request<PatientTimeline>(`/patients/${id}/timeline`);
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

  // --- documents ---
  listDocuments(patientId: number) {
    return request<Document[]>(`/patients/${patientId}/documents`);
  },
  uploadDocument(
    patientId: number,
    form: { file: File; title?: string; docType?: string }
  ) {
    const body = new FormData();
    body.append("file", form.file);
    if (form.title) body.append("title", form.title);
    if (form.docType) body.append("doc_type", form.docType);
    return request<Document>(`/patients/${patientId}/documents`, {
      method: "POST",
      body,
    });
  },
  reextractDocument(documentId: number) {
    return request<Document>(`/documents/${documentId}/extract`, {
      method: "POST",
    });
  },
  deleteDocument(documentId: number) {
    return request<void>(`/documents/${documentId}`, { method: "DELETE" });
  },
  documentDownloadUrl(documentId: number): string {
    return `${API_BASE_URL}/documents/${documentId}/download`;
  },

  // --- voice notes (Persian speech-to-text) ---
  listVoiceNotes(patientId: number) {
    return request<VoiceNote[]>(`/patients/${patientId}/voice-notes`);
  },
  uploadVoiceNote(
    patientId: number,
    form: {
      file: File;
      title?: string;
      conversationType?: string;
      durationSeconds?: number;
    }
  ) {
    const body = new FormData();
    body.append("file", form.file);
    if (form.title) body.append("title", form.title);
    if (form.conversationType)
      body.append("conversation_type", form.conversationType);
    if (form.durationSeconds != null)
      body.append("duration_seconds", String(Math.round(form.durationSeconds)));
    return request<VoiceNote>(`/patients/${patientId}/voice-notes`, {
      method: "POST",
      body,
    });
  },
  retranscribeVoiceNote(voiceNoteId: number) {
    return request<VoiceNote>(`/voice-notes/${voiceNoteId}/transcribe`, {
      method: "POST",
    });
  },
  createNoteFromVoiceNote(
    voiceNoteId: number,
    payload: ClinicalNoteFromVoicePayload
  ) {
    return request<unknown>(`/voice-notes/${voiceNoteId}/note`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  renameVoiceNote(voiceNoteId: number, title: string) {
    return request<VoiceNote>(`/voice-notes/${voiceNoteId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  },
  deleteVoiceNote(voiceNoteId: number) {
    return request<void>(`/voice-notes/${voiceNoteId}`, { method: "DELETE" });
  },
  voiceNoteDownloadUrl(voiceNoteId: number): string {
    return `${API_BASE_URL}/voice-notes/${voiceNoteId}/download`;
  },

  // --- clinical AI assistant (decision support) ---
  askClinicalQuestion(
    patientId: number,
    question: string,
    history: ChatTurn[] = [],
    medicationSafety = false
  ) {
    return request<ChatResponse>(`/patients/${patientId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question, history, medication_safety: medicationSafety }),
    });
  },

  // --- AI-assisted medication safety (decision support) ---
  aiMedicationSafetyCheck(
    patientId: number,
    payload: AiMedicationSafetyCheckPayload
  ) {
    return request<AiMedicationSafetyResult>(
      `/patients/${patientId}/medications/ai-safety-check`,
      { method: "POST", body: JSON.stringify(payload) }
    );
  },

  // --- persistent clinical conversations (Task 15) ---
  listConversations(patientId: number) {
    return request<ConversationSummary[]>(
      `/patients/${patientId}/conversations`
    );
  },
  createConversation(patientId: number, title?: string) {
    return request<ConversationSummary>(`/patients/${patientId}/conversations`, {
      method: "POST",
      body: JSON.stringify(title ? { title } : {}),
    });
  },
  getConversation(conversationId: number) {
    return request<ConversationDetail>(`/conversations/${conversationId}`);
  },
  sendConversationMessage(
    conversationId: number,
    payload: SendMessagePayload
  ) {
    return request<SendMessageResult>(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  deleteConversation(conversationId: number) {
    return request<void>(`/conversations/${conversationId}`, { method: "DELETE" });
  },
};
