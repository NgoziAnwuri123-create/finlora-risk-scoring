# Finlora — Project Requirements

## 1. Overview

Finlora is a fintech/banking platform serving both **retail (individual) customers** and **small businesses (SMBs)**. It provides core banking functionality (accounts, payments, card issuing) alongside budgeting, lending, and financial insight tools, delivered initially as a **web application**.

## 2. Goals

- Provide a unified platform where individuals and small businesses can hold funds, move money, and access credit.
- Give users visibility and control over their finances through budgeting and analytics.
- Establish a secure, compliant foundation suitable for regulated financial services.
- Launch with a web application; architect for future mobile and admin-portal expansion.

## 3. Target Users

| Segment | Description | Primary Needs |
|---|---|---|
| Retail customers | Individuals managing personal finances | Everyday spending, savings, budgeting, P2P transfers |
| SMB customers | Small business owners/operators | Business accounts, payments to vendors/employees, cash flow visibility, credit access |

Both segments share the core platform; SMB accounts require additional business-entity onboarding (KYB) versus individual onboarding (KYC).

## 4. Scope — Core Capabilities

### 4.1 Accounts & Transactions
- Open one or more accounts per user (personal checking/savings-equivalent; business operating account for SMBs).
- Real-time balance display.
- Transaction history with search, filtering (date range, amount, category, counterparty), and export (CSV/PDF).
- Account statements (monthly, on-demand generation).
- Multi-account support per user/business (e.g., savings + checking, or multiple business accounts).
- Account-level permissions for SMBs (owner vs. authorized user/employee access).

### 4.2 Payments & Transfers
- Internal transfers between a user's own Finlora accounts.
- Peer-to-peer (P2P) transfers between Finlora users.
- External transfers via ACH (and/or wire for larger amounts) to outside bank accounts.
- Bill pay (scheduled and one-time payments to payees).
- Recurring/scheduled payments and transfers.
- Payment status tracking (pending, processing, completed, failed, returned).
- Transaction limits configurable by account type/risk tier (daily/monthly caps).

### 4.3 Card Issuing
- Issue virtual debit cards immediately upon account opening.
- Issue physical debit cards (mailed) on request.
- Card controls: freeze/unfreeze, set spending limits, merchant-category restrictions, ATM withdrawal limits.
- Real-time transaction notifications for card usage.
- Card replacement/reissue flow (lost, stolen, damaged).
- Support for both consumer and business card programs (including potential for employee sub-cards under an SMB account).

### 4.4 Budgeting, Lending & Insights
- Automatic transaction categorization (merchant/category tagging).
- Budget creation by category with spend tracking against budget.
- Spending insights/dashboards (trends over time, category breakdowns, cash flow for SMBs).
- Savings goals (target amount, target date, progress tracking) for retail users.
- Lending products:
  - Personal line of credit / small personal loans for retail users.
  - Business line of credit / working capital loans for SMB users.
  - Credit application, underwriting decision flow, disbursement, and repayment scheduling.
  - Loan/credit account statements and payment history.
- Credit-building features for retail users (e.g., reporting on-time payments), if applicable to business model.

## 5. Platform Scope

- **Launch platform:** Responsive web application (desktop and mobile browser support).
- **Out of scope for v1** (explicitly deferred, but architecture should not preclude later addition):
  - Native iOS/Android mobile apps.
  - Internal admin/back-office portal for ops, compliance, and support staff (a v1 platform still needs *some* internal tooling for compliance/support operations — see Section 9 — but a full-featured portal is deferred).

## 6. Functional Requirements Summary

1. Users can register and complete identity verification (KYC for individuals, KYB for businesses) before account activation.
2. Users can open, view, and manage one or more accounts.
3. Users can view real-time balances and transaction history.
4. Users can initiate internal transfers, P2P transfers, ACH/wire transfers, and bill payments.
5. Users can request and manage virtual and physical debit cards, including setting controls and freezing cards.
6. Users can categorize transactions, create budgets, and track spending against budgets.
7. Users can set and track savings goals.
8. Eligible users can apply for lending products and manage repayment.
9. Businesses can grant/restrict account access to authorized users (employees) with role-based permissions.
10. The system generates account statements and supports transaction export.
11. The system sends notifications (email/in-app, and push if mobile is later added) for key events: transactions, payment status changes, low balance, budget threshold reached, loan payment due.

