# Meridian Systems, Inc. — Information Security Policy

**SYNTHETIC SAMPLE DOCUMENT. Illustrative test data for Attestly benchmarking. Meridian Systems is a fictional company.**

Version 4.1 · Last reviewed: 2026-01-10 · Owner: Chief Information Security Officer (CISO)

## 1. Purpose and Governance

This policy defines how Meridian protects the confidentiality, integrity, and availability of customer and company information. It is reviewed and approved by management at least annually. The CISO owns the security program and reports to the executive team.

Meridian maintains a risk management process. A formal risk assessment is performed at least annually and after significant changes; risks are tracked to treatment with assigned owners.

## 2. Human Resources Security

- Background checks are performed on all employees before hire, where legally permitted.
- All employees sign confidentiality (non-disclosure) agreements as a condition of employment.
- Security awareness training is completed at hire and repeated at least annually.
- Meridian runs simulated phishing exercises on a recurring basis and tracks results.
- Security responsibilities are defined in role descriptions and a shared responsibility model published to customers.

## 3. Asset and Endpoint Management

- Meridian maintains an inventory of company assets and devices.
- Employee endpoints are centrally managed (MDM), full-disk encrypted, and enforce automatic screen lock after inactivity.
- Default credentials are removed from all systems before deployment.
- Secrets are stored in a dedicated secrets manager, never in source code.

## 4. Data Classification and Handling

- Information is classified (Public, Internal, Confidential, Restricted) under a documented data classification policy.
- Personally identifiable information (PII) is inventoried and tracked.
- Data minimization is applied: Meridian collects only the data required to deliver the service.
- Sensitive fields are masked or tokenized in logs and non-production environments where appropriate.

## 5. Network Security

- Production networks are segmented from corporate networks.
- Inbound access is restricted by security groups and firewalls; only required ports are exposed.
- Administrative access to cloud consoles requires MFA.
- Outbound traffic is monitored for anomalous behavior.
- Content Security Policy (CSP) headers are enforced on web application responses, and all user-supplied input is validated and sanitized.

## 6. Compliance

- Meridian is certified to ISO/IEC 27001:2022 and undergoes an annual SOC 2 Type II examination.
- A public list of current compliance certifications is maintained.
- Meridian carries cyber liability insurance.
- Recurring third-party security assessments are performed in addition to the annual audit.
- A security whitepaper is available to customers on request.

## 7. Exceptions

Policy exceptions require documented CISO approval, a compensating control, and a defined expiry date.
