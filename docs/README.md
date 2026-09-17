# Documentation — Clinical AI Copilot

This directory contains the project's architecture and implementation documentation.

Planned contents (added incrementally, only as features are actually implemented):

- `architecture/` — system architecture and data-flow diagrams
- `data-model/` — database schema and entity documentation
- `decisions/` — short records of important technical decisions and their reasons
- feature-specific implementation notes

Current contents:

- `data-model/` — patient database schema, relationships, and design decisions
- `task-01-foundation-report.md` — Task 1 (project foundation) implementation report
- `task-02-data-model-report.md` — Task 2 (patient data model) implementation report
- `task-03-patient-api-report.md` — Task 3 (patient CRUD API) implementation report
- `task-04-clinical-apis-report.md` — Task 4 (conditions/allergies/medications APIs + overview) implementation report
- `task-05-frontend-report.md` — Task 5 (frontend: patients list + clinical record) implementation report
- `task-06-documents-report.md` — Task 6 (document upload/storage API with MinIO) implementation report
- `task-07-extraction-report.md` — Task 7 (deterministic text extraction: PDF + OCR, frontend documents UI) implementation report
- `task-08-voice-notes-report.md` — Task 8 (Persian speech-to-text: voice notes API + UI via Speechmatics) implementation report
- `task-09-context-timeline-report.md` — Task 9 (patient context builder + unified clinical timeline) implementation report
- `task-10-ai-assistant-report.md` — Task 10 (clinical AI assistant: provider-agnostic chat grounded in patient context) implementation report
- `task-10.5-gemini-report.md` — Task 10.5 (connecting the AI layer to Google Gemini) implementation report
- `task-11-medication-safety-report.md` — Task 11 (deterministic medication-safety rule engine + optional LLM explanation) implementation report
- `task-12-document-analysis-report.md` — Task 12 (AI analysis of extracted document text) implementation report
- `task-13-voice-documentation-report.md` — Task 13 (STT provider abstraction + optional Gemini transcript cleanup) implementation report
- `task-14-ai-medication-safety-report.md` — Task 14 (AI-assisted medication-safety analysis: structured endpoint + chat safety mode) implementation report
- `task-15-persistent-clinical-chat-report.md` — Task 15 (persistent clinical conversations: DB-backed chat history + conversation UI) implementation report
- `task-16-evidence-source-documents-report.md` — Task 16 (patient-record evidence ids + validated citations + original source-document access) implementation report
- `task-17-mcp-agent-spike-report.md` — Task 17 (local MCP server + clinical AI agent spike, with an honest keep/drop assessment) implementation report
- `task-18-authentication-report.md` — Task 18 (JWT authentication + patient-level access control) implementation report
