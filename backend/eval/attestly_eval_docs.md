# Acme SaaS — Trust Package (eval fixture v3)

Synthetic but realistic. This fixture models what a customer actually receives:
a SOC 2 Type II report plus the underlying security policies. It is deliberately
large (dozens of passages) so retrieval has to find the one relevant control
among many, not just abstain. Anything NOT stated here is, by definition,
unsupported. The specific figures below (frequencies, key sizes, retention
windows, SLAs, algorithms) are the ground truth the contradicted questions push
against.

# Part 1 — SOC 2 Type II Report (independent service auditor's report)

## Scope and period
This report covers the Security (Common Criteria) trust services category for
the Acme SaaS platform, for the period 1 January to 31 December. The other trust
services categories (Availability, Confidentiality, Processing Integrity,
Privacy) are not included in the scope of this examination.

## Opinion
In the service auditor's opinion, the controls were suitably designed and
operated effectively throughout the period to meet the applicable Security
criteria. The report is a **SOC 2 Type II** report.

## System overview
Acme SaaS provides multi-tenant workflow-automation software for mid-market
operations teams. The company was founded in 2019, is headquartered in Austin,
and has roughly 140 employees across the United States and the European Union.

## Infrastructure and subservice organizations
The production system runs entirely on a major public cloud provider, in United
States and European Union regions. Acme operates no data centers of its own and
relies on the cloud provider as a subservice organization, using the carve-out
method. Acme maintains no on-premises production infrastructure.

## Logical tenancy
The platform is multi-tenant. Tenants are logically isolated at the application
and data layers so that one customer cannot access another customer's data.

## Complementary user entity controls
Customers are responsible for managing their own end users, including how those
users authenticate to the customer's own systems. Customer-side authentication,
including any customer single sign-on, is outside the boundary of this report.

## Tests of controls — access
The auditor inspected the identity provider configuration and confirmed that
multi-factor authentication is enforced for all employees, with no exceptions
noted. Access provisioning and de-provisioning tickets were sampled and agreed
to the documented approvals.

## Tests of controls — change management
The auditor sampled production changes across the period and confirmed each had
a peer code review recorded before deployment, with no exceptions noted.

## Tests of controls — monitoring
The auditor confirmed that centralized logging was operating and that logs were
retained for the defined period, with no exceptions noted.

## Complementary note on availability
Availability commitments are described in customer agreements. This Security
report does not opine on availability, and specific recovery objectives are set
out in the customer's contract rather than in this report.

# Part 2 — Information Security Policy

## Governance
Acme maintains a documented information security program. Information security
policies are approved by management and reviewed at least annually. Security
responsibilities are formally assigned to the engineering and operations
leadership.

## Risk management
A security risk assessment is performed at least annually. Identified risks are
tracked to remediation and reviewed by leadership.

## Data classification
Data is classified by sensitivity, and handling requirements follow the
classification. Customer data is treated as confidential.

## Asset management
Acme maintains an inventory of production assets and data flows. Assets are
assigned owners.

## Acceptable use
An acceptable use policy governs the use of company devices and the handling of
company and customer data by employees.

# Part 3 — Access Control Policy

## Authentication
Multi-factor authentication (MFA) is enforced for all employee access to
internal systems, the identity provider (Okta SSO), cloud consoles, and code
repositories. Access without a second factor is blocked. MFA applies to every
employee, not only administrators.

## Passwords
Passwords must meet complexity and length requirements enforced by the identity
provider. Application passwords are hashed with bcrypt. Idle sessions time out
and require re-authentication.

## Authorization
Access is granted on a least-privilege basis using role-based access control
(RBAC). Employees receive only the minimum access required for their role.
Segregation of duties is enforced between those who develop changes and those
who approve deployment.

## Accounts
Every employee has a unique, named account. Shared or generic logins are
prohibited.

## Reviews and revocation
User access is reviewed quarterly. Access is revoked within 24 hours of an
employee's departure. Employee single sign-on is provided through Okta.

## Network access
Network access to production is restricted using cloud security groups on a
default-deny basis. Administrative access to infrastructure requires MFA.

# Part 4 — Cryptography Policy

## Data at rest
All customer data is encrypted at rest using AES-256, including primary
databases, object storage, and backups.

## Data in transit
Data in transit is encrypted using TLS 1.2 or higher. Plain HTTP is redirected
to HTTPS and HSTS is enabled.

## Key management
Encryption keys are managed by the cloud provider's managed key service and are
rotated at least annually.

## Secrets
Application secrets and credentials are stored in a managed secrets vault and
are never committed to source code.

# Part 5 — Change Management and Secure Development Policy

