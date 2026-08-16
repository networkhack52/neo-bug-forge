# Acme SaaS — Security, Compliance & Company Handbook (eval fixture)

Synthetic but realistic. This fixture is deliberately larger than the control
list, with adjacent and unrelated passages, so that "just abstain" is not the
easy default — near-miss evidence is present for the contradicted-case tests.
Anything NOT stated here is, by definition, unsupported. Specific figures below
(frequencies, key sizes, retention windows, SLAs) are the ground truth the
contradicted questions push against.

## Company overview
Acme SaaS builds workflow-automation software for mid-market operations teams.
Founded 2019, headquartered in Austin, roughly 140 employees across the US and
EU. The platform is multi-tenant and cloud-hosted.

## Product
The product offers workflow builders, approvals, dashboards, and an open REST
API. Customers integrate via API keys and webhooks. There is a sandbox
environment for testing. None of this is security-control evidence.

## Support and success
Standard support is available business hours (9am-6pm CT). Enterprise plans add
a named customer success manager. Support tickets are handled in a shared
helpdesk. This section is operational, not a security control.

## Access control
- Multi-factor authentication (MFA) is enforced for all employee access to
  internal systems, the identity provider (Okta SSO), cloud consoles, and code
  repositories. Access without a second factor is blocked.
- Access is granted on a least-privilege basis using role-based access control
  (RBAC). Employees receive only the minimum access required for their role.
- User access is reviewed **quarterly**. Access is revoked within **24 hours**
  of an employee's departure.
- Employee SSO is via Okta. Customer-facing SSO options are not described here.

## Encryption
- All customer data is encrypted at rest using **AES-256**, including primary
  databases, object storage, and backups.
- Data in transit is encrypted using **TLS 1.2 or higher**. HTTP is redirected
  to HTTPS and HSTS is enabled.
- Encryption keys are managed by the cloud provider's managed key service.

## Testing and vulnerabilities
- An independent third party performs penetration testing **at least annually**.
- Vulnerability scanning runs continuously. Critical vulnerabilities are
  remediated on a defined schedule; specific hour-level SLAs are not stated.

## Resilience and operations
- Backups run **daily** and are encrypted at rest.
- The production service targets **99.9%** monthly availability.
- A documented incident response plan defines severity levels, roles, and
  communication paths.
- In the event of a confirmed breach affecting customer data, we notify affected
  customers without undue delay.

## Logging and monitoring
- Application, infrastructure, and access logs are centrally collected and
  retained for **at least 12 months**.
- Logs are protected from tampering. Real-time alerting specifics are not
  described in this document.

## Compliance and privacy
- We maintain a **SOC 2 Type II** attestation covering the Security trust
  services criteria.
- We comply with the **GDPR** as a data processor and offer a Data Processing
  Agreement (DPA) incorporating Standard Contractual Clauses.
- Upon termination, customer data is deleted from production systems **within 30
  days**. Backups age out on their normal rotation.

## People and process
- All employees complete security awareness training **at least annually**.
- Changes to production follow a change-management process that requires peer
  code review before deployment.
- We perform security risk reviews of key vendors and subprocessors.

## Facilities
The corporate office uses badge access and visitor sign-in. Production runs
entirely in the public cloud; Acme operates no data centers of its own.

## Marketing boilerplate
Acme is trusted by teams who care about moving fast without breaking things.
This is marketing copy and carries no compliance weight.
