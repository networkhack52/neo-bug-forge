# Synthetic trust corpus (Meridian Systems)

A realistic, **synthetic** set of trust documents for a fictional SaaS vendor
("Meridian Systems, Inc."). Use it to exercise the answering pipeline against a
representative corpus instead of the tiny onboarding sample, so coverage and
timing numbers reflect what a real customer with a full policy set would see.

**These are fabricated test fixtures. Meridian Systems is not a real company and
nothing here describes a real organization. Do not present any of it as real.**

## Files

- `Meridian_SOC2_TypeII_2025.md` — SOC 2 Type II report summary (period 2025, dated 2026-02-15).
- `Meridian_Information_Security_Policy.md` — governance, HR, assets, data classification, network, compliance.
- `Meridian_Incident_Response_and_BCDR_Policy.md` — IR, breach notification, logging, BC/DR, change management.
- `Meridian_Data_Privacy_and_Vendor_Policy.md` — privacy/GDPR, residency, retention/deletion, product security, vendors, physical.

## How to use

Upload all four into **Trust Documents** on a fresh account, then run the
126-question timing file. Together they ground the large majority of common
SIG/CAIQ topics with specific figures (AES-256, TLS 1.2+, quarterly access
reviews, 72-hour breach notification, 365-day log retention, RTO 4h / RPO 1h,
annual pen test, SOC 2 + ISO 27001, 30-day deletion, and so on).

A few topics are deliberately left absent or explicitly negative (FedRAMP, PCI
DSS, single-tenant/on-prem deployment) so the run still demonstrates correct
"No" answers and honest abstentions rather than 100% coverage.
