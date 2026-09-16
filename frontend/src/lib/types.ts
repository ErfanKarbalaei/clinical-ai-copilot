/** TypeScript types mirroring the backend API schemas (Tasks 3 & 4). */

export type Gender = "male" | "female" | "other" | "unknown";
export type ConditionStatus = "active" | "resolved";
export type AllergySeverity = "mild" | "moderate" | "severe" | "unknown";
export type MedicationStatus = "active" | "stopped" | "completed";
export type ResultFlag = "normal" | "abnormal" | "critical";
export type NoteSource = "manual" | "voice" | "ai_assisted";
export type DocumentType =
  | "lab_report"
  | "imaging_report"
  | "discharge_summary"
  | "medical_note"
  | "other";
export type ExtractionStatus = "pending" | "processing" | "completed" | "failed";
export type ConversationType = "physician_note" | "doctor_patient";
export type TranscriptionStatus = "pending" | "processing" | "completed" | "failed";
export type AnalysisStatus = "pending" | "completed" | "failed";

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  national_code: string | null;
  date_of_birth: string | null;
  gender: Gender;
  phone: string | null;
  address: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientListResponse {
  items: Patient[];
  total: number;
}

export interface PatientCreatePayload {
  first_name: string;
  last_name: string;
  national_code?: string | null;
  date_of_birth?: string | null;
  gender?: Gender;
  phone?: string | null;
  address?: string | null;
}

export interface Condition {
  id: number;
  patient_id: number;
  name: string;
  status: ConditionStatus;
  onset_date: string | null;
  resolved_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConditionPayload {
  name: string;
  status?: ConditionStatus;
  onset_date?: string | null;
  resolved_date?: string | null;
  notes?: string | null;
}

export interface Allergy {
  id: number;
  patient_id: number;
  allergen: string;
  reaction: string | null;
  severity: AllergySeverity;
  created_at: string;
  updated_at: string;
}

export interface AllergyPayload {
  allergen: string;
  reaction?: string | null;
  severity?: AllergySeverity;
}

export interface MedicationBrief {
  id: number;
  name: string;
  generic_name: string | null;
}

export interface PatientMedication {
  id: number;
  patient_id: number;
  medication: MedicationBrief;
  dosage: string | null;
  frequency: string | null;
  status: MedicationStatus;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientMedicationCreatePayload {
  medication_id?: number;
  medication_name?: string;
  generic_name?: string | null;
  dosage?: string | null;
  frequency?: string | null;
  status?: MedicationStatus;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
}

export interface PatientMedicationUpdatePayload {
  dosage?: string | null;
  frequency?: string | null;
  status?: MedicationStatus;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
}

export interface LabResult {
  id: number;
  patient_id: number;
  document_id: number | null;
  test_name: string;
  value: string;
  unit: string | null;
  reference_range: string | null;
  flag: ResultFlag | null;
  result_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClinicalNote {
  id: number;
  patient_id: number;
  voice_note_id: number | null;
  title: string;
  content: string;
  source: NoteSource;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: number;
  patient_id: number;
  title: string;
  doc_type: DocumentType;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  extraction_status: ExtractionStatus;
  extracted_text: string | null;
  analysis_status: AnalysisStatus;
  ai_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface VoiceNote {
  id: number;
  patient_id: number;
  title: string | null;
  conversation_type: ConversationType;
  duration_seconds: number | null;
  language: string;
  transcription_status: TranscriptionStatus;
  transcript: string | null;
  cleanup_status: AnalysisStatus;
  cleaned_note: string | null;
  error_message: string | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClinicalNoteFromVoicePayload {
  title: string;
  content: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  patient_id: number;
  question: string;
  answer: string;
  generated_at: string;
}

export interface PatientOverview {
  patient: Patient;
  conditions: Condition[];
  active_medications: PatientMedication[];
  allergies: Allergy[];
  recent_lab_results: LabResult[];
  recent_clinical_notes: ClinicalNote[];
}

export interface PatientContext {
  patient: Patient;
  conditions: Condition[];
  medications: PatientMedication[];
  allergies: Allergy[];
  lab_results: LabResult[];
  documents: Document[];
  voice_notes: VoiceNote[];
  clinical_notes: ClinicalNote[];
  generated_at: string;
}

export interface TimelineItem {
  event_type: string;
  date: string;
  title: string;
  description: string | null;
  source_type: string;
  source_id: number;
}

export interface PatientTimeline {
  items: TimelineItem[];
  total: number;
}
