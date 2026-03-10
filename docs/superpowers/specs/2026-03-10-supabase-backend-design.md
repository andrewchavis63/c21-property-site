# Supabase Backend Design
**Date:** 2026-03-10
**Project:** C21 Alliance Properties Website + TAR(RENT) Blog
**Status:** Approved

---

## Overview

Supabase serves as the central backend for both the C21 Alliance Properties website and the TAR(RENT) Blog. It handles all inbound leads, subscriber captures, team CRM, and automated notifications — while remaining the data layer Claude queries to generate personalized, context-aware responses for the team.

The website stays 100% static (pure HTML/CSS/JS). All logic lives inside Supabase.

---

## Architecture

```
[Website / TAR(RENT) Blog]
  ├── Contact Form        ──→  Supabase Edge Function: handle-contact-form
  ├── Blog Subscribe      ──→  Supabase Edge Function: handle-subscription
  ├── Portal Waitlist     ──→  Supabase Edge Function: handle-contact-form (source: portal_waitlist)
  └── Team Admin Page (/admin) ──→  Supabase Auth + Database

[Supabase Edge Functions]
  ├── Save lead/subscriber to database
  ├── Send email notification via Resend (free tier — 3,000/month)
  └── Send SMS via Twilio (stubbed — activate at launch)

[Supabase Database]
  ├── leads          (all inbound contact/waitlist submissions)
  ├── subscribers    (blog/newsletter signups)
  ├── contacts       (full CRM records — owners, tenants, prospects)
  ├── contact_people (family members and relationships)
  └── contact_events (birthdays, anniversaries, key dates)

[Claude via Supabase MCP Plugin]
  └── Query any table, surface upcoming dates, draft personalized responses
```

---

## Data Model

### `leads`
| field | type | notes |
|---|---|---|
| id | uuid | auto-generated |
| name | text | |
| email | text | |
| phone | text | optional |
| message | text | |
| source | text | `contact_form`, `portal_waitlist`, `tarrent_blog` |
| status | text | `new` → `contacted` → `follow_up` → `converted` |
| created_at | timestamp | auto |

### `subscribers`
| field | type | notes |
|---|---|---|
| id | uuid | auto-generated |
| email | text | unique |
| name | text | optional |
| source | text | `c21_website`, `tarrent_blog` |
| subscribed_at | timestamp | auto |
| active | boolean | false on unsubscribe |

### `contacts`
| field | type | notes |
|---|---|---|
| id | uuid | auto-generated |
| lead_id | uuid | links to originating lead |
| name | text | |
| email | text | |
| phone | text | |
| type | text | `owner`, `tenant`, `prospect` |
| property_address | text | |
| notes | text | freeform running notes |
| assigned_to | text | Starlyn / Sarena / Andrew |
| created_at | timestamp | auto |

### `contact_people`
| field | type | notes |
|---|---|---|
| id | uuid | auto-generated |
| contact_id | uuid | FK → contacts |
| name | text | e.g. "Maria" |
| relationship | text | `spouse`, `child`, `parent`, `other` |
| birthday | date | optional |

### `contact_events`
| field | type | notes |
|---|---|---|
| id | uuid | auto-generated |
| contact_id | uuid | FK → contacts |
| label | text | e.g. "Wedding Anniversary", "Move-in Date" |
| date | date | |
| recurs_yearly | boolean | true for birthdays/anniversaries |

---

## Notifications

### Email — Resend
- Free tier: 3,000 emails/month
- Recipient: SarenaSSmith@gmail.com
- Triggered on every new lead submission
- Includes: name, phone, message, source, timestamp — formatted for action, not raw data

### SMS — Twilio
- **Status: Stubbed — activate at launch**
- Short alert format: *"New lead — Tom Harris, (817) 555-0192. Check email for details."*
- Designated team phone number(s) set via environment variable
- Cost: ~$1/month per number + $0.0079/text

---

## Team Admin Page (`/admin`)

A private, auth-gated page on the C21 site. Access limited to Starlyn, Sarena, and Andrew via Supabase Auth.

### Views
- **Leads Queue** — all submissions, newest first, status badges
- **Subscribers List** — tagged by source (C21 vs TAR(RENT))
- **Contacts / CRM** — full profiles with notes, family details, property info, assigned team member
- **Upcoming Dates Sidebar** — birthdays, anniversaries, key dates in the next 30 days

### Actions
- Update lead status (one click)
- Promote lead → contact record
- Add family members and personal details
- Log notes after every interaction
- Assign contact to team member

### Design
- Fully on-brand: dark background (`#1c1c1e`), Relentless Gold (`#beaf87`) accents
- Headings: Playfair Display | Body: Inter
- Consistent with the visual language established across the C21 website

---

## Claude Integration

The Supabase MCP plugin is already installed and enabled in Claude Code. Once the Supabase account is connected and authenticated, Claude can:

- Query leads, contacts, subscribers by name, date, status, or source
- Surface upcoming personal dates before the team reaches out
- Draft personalized, context-aware responses using stored CRM data
- Flag follow-ups that have gone cold

The team interacts with the data primarily through Claude — not by logging into Supabase directly.

---

## Future: Owner/Tenant Portal

Security model and document access controls to be defined separately before implementation. Supabase Auth and Row Level Security (RLS) are already part of the stack and will serve as the foundation when ready.

---

## Deferred / Out of Scope for Launch

- Twilio SMS (stubbed, activate at launch)
- Owner/Tenant document portal (security design pending)
- TAR(RENT) Blog integration into C21 site (partitioned until ready)
