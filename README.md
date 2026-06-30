# 技擊跆拳道會 CRM System

Production-grade Club Management System for Advanced Taekwondo Club (技擊跆拳道會)

---

## Table of Contents

- [Project Overview](#project-overview)  
- [Tech Stack](#tech-stack)  
- [Architecture](#architecture)  
- [URL Structure](#url-structure)  
- [Local Development Setup](#local-development-setup)  
- [Environment Variables Reference](#environment-variables-reference)  
- [Django Apps](#django-apps)  
- [Database](#database)  
- [Deployment](#deployment)  
- [Contributing](#contributing)  
- [Changelog](#changelog)

---

## Project Overview

A comprehensive CRM and public website management system built for 技擊跆拳道會. The system covers:

| Module | Description |
| :---- | :---- |
| Member CRM | Member profiles, belt progression, multi-dojo enrollment, status management |
| Skills Tracking | Per-exam skill records, displayed on member profile page |
| Events & Exams | Unified event model (training / exam / tournament / other), attendance tracking |
| Fees & Invoicing | Annual membership fees, WeasyPrint PDF invoices, payment tracking |
| Payments | Stripe (international) \+ PayMe (HK local) dual gateway |
| Communications | In-app notifications, email, WhatsApp |
| Public Website | Public-facing marketing site — homepage, about, instructor bios, dojo info, news, black belt showcase, enrollment leads (no login required) |
| Public Website CMS | Editor-managed content (news posts, static content blocks) backing the public site |
| Match Management | Tournament and match result tracking |
| Chatbot | Phase 1 FAQ bot via Claude API \+ n8n |
| RBAC | Role-based access control across all modules |

**System Spec Blueprint:** `docs/System_Spec_Blueprint_V0.7.1.pdf`

---

## Tech Stack

| Layer | Technology |
| :---- | :---- |
| Language | Python 3.11+ |
| Framework | Django 4.x |
| Frontend | Bootstrap 5 |
| Database (dev) | SQLite 3 |
| Database (prod) | PostgreSQL 15+ |
| PDF Generation | WeasyPrint |
| Payments | Stripe SDK \+ PayMe HK API |
| Chatbot | Claude API \+ n8n (self-hosted) |
| Tunnel / Proxy | Cloudflare Tunnel |
| Dev Environment | VS Code |
| Version Control | GitHub |

---

## Architecture

```
ADV_Web_Project/
├── config/                  # Django project settings
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── dev.py           # Development overrides (SQLite)
│   │   └── prod.py          # Production overrides (PostgreSQL)
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── accounts/            # Auth, RBAC, user profiles
│   ├── members/             # Member CRM core
│   ├── dojos/               # Dojo / branch management
│   ├── events/              # Events, exams, tournaments, attendance
│   ├── skills/              # Skill records per exam
│   ├── fees/                # Annual fees, invoices
│   ├── payments/            # Stripe + PayMe gateway integration
│   ├── communications/      # In-app, email, WhatsApp
│   ├── cms/                 # Public website content management
│   ├── matches/             # Match and tournament results
│   └── chatbot/             # Chatbot config and FAQ management
│
├── templates/               # Global templates
├── static/                  # CSS, JS, images
├── media/                   # User-uploaded files
├── docs/                    # Blueprint, specs, references
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── DEBUGLOG.md
```

---

## URL Structure

### Public (no login required)

| URL | Purpose |
| :---- | :---- |
| `/` | Homepage |
| `/about/` | About the club |
| `/instructors/` | Coach/instructor bios |
| `/our-dojos/` | Dojo list |
| `/our-dojos/<slug>/` | Dojo detail (address, schedule, social links) |
| `/news/` | News & announcements |
| `/news/<slug>/` | News post detail |
| `/showcase/` | Black belt member showcase |
| `/enroll/` | Enrollment lead form |
| `/robots.txt` | SEO crawler directives |

### Authenticated (CRM — requires login + role)

| URL | Purpose |
| :---- | :---- |
| `/accounts/login/` | Login |
| `/accounts/logout/` | Logout |
| `/accounts/dashboard/` | CRM dashboard (role-scoped) |
| `/accounts/profile/` | Own profile |
| `/members/` | Member management |
| `/dojos/` | Dojo management |
| `/events/` | Events |
| `/activities/` | Activities / exams |
| `/skills/` | Skills records |
| `/fees/` | Fees |
| `/payments/` | Payments |
| `/communications/` | Communications |
| `/cms/` | CMS management |
| `/matches/` | Matches |
| `/chatbot/` | Chatbot |

**Note:** `/our-dojos/` (public) and `/dojos/` (CRM) are intentionally separate URL prefixes —
this keeps `robots.txt` rules unambiguous and avoids any routing overlap between public and
authenticated views. Same reasoning applies to `/showcase/` (public) vs. `/members/` (CRM).

---

## Local Development Setup

### Prerequisites

- Python 3.11+  
- Git  
- VS Code (recommended extensions: Python, Django, GitLens)

### 1\. Clone the Repository

```shell
git clone https://github.com/CryptoFatBeef/ADV_Web_Project.git
cd ADV_Web_Project
```

### 2\. Create Virtual Environment

```shell
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3\. Install Dependencies

```shell
pip install -r requirements/dev.txt
```

### 4\. Configure Environment Variables

```shell
cp .env.example .env
# Edit .env with your local values — never commit .env to Git
```

### 5\. Run Migrations

```shell
python manage.py migrate --settings=config.settings.dev
```

### 6\. Create Superuser

```shell
python manage.py createsuperuser --settings=config.settings.dev
```

### 7\. Start Development Server

```shell
python manage.py runserver --settings=config.settings.dev
```

Visit: `http://127.0.0.1:8000`

---

## Environment Variables Reference

Copy `.env.example` to `.env` and fill in all values. **Never commit `.env` to Git.**

| Variable | Required | Description | Example |
| :---- | :---- | :---- | :---- |
| `DJANGO_SECRET_KEY` | ✅ | Django secret key | `django-insecure-xxxxx` |
| `DJANGO_DEBUG` | ✅ | Debug mode | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | ✅ | Allowed hostnames | `localhost,127.0.0.1` |
| `DATABASE_URL` | Prod only | PostgreSQL connection string | `postgres://user:pass@host/db` |
| `STRIPE_PUBLIC_KEY` | ✅ | Stripe publishable key | `pk_test_xxxxx` |
| `STRIPE_SECRET_KEY` | ✅ | Stripe secret key | `sk_test_xxxxx` |
| `STRIPE_WEBHOOK_SECRET` | ✅ | Stripe webhook signing secret | `whsec_xxxxx` |
| `PAYME_MERCHANT_ID` | ✅ | PayMe merchant ID | `xxxxx` |
| `PAYME_API_KEY` | ✅ | PayMe API key | `xxxxx` |
| `ANTHROPIC_API_KEY` | ✅ | Claude API key (chatbot) | `sk-ant-xxxxx` |
| `EMAIL_HOST` | ✅ | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | ✅ | SMTP port | `587` |
| `EMAIL_HOST_USER` | ✅ | SMTP username | `no-reply@advancedtkd.net` |
| `EMAIL_HOST_PASSWORD` | ✅ | SMTP password / app password | `xxxxx` |
| `WHATSAPP_API_TOKEN` | ✅ | WhatsApp Business API token | `xxxxx` |
| `WHATSAPP_PHONE_NUMBER_ID` | ✅ | WhatsApp phone number ID | `xxxxx` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Prod only | Cloudflare Tunnel token | `xxxxx` |
| `SITE_DOMAIN` | Recommended | Production domain, used in JSON-LD structured data, sitemap, and robots.txt | `www.example.com` |
| `SITE_FACEBOOK_URL` | Optional | Club Facebook page URL — omitted from footer/schema if blank | `https://facebook.com/...` |
| `SITE_INSTAGRAM_URL` | Optional | Club Instagram page URL — omitted from footer/schema if blank | `https://instagram.com/...` |

---

## Django Apps

| App | Responsibility |
| :---- | :---- |
| `accounts` | Custom user model, authentication, RBAC roles & permissions |
| `members` | Member profiles, belt levels, status (Active/Inactive/Suspended/Graduated), MemberDojoEnrollment |
| `dojos` | Dojo / branch profiles, locations, coaches |
| `events` | Event model (event\_type field), attendance for classes and exams |
| `skills` | SkillRecord per exam — independent model, SQLite-compatible (no ArrayField) |
| `fees` | Annual fee setup, invoice generation (WeasyPrint) |
| `payments` | Stripe \+ PayMe integration, payment records, webhook handlers |
| `communications` | Notification hub — in-app, email, WhatsApp dispatch |
| `cms` | Public website content blocks, news (`NewsPost`), announcements |
| `matches` | Tournament brackets, match results, competitor records |
| `chatbot` | FAQ entries, chatbot config, Claude API \+ n8n webhook bridge |
| `public` | Public-facing marketing site — no models of its own; reads data from `dojos`, `cms`, `members` to render homepage, about, instructor bios, dojo listings, news, and black belt showcase |
| `enrollment` | Public enrollment lead capture (`EnrollmentLead` model with mandatory PDPO consent field) — no login required |

---

## Database

- **Development:** SQLite (zero-config, file at `db.sqlite3`)  
- **Production:** PostgreSQL 15+  
- **Rule:** No PostgreSQL-specific model fields (e.g. `ArrayField`) — all models must be SQLite-compatible

### Migration Workflow

```shell
# Create migrations after model changes
python manage.py makemigrations --settings=config.settings.dev

# Apply migrations
python manage.py migrate --settings=config.settings.dev

# Never manually ALTER TABLE — always use migrations
```

---

## Deployment

Deployment uses Cloudflare Tunnel — no public port exposure required.

Refer to `docs/deployment_guide.md` (TBD) for full production setup steps.

---

## Contributing

1. Branch naming: `feature/<feature-name>`, `fix/<issue>`, `docs/<topic>`  
2. Always work on a branch — never commit directly to `main`  
3. Write migration files for every model change  
4. Log significant bugs and fixes in `DEBUGLOG.md`  
5. Keep `.env` out of Git — update `.env.example` when adding new variables

---

## Changelog

| Version | Date | Notes |
| :---- | :---- | :---- |
| 0.3.1 | 2026-06-30 | Public website split — `/` now serves a public homepage; CRM moved to `/accounts/dashboard/`. New `public` and `enrollment` apps. SEO foundation (robots.txt, JSON-LD, OG tags). Fixed a CRM-shell leak on the login/403/404 pages. |
| 0.3.0 | 2026-06-29 | Frontend layer complete — RBAC template tags, role-scoped dashboard, sidebar shell, all 12 apps' views/URLs/templates wired |
| 0.2.0 | 2026-06-29 | Data layer complete — all 12 apps scaffolded (models, admin, migrations) |
| 0.1.0 | 2026-06-22 | Project initialised — Django scaffold, 12 app skeletons, settings split, Celery/Redis, CI workflow |

