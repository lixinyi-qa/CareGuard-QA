# Security policy

This repository is a portfolio and local demonstration project. It must not be used to store real health, identity, contact, or emergency data.

## Reporting a vulnerability

Please open a GitHub issue without including exploitable secrets or personal data. Describe the affected component, reproduction conditions, expected result, and observed result.

## Secrets and demo data

- Never commit `.env`, API keys, access tokens, database files, or generated production data.
- Use `.env.example` only as a template and replace all development secrets before any deployment.
- The bundled phone numbers and accounts are fictitious local demo data.
- If a real credential is committed, revoke or rotate it immediately before removing it from history.