## SDLC
Software development follows a defined secure development lifecycle. Security
considerations are part of design and review.

## Code review
Changes to production follow a change-management process that requires peer code
review before deployment.

## Environments
Development, staging, and production are maintained as separate environments.

# Part 6 — Vulnerability Management Policy

## Testing
An independent third party performs penetration testing at least annually.
Vulnerability scanning runs continuously.

## Prioritization
Findings are prioritized by severity, using CVSS scores. Critical vulnerabilities
are remediated on a defined schedule. Specific hour-level or day-level
remediation SLAs are not fixed in this policy.

# Part 7 — Incident Response Policy

## Plan
A documented incident response plan defines severity levels, roles, and
communication paths. The cadence at which the plan is exercised is set by the
security team and is not fixed in this document.

## Breach notification
In the event of a confirmed breach affecting customer data, Acme notifies
affected customers without undue delay, and in any case within 72 hours of
confirming the breach.

# Part 8 — Business Continuity and Disaster Recovery Policy

## Backups
Backups run daily, are encrypted at rest, and are retained for 35 days. Backups
are replicated across at least two availability zones.

## Availability
The production service targets 99.9% monthly availability.

## Disaster recovery
A disaster recovery plan is documented. Specific recovery time and recovery
point objectives (RTO and RPO) are established with individual enterprise
customers and are not fixed in this policy.

# Part 9 — Logging and Monitoring Policy

## Collection
Application, infrastructure, and access logs are centrally collected. Logs are
retained for at least 12 months. Administrative actions are logged.

## Integrity
Logs are protected from tampering. Real-time alerting and anomaly-monitoring
specifics are determined operationally and are not described in this policy.

# Part 10 — Vendor and Third-Party Risk Policy

## Reviews
Acme performs security reviews of key vendors and subprocessors at least
annually.

## Agreements
Subprocessors that process customer data are bound by data protection
agreements.

# Part 11 — Data Management, Retention and Privacy Policy

## Compliance
Acme complies with the GDPR as a data processor and offers a Data Processing
Agreement (DPA) that incorporates the Standard Contractual Clauses (SCCs).

## Retention and deletion
Upon termination, customer data is deleted from production systems within
30 days. Backups age out on their normal 35-day rotation.

# Part 12 — Human Resources / Personnel Security Policy

## Screening and agreements
All employees sign confidentiality (NDA) agreements as a condition of
employment.

## Training
All employees complete security awareness training at least annually.

## Onboarding and offboarding
Employee onboarding and offboarding follow a documented checklist that includes
provisioning and revoking access.

# Part 13 — Physical and Environmental Security Policy

## Offices
The corporate office uses badge access and visitor sign-in. Because production
runs entirely in the public cloud, data-center physical security is inherited
from the cloud provider and is covered by the provider's own attestations.

# Part 14 — Company and product handbook (context, not security controls)

## What the product does
The product offers workflow builders, approval routing, dashboards, and an open
REST API. Customers integrate through API keys and webhooks. None of this is, on
its own, security-control evidence.

## Editions
Acme offers Team, Business, and Enterprise editions. Enterprise adds a named
customer success manager and priority support. Edition differences are
commercial, not security controls.

## Support hours
Standard support is available business hours, 9am to 6pm Central Time. Support
tickets are handled through a shared helpdesk. This is operational information.

## Sandbox
A sandbox environment is available for customers to test integrations before
going live. It contains only the customer's own test data.

## Company milestones
Acme was founded in 2019 and reached profitability in 2023. It has raised a
Series B round. Financial and funding details carry no compliance weight.

## Engineering culture
Engineering works in two-week sprints and practices trunk-based development.
Feature flags are used to roll changes out gradually. This describes delivery
practice, not a security control.

## Office locations
Acme has offices in Austin and a small presence in Dublin. Most staff work
remotely. Office details are operational.

## Product roadmap
Upcoming features include additional reporting widgets and more webhook event
types. Roadmap items are forward-looking and carry no compliance weight.

## Billing
Billing is monthly or annual through a third-party payment processor. Card data
is handled entirely by the payment processor and never reaches Acme systems.

## Localization
The interface is available in English, French, and German. Localization is a
product feature, not a security control.

## Data export
Customers can export their own data at any time through the API or a CSV
download. This is a product feature.

## Status communications
Planned maintenance is announced in advance by email to workspace admins. The
timing and channels for unplanned-incident updates are handled operationally.

## Additional operational notes
The team holds a weekly operations review. Runbooks exist for common operational
tasks. These are internal practices, not attested controls.

# Part 15 — Marketing boilerplate (no compliance weight)
Acme is trusted by teams who care about moving fast without breaking things.
This paragraph is marketing copy and carries no compliance weight.
