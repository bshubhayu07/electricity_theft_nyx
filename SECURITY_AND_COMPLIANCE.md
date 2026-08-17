# Smart Grid Data Protection, Governance & CERT-In Compliance Specification

**Version:** 2.4.0-enterprise  
**Standard:** Digital Personal Data Protection (DPDP Rules 2025) & CERT-In Cyber Security Directions

---

## 1. Data Governance Principles

Smart meter consumption readings constitute sensitive consumer energy usage data. The system enforces strict data minimization, ephemeral processing, and auditable deletion controls.

1. **Zero-Byte Retention for Ad-Hoc Queries:** Ad-hoc raw daily consumption series submitted via `POST /score` are processed entirely in memory. Raw arrays are purged immediately following feature extraction and risk scoring.
2. **Pseudonymized Consumer Identifiers:** All consumer IDs and transformer feeder tags are pseudonymized hashes (e.g., `C100348`, `T024`) stripped of personally identifiable information (PII).
3. **Cryptographic Deletion Receipts:** The `POST /purge-session` endpoint clears in-memory session caches and generates a SHA-256 verifiable compliance receipt (`DEL-CERT-XXXXXXXXXXXX`).

---

## 2. CERT-In Incident Response & SLA Protocol

In accordance with CERT-In directions:
* **Cyber Security Incident Reporting:** Any unauthorized data access or anomaly modification attempt is logged with UTC/IST timestamps and reported within 6 hours.
* **Audit Trail Integrity:** System audit logs record API requests, risk thresholds, and feature attribution extractions without storing raw consumer PII.
