# Meridian Systems, Inc. — Incident Response, Business Continuity, and Disaster Recovery Policy

**SYNTHETIC SAMPLE DOCUMENT. Illustrative test data for Attestly benchmarking. Meridian Systems is a fictional company.**

Version 3.0 · Last reviewed: 2025-11-20 · Owner: CISO and VP Engineering

## 1. Incident Response

Meridian maintains a documented incident response plan covering detection, triage, containment, eradication, recovery, and post-incident review. The plan is reviewed and tested at least annually, including a tabletop exercise with the security and engineering teams.

- Security alerts are triaged against defined severity levels (SEV1 to SEV4) with target response times per level.
- A 24/7 on-call rotation provides coverage for security and availability alerts.
- Root cause analysis is performed after every SEV1 and SEV2 incident, with corrective actions tracked.
- Customers can report suspected security issues through security@meridian.example, and Meridian operates a responsible disclosure program.

## 2. Breach Notification

In the event of a confirmed breach affecting customer data, Meridian notifies affected customers within 72 hours of confirmation, consistent with contractual and regulatory obligations. Notifications describe what happened, the data involved, and remediation steps.

## 3. Logging and Detection

- Security events are centralized in a SIEM and retained for 365 days.
- Endpoint detection and response (EDR) and intrusion detection are deployed across production.
- Log integrity is protected; administrative and configuration changes are recorded in an audit trail.

## 4. Business Continuity

Meridian maintains a business continuity plan addressing loss of facilities, key personnel, and critical suppliers. Runbooks are maintained for critical operational procedures.

## 5. Disaster Recovery

- Production is deployed across multiple AWS Availability Zones; critical components are redundant.
- The disaster recovery plan defines a Recovery Time Objective (RTO) of 4 hours and a Recovery Point Objective (RPO) of 1 hour.
- Backups are performed daily, encrypted, and stored in a separate account and region. Restores are tested quarterly.
- Multi-region failover is available for Enterprise customers.
- Disaster recovery exercises are conducted at least annually, and results feed back into the plan.

## 6. Change Management

A documented change management process governs production changes. Changes are peer-reviewed, tested in staging, and deployed through automated pipelines with the ability to roll back. Customers are notified in advance of major scheduled maintenance through the status page.
