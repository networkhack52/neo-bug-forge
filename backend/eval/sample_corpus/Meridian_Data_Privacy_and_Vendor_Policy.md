# Meridian Systems, Inc. — Data Protection, Privacy, and Vendor Management Policy

**SYNTHETIC SAMPLE DOCUMENT. Illustrative test data for Attestly benchmarking. Meridian Systems is a fictional company.**

Version 2.6 · Last reviewed: 2026-01-05 · Owner: Data Protection Officer (DPO)

## 1. Privacy and Regulatory

- Meridian complies with the EU General Data Protection Regulation (GDPR) for personal data of EU data subjects and acts as a processor on behalf of customers.
- A Data Processing Agreement (DPA) is signed with customers on request.
- A public privacy policy describes Meridian's data practices.
- Data subject access requests (DSARs) are honored within regulatory timeframes.

## 2. Data Residency and Storage

- Customer data is stored only in the regions disclosed to the customer (us-east-1 and eu-west-1).
- Data residency options are offered: customers may elect EU-only storage.
- Meridian does not use customer data to train shared or cross-customer machine learning models.

## 3. Retention and Deletion

- Meridian maintains a documented data retention policy. Customer-configurable retention windows are supported for in-product data.
- Security event logs are retained for 365 days.
- On contract termination, customer data is retained for a wind-down window of typically 30 days to allow export, after which it is deleted from production systems. Deletion is evidenced through deletion logs.
- Customer-initiated data export is available, and an audit log export can be provided to customers.
- Media containing customer data is sanitized before decommissioning using a documented process.

## 4. Product Security Features

- Role-based access control (RBAC) is available within the product.
- Administrative actions in the product are audit-logged.
- SCIM is supported for automated user provisioning and de-provisioning.
- Single sign-on (SSO) is supported for customer administrators.
- Configurable session timeout controls are available to end users.
- IP allow-listing is supported for customer access.
- Alerting webhooks notify customers of security-relevant events.

## 5. Vendor and Subprocessor Management

- Third-party vendors are assessed for security before onboarding, with periodic reassessment.
- A public register of subprocessors is maintained and updated when it changes.
- A formal vendor offboarding process revokes access and recovers or destroys data at the end of an engagement.

## 6. Physical Security

- Meridian is a cloud-hosted, remote-first company and does not operate its own data centers.
- Production is hosted in AWS facilities that hold SOC 2 and ISO 27001 attestations.
- Access to Meridian office space is controlled via badge access.

## 7. Out of Scope

Meridian does not offer on-premises or single-tenant hardware appliances, and does not currently hold FedRAMP or PCI DSS authorization.
