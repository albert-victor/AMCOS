# Mkuu wa Mkoa - Enterprise Cooperative Management System

Multi-Tenant SaaS Cooperative Management System built with Python Django + MySQL.

## Features

- Multi-Tenant Architecture (SACCOs, AMCOS, VICOBA, Credit Unions)
- Role-Based Access Control (Super Admin, Cooperative Admin, Accountant, Loan Officer, Secretary, Chairperson, Auditor, Member)
- Member Management with KYC
- Savings Management (Voluntary, Mandatory, Fixed Deposit)
- Loan Management with Full Workflow
- Share Management with Dividends
- Payments (M-Pesa, Tigo Pesa, Airtel Money, Bank, Cash)
- Double-Entry Accounting (Trial Balance, Income Statement, Balance Sheet)
- Governance (Meetings, Minutes, Elections, Voting)
- Reporting (Member, Savings, Loan, Payment Reports)
- Notifications (In-App, SMS, Email)
- Audit Trails & Compliance
- Fraud Detection & Alerts

## Tech Stack

- **Backend:** Python Django 6.0
- **Database:** MySQL (Database: MKUU_WA_MKOA)
- **Frontend:** HTML + CSS + JavaScript (TailwindCSS-like custom CSS)

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create MySQL database named `MKUU_WA_MKOA`
4. Copy `.env.example` to `.env` and configure
5. Run migrations: `python manage.py migrate`
6. Create superuser: `python manage.py createsuperuser`
7. Run server: `python manage.py runserver`

## Project Structure

```
mkukuwa_mkoa/
├── manage.py
├── requirements.txt
├── mkukuwa_mkoa/           # Project settings
├── apps/
│   ├── core/               # Base models, middleware
│   ├── authentication/     # Auth, OTP, sessions
│   ├── cooperative/        # Cooperative setup
│   ├── members/            # Member management, KYC
│   ├── payments/           # Payment processing
│   ├── savings/            # Savings accounts
│   ├── shares/             # Share management
│   ├── loans/              # Loan management
│   ├── accounting/         # Double-entry accounting
│   ├── governance/         # Meetings, elections
│   ├── reporting/          # Reports
│   ├── audit/              # Audit trails, compliance
│   └── notifications/      # Notifications, SMS, email
├── templates/              # HTML templates
└── static/                 # CSS, JS
```

## Default Roles

1. **Super Admin** - System-wide management
2. **Cooperative Admin** - Cooperative operations
3. **Accountant** - Financial management
4. **Loan Officer** - Loan processing
5. **Secretary** - Governance & meetings
6. **Chairperson** - Approvals
7. **Auditor** - Compliance & audit
8. **Member** - Self-service portal
