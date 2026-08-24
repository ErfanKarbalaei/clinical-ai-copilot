# Infrastructure — Clinical AI Copilot

Infrastructure configuration for local development.

Currently the only infrastructure definition is the root-level
`docker-compose.yml`, which starts:

- **PostgreSQL** — structured clinical data (patients, conditions, medications, metadata, ...)
- **MinIO** — S3-compatible object storage for original clinical documents and audio files

The backend and the frontend run locally during development and are not
containerized at this stage.

This directory is reserved for future infrastructure configuration (e.g.
container definitions for the application services) that will be added only
when the project actually needs it.
