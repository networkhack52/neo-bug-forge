# Meridian Systems, Inc. — SOC 2 Type II Report (Summary)

**SYNTHETIC SAMPLE DOCUMENT. Illustrative test data for Attestly benchmarking. Meridian Systems is a fictional company; nothing here describes a real organization.**

Service Organization: Meridian Systems, Inc.
Report type: SOC 2 Type II
Trust Services Criteria: Security, Availability, Confidentiality
Review period: January 1, 2025 to December 31, 2025
Report date: February 15, 2026
Independent auditor: Barrow & Kline LLP (fictional)
Opinion: Unqualified. Controls were suitably designed and operating effectively throughout the review period.

## Scope

The description covers the Meridian production platform hosted on Amazon Web Services (AWS) in the us-east-1 and eu-west-1 regions, including the application, database, and supporting infrastructure services used to deliver the Meridian SaaS to customers.

## Control Environment and Governance

Meridian maintains a documented Information Security Policy, reviewed and approved by management at least annually. A designated Chief Information Security Officer (CISO) owns the security program. A formal risk assessment is performed at least annually and after significant changes, with identified risks tracked to treatment.

Meridian is certified to ISO/IEC 27001:2022 (certificate issued 2024, surveillance audit completed 2025). An independent SOC 2 Type II examination is performed annually.

## Logical Access (CC6)

- Multi-factor authentication (MFA) is enforced for all employee access to production systems, cloud consoles, and administrative interfaces, delivered through the corporate identity provider (SSO via Okta).
- Access to customer data is granted on a least-privilege, role-based (RBAC) basis. Production access is limited to a small on-call engineering group and requires documented business justification.
- User access rights are reviewed quarterly, with review evidence retained.
- Access is provisioned through an approval workflow and de-provisioned within 24 hours of employee termination.
- Privileged administrative accounts are separated from standard user accounts. Shared or generic accounts are prohibited for production access.
- A password policy enforces a minimum length of 12 characters, complexity requirements, and lockout after repeated failed attempts. Authentication endpoints are rate limited to slow brute-force attempts.
- Remote access to production is brokered through a zero-trust access gateway; direct network access is not permitted.

## Encryption and Key Management (CC6.7)

- All customer data is encrypted at rest using AES-256.
- All data in transit is encrypted using TLS 1.2 or higher, including internal service-to-service traffic.
- Encryption keys are managed in AWS Key Management Service (KMS). Keys are rotated at least annually.
- Tenant data is logically isolated at the application and database layers. Meridian operates a shared multi-tenant architecture; dedicated single-tenant deployment is not offered.

## System Operations and Monitoring (CC7)

- Security events are collected centrally in a SIEM. Security logs are retained for 365 days.
- Endpoint detection and response (EDR) and network intrusion detection are deployed across production.
- A 24/7 on-call rotation responds to security and availability alerts, which are triaged against defined severity levels.
- Configuration changes to production are recorded in an audit trail. Administrative actions within the product are audit-logged and available to customers on request.
- Failed administrative login attempts are logged and alerted. Log integrity is protected through write-once storage and access controls.

## Change Management and Development (CC8)

- Meridian follows a documented secure software development lifecycle. All code changes are peer-reviewed before merge.
- Development, staging, and production environments are separated.
- Static application security testing (SAST) and software composition analysis (SCA) run in the CI pipeline; dependencies are monitored for newly disclosed CVEs.
- Infrastructure is managed as code with reviewed changes.

## Vulnerability Management (CC7.1)

- An independent third party performs network and application penetration testing at least annually; findings are tracked to remediation.
- Automated vulnerability scans run weekly across infrastructure and container images.
- Critical vulnerabilities are remediated within 30 days against a documented SLA.
- A public web application firewall (WAF) and DDoS protection front public endpoints.

## Availability (A1)

- Production is deployed across multiple AWS Availability Zones with redundancy for critical components.
- Backups are performed daily, encrypted, and stored in a separate account and region. Backup restores are tested quarterly.
- The disaster recovery plan defines a Recovery Time Objective (RTO) of 4 hours and a Recovery Point Objective (RPO) of 1 hour. DR exercises are conducted at least annually.
- Meridian publishes a 99.9% uptime service level agreement and maintains a public status page for incidents and scheduled maintenance.

## Confidentiality and Incident Response

- A documented incident response plan is maintained and tested at least annually, including a tabletop exercise.
- In the event of a confirmed breach affecting customer data, Meridian notifies affected customers within 72 hours of confirmation.
- Root cause analysis is performed after security incidents.

## Complementary Notes

The following are not covered by this examination and were not in scope: FedRAMP authorization, PCI DSS, and HITRUST. Meridian does not currently hold these authorizations.
