# Acme SaaS — Security Policy & SOC 2 Summary (eval fixture)

This is a synthetic, known document set for the answer-quality eval. It states a
fixed set of controls. Anything NOT written here is, by definition, unsupported.

## Access control
- Multi-factor authentication (MFA) is enforced for all employee access to
  internal systems, the identity provider (Okta SSO), cloud consoles, and code
  repositories. Access without a second factor is blocked.
- Access is granted on a least-privilege basis using role-based access control
  (RBAC). Employees receive only the minimum access required for their role.
- User access is reviewed quarterly. Access is revoked within 24 hours of an
  employee's departure.

## Encryption
- All customer data is encrypted at rest using AES-256, including primary
  databases, object storage, and backups.
- Data in transit is encrypted using TLS 1.2 or higher. HTTP is redirected to
  HTTPS and HSTS is enabled.

## Testing and vulnerabilities
- An independent third party performs penetration testing at least annually.
- Vulnerability scanning runs continuously; critical vulnerabilities are patched
  on a defined remediation schedule.

## Resilience and operations
- Backups run daily and are encrypted at rest.
- The production service targets 99.9% monthly availability.
- A documented incident response plan defines severity levels, roles, and
  communication paths.
- In the event of a confirmed breach affecting customer data, we notify affected
  customers without undue delay.

## Logging
- Application, infrastructure, and access logs are centrally collected and
  retained for at least 12 months.

## Compliance and privacy
- We maintain a SOC 2 Type II attestation covering the Security trust services
  criteria.
- We comply with the GDPR as a data processor and offer a Data Processing
  Agreement (DPA) incorporating Standard Contractual Clauses.
- Upon termination, customer data is deleted from production systems within 30
  days.

## People and process
- All employees complete security awareness training at least annually.
- Changes to production follow a change-management process that requires peer
  code review before deployment.
- We perform security risk reviews of key vendors and subprocessors.