## 7. Non-Functional Requirements

### 7.1 Security
- End-to-end encryption of data in transit (TLS 1.2+) and at rest.
- Multi-factor authentication (MFA) required for login and sensitive actions (e.g., adding a payee, large transfers).
- Role-based access control (RBAC) for SMB multi-user accounts.
- Secure handling of PII and financial data (tokenization of sensitive card/account data; no raw PAN storage where avoidable — use a PCI-compliant processor/vault).
- Fraud detection/monitoring on transactions and card usage.
- Session management: automatic timeout, device/session visibility, ability to revoke sessions.
- Audit logging of all account, payment, and permission-change actions.

### 7.2 Compliance & Regulatory
- KYC/KYB identity verification workflows meeting applicable regulatory requirements (e.g., BSA/AML in the US, or equivalent in target jurisdiction).
- AML transaction monitoring and suspicious activity reporting capability.
- PCI DSS compliance for card data handling (likely via a licensed card-issuing/processing partner rather than self-issuing).
- Partnership with a chartered bank or licensed financial institution for deposit accounts and lending, as direct banking/lending licenses are typically required (Banking-as-a-Service model) — **to be confirmed with legal/compliance before technical design finalizes**.
- Data retention and reporting requirements per relevant financial regulations.
- Terms of service, privacy policy, and consumer disclosures (e.g., Reg E for electronic transfers, if applicable).

### 7.3 Performance & Reliability
- Balance and transaction data must reflect near-real-time state (target: <5s latency from transaction event to visibility).
- Platform target uptime: 99.9% for core banking functions (account access, payments).
- System must handle peak load (e.g., end-of-month bill pay, payroll days for SMBs) without degradation.

### 7.4 Usability & Accessibility
- Responsive design supporting desktop and mobile browser widths.
- WCAG 2.1 AA accessibility compliance.
- Clear, jargon-free language for financial actions and disclosures.

### 7.5 Auditability & Observability
- Full audit trail for financial transactions, account changes, and permission changes.
- Application monitoring/alerting for payment processing failures and system errors.

## 8. Data Model (High-Level Sketch)

Key entities (to be refined during technical design):

- **User** (individual) — identity, credentials, KYC status, linked accounts.
- **Business** — entity info, KYB status, authorized users (linked to User with roles).
- **Account** — type (personal/business), balance, status, owner(s).
- **Transaction** — amount, direction, status, category, counterparty, linked account, linked payment/transfer.
- **Card** — type (virtual/physical), linked account, status, controls/limits.
- **Payment/Transfer** — type (internal, P2P, ACH, wire, bill pay), status, schedule (if recurring), source/destination.
- **Budget** — category, period, limit, linked account/user.
- **SavingsGoal** — target amount, target date, progress, linked account.
- **LoanAccount** — principal, rate, term, status, repayment schedule, linked account.
- **AuditLog** — actor, action, entity affected, timestamp.

## 9. Open Questions / Decisions Needed

- **Banking partner strategy:** Will Finlora operate under a Banking-as-a-Service (BaaS) partnership with a chartered bank/card issuer/lending partner, or pursue direct licensing? This materially affects architecture (integration with partner APIs) and compliance scope.
- **Target jurisdiction(s):** US-only at launch, or multi-region? Determines applicable regulatory framework (BSA/AML, Reg E, state money transmitter licenses, etc.).
- **Internal operations tooling for v1:** Even without a full admin portal, compliance/support staff will need some minimal internal tooling (e.g., view account/KYC status, freeze accounts, review flagged transactions) — scope this minimally for launch.
- **Lending underwriting approach:** Build in-house underwriting/risk models, or integrate a third-party underwriting/credit-decisioning provider?
- **Tech stack:** Not yet specified — to be determined in technical design phase, informed by the BaaS/partner decision above.
- **Monetization model:** Interchange revenue, subscription/fees, lending interest, or combination — affects prioritization of features.

## 10. Success Metrics (Draft)

- Number of active accounts (retail + SMB).
- Transaction volume and value processed.
- Card activation and usage rate.
- Budgeting/insights feature adoption (% of users with an active budget or goal).
- Loan/credit product adoption and repayment performance.
- Platform uptime and payment success rate.
- Customer support ticket volume related to payment/account issues (lower is better).
