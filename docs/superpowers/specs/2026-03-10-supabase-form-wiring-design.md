# Design: Supabase Form Wiring (Part A)
**Date:** 2026-03-10
**Project:** C21 Alliance Properties Website
**Scope:** Wire contact form + blog subscribe form to Supabase; deploy Edge Functions

---

## Current State

| Piece | Status |
|---|---|
| Contact form JS (`main.js`) | ✅ Already calls `handle-contact-form` Edge Function |
| `handle-contact-form` Edge Function | ✅ Written, not yet deployed |
| `handle-subscription` Edge Function | ✅ Written, not yet deployed |
| Blog email strip JS | ❌ Button does nothing — no JS |
| Env vars on Supabase | ❌ Not set |

---

## What This Build Covers

### 1. Blog Subscribe Form (`blog/index.html`)

Add inline JS to the `.email-strip` section:
- On "Subscribe Free" click: validate email, POST to `handle-subscription` Edge Function
- Payload: `{ email, source: 'tarrent_blog' }`
- Success: replace button text with "You're in ✓", disable input
- Error: show inline error message below the form
- Duplicate email: Edge Function uses `upsert` — silently succeeds (no error shown)

**No new files.** JS goes inline in `blog/index.html` below the email strip markup.

### 2. Edge Function Deployment

Both functions deployed via Supabase CLI:
```
supabase functions deploy handle-contact-form
supabase functions deploy handle-subscription
```

### 3. Environment Variables

Three secrets set via CLI:
```
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<from Supabase dashboard>
supabase secrets set RESEND_API_KEY=<from Resend dashboard>
supabase secrets set NOTIFICATION_EMAIL=SarenaSSmith@gmail.com
```

---

## Data Flow

```
Blog email strip
  → POST /functions/v1/handle-subscription
    → upsert into subscribers table
    → Resend email to SarenaSSmith@gmail.com
    → return { success: true }
  → UI shows "You're in ✓"

Contact form (index.html)
  → POST /functions/v1/handle-contact-form   ← already wired
    → insert into leads table
    → Resend email to SarenaSSmith@gmail.com
    → return { success: true }
  → UI shows success state                   ← already wired
```

---

## What Is Not Changing
- Contact form JS in `main.js` — already correct
- `handle-contact-form` Edge Function code — already correct
- `handle-subscription` Edge Function code — already correct
- Admin panel — no changes needed; it already reads from both tables
- RLS policies — already set correctly (anon can INSERT, auth reads)

---

## Success Criteria
- Submitting the contact form creates a row in `leads` and triggers a Resend email
- Subscribing on the blog creates a row in `subscribers` and triggers a Resend email
- Both records appear in the admin panel immediately
- Blog form shows success/error state inline without page reload
- Duplicate blog email subscriptions silently succeed (no error shown to user)
