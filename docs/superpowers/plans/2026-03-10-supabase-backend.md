# Supabase Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Supabase as the backend for C21 Alliance Properties + TAR(RENT) Blog — capturing leads, subscribers, and CRM data, with email notifications and a private team admin page.

**Architecture:** Supabase Edge Functions receive form submissions, persist data to Postgres, and fire Resend email notifications. The website stays 100% static. The team admin page uses Supabase Auth + vanilla JS to manage leads and contacts. Claude queries data through the Supabase MCP plugin.

**Tech Stack:** Supabase (Postgres + Edge Functions + Auth + RLS), Deno (Edge Function runtime), Resend (email), Twilio (SMS — stubbed), Vanilla JS/HTML/CSS (admin page + site forms)

---

## File Map

### New files
| Path | Responsibility |
|---|---|
| `supabase/migrations/20260310000001_initial_schema.sql` | All table definitions + RLS policies |
| `supabase/functions/handle-contact-form/index.ts` | Receive contact/waitlist form POST, save lead, send email, stub SMS |
| `supabase/functions/handle-subscription/index.ts` | Receive subscribe POST, save subscriber, send confirmation email |
| `supabase/.env.example` | Required env var template for team reference |
| `admin/index.html` | Private team admin page (auth-gated) |
| `admin/css/admin.css` | Admin styles — on-brand with C21 site |
| `admin/js/admin.js` | Auth, leads queue, subscribers, CRM, upcoming dates |

### Modified files
| Path | Change |
|---|---|
| `js/main.js` line 237 | Replace Formspree URL with Supabase Edge Function URL |

---

## Chunk 1: Supabase Project Setup + Database Schema

### Task 1: Initialize Supabase project locally

**Files:**
- Create: `supabase/` (directory, managed by CLI)

- [ ] **Step 1: Open a new terminal** (so `supabase` is in PATH from the install earlier)

- [ ] **Step 2: Initialize Supabase in the project root**

```bash
cd C:\Users\achav\c21-property-site
supabase init
```

Expected: Creates `supabase/` directory with `config.toml`

- [ ] **Step 3: Log in to Supabase CLI**

```bash
supabase login
```

Follow the browser prompt to authenticate with your Supabase account.

- [ ] **Step 4: Link to your Supabase project**

After creating a project at supabase.com (free tier), grab the project reference ID from the project URL (`https://supabase.com/dashboard/project/<ref-id>`), then:

```bash
supabase link --project-ref <your-project-ref-id>
```

- [ ] **Step 5: Commit**

```bash
git add supabase/
git commit -m "chore: initialize Supabase project"
```

---

### Task 2: Write the database migration

**Files:**
- Create: `supabase/migrations/20260310000001_initial_schema.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- supabase/migrations/20260310000001_initial_schema.sql

-- ============================================================
-- LEADS — every inbound contact/waitlist submission
-- ============================================================
create table leads (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  email       text not null,
  phone       text,
  message     text,
  source      text not null default 'contact_form',
  status      text not null default 'new'
              check (status in ('new','contacted','follow_up','converted')),
  created_at  timestamptz not null default now()
);

-- ============================================================
-- SUBSCRIBERS — blog/newsletter signups
-- ============================================================
create table subscribers (
  id             uuid primary key default gen_random_uuid(),
  email          text not null unique,
  name           text,
  source         text not null default 'c21_website',
  subscribed_at  timestamptz not null default now(),
  active         boolean not null default true
);

-- ============================================================
-- CONTACTS — full CRM records (promoted from leads)
-- ============================================================
create table contacts (
  id               uuid primary key default gen_random_uuid(),
  lead_id          uuid references leads(id),
  name             text not null,
  email            text,
  phone            text,
  type             text not null default 'prospect'
                   check (type in ('owner','tenant','prospect')),
  property_address text,
  notes            text,
  assigned_to      text,
  created_at       timestamptz not null default now()
);

-- ============================================================
-- CONTACT_PEOPLE — family members tied to a contact
-- ============================================================
create table contact_people (
  id           uuid primary key default gen_random_uuid(),
  contact_id   uuid not null references contacts(id) on delete cascade,
  name         text not null,
  relationship text not null default 'other'
               check (relationship in ('spouse','child','parent','other')),
  birthday     date
);

-- ============================================================
-- CONTACT_EVENTS — birthdays, anniversaries, key dates
-- ============================================================
create table contact_events (
  id            uuid primary key default gen_random_uuid(),
  contact_id    uuid not null references contacts(id) on delete cascade,
  label         text not null,
  date          date not null,
  recurs_yearly boolean not null default true
);

-- ============================================================
-- ROW LEVEL SECURITY
-- Public can INSERT into leads and subscribers (forms)
-- Only authenticated team members can SELECT/UPDATE/DELETE
-- ============================================================
alter table leads           enable row level security;
alter table subscribers     enable row level security;
alter table contacts        enable row level security;
alter table contact_people  enable row level security;
alter table contact_events  enable row level security;

-- leads: anyone can insert (contact form), only auth users can read/edit
create policy "public insert leads"
  on leads for insert to anon with check (true);

create policy "team read leads"
  on leads for select to authenticated using (true);

create policy "team update leads"
  on leads for update to authenticated using (true);

-- subscribers: anyone can insert, only auth users can read/edit
create policy "public insert subscribers"
  on subscribers for insert to anon with check (true);

create policy "team read subscribers"
  on subscribers for select to authenticated using (true);

-- contacts + related: auth users only
create policy "team all contacts"
  on contacts for all to authenticated using (true);

create policy "team all contact_people"
  on contact_people for all to authenticated using (true);

create policy "team all contact_events"
  on contact_events for all to authenticated using (true);
```

- [ ] **Step 2: Push migration to Supabase**

```bash
supabase db push
```

Expected: Migration runs without errors. Tables visible in Supabase dashboard → Table Editor.

- [ ] **Step 3: Verify in dashboard**

Open `https://supabase.com/dashboard/project/<ref-id>/editor` and confirm all 5 tables exist with correct columns.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/
git commit -m "feat: add initial database schema with RLS"
```

---

### Task 3: Create team auth accounts

- [ ] **Step 1: Go to Supabase dashboard → Authentication → Users**

- [ ] **Step 2: Invite each team member** using "Invite User":
  - Starlyn Smith (her email)
  - Sarena Smith — SarenaSSmith@gmail.com
  - Andrew Chavis (his email)

Each will receive a magic link to set their password.

- [ ] **Step 3: Confirm all three users appear in the Users list**

---

### Task 4: Create env example file

**Files:**
- Create: `supabase/.env.example`

- [ ] **Step 1: Create the file**

```bash
# supabase/.env.example
# Copy to supabase/.env and fill in values
# NEVER commit supabase/.env to git

SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
RESEND_API_KEY=<your-resend-api-key>
NOTIFICATION_EMAIL=SarenaSSmith@gmail.com

# Twilio (stubbed — fill in at launch)
# TWILIO_ACCOUNT_SID=
# TWILIO_AUTH_TOKEN=
# TWILIO_FROM_NUMBER=
# TWILIO_TO_NUMBERS=+18175550001,+18175550002
```

- [ ] **Step 2: Add .env to .gitignore**

```bash
echo "supabase/.env" >> .gitignore
echo ".env" >> .gitignore
```

- [ ] **Step 3: Commit**

```bash
git add supabase/.env.example .gitignore
git commit -m "chore: add env example and gitignore"
```

---

## Chunk 2: Edge Functions

### Task 5: handle-contact-form Edge Function

**Files:**
- Create: `supabase/functions/handle-contact-form/index.ts`

- [ ] **Step 1: Create the function directory and file**

```typescript
// supabase/functions/handle-contact-form/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { name, email, phone, message, source } = await req.json()

    if (!name || !email) {
      return new Response(
        JSON.stringify({ error: 'Name and email are required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Save lead to database
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { error: dbError } = await supabase
      .from('leads')
      .insert({
        name,
        email,
        phone: phone || null,
        message: message || null,
        source: source || 'contact_form',
        status: 'new',
      })

    if (dbError) throw new Error(dbError.message)

    // Send email notification via Resend
    const emailRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('RESEND_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'C21 Alliance Leads <leads@notifications.c21allianceproperties.com>',
        to: [Deno.env.get('NOTIFICATION_EMAIL') ?? 'SarenaSSmith@gmail.com'],
        subject: `New Lead: ${name}`,
        html: `
          <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#1c1c1e;color:#f8f7f4;padding:32px;border-radius:8px;">
            <h2 style="color:#beaf87;margin:0 0 24px;font-family:Georgia,serif;">New Lead — C21 Alliance Properties</h2>
            <table style="width:100%;border-collapse:collapse;">
              <tr><td style="padding:8px 0;color:#c4c4c5;width:120px;">Name</td><td style="padding:8px 0;"><strong>${name}</strong></td></tr>
              <tr><td style="padding:8px 0;color:#c4c4c5;">Email</td><td style="padding:8px 0;">${email}</td></tr>
              <tr><td style="padding:8px 0;color:#c4c4c5;">Phone</td><td style="padding:8px 0;">${phone || '—'}</td></tr>
              <tr><td style="padding:8px 0;color:#c4c4c5;">Source</td><td style="padding:8px 0;">${source || 'contact_form'}</td></tr>
              <tr><td style="padding:8px 0;color:#c4c4c5;vertical-align:top;">Message</td><td style="padding:8px 0;">${message || '—'}</td></tr>
            </table>
          </div>
        `,
      }),
    })

    if (!emailRes.ok) {
      console.error('Resend error:', await emailRes.text())
      // Don't fail the request if email fails — lead is already saved
    }

    // ── SMS via Twilio (stubbed — uncomment at launch) ──────────────────
    // const twilioSid   = Deno.env.get('TWILIO_ACCOUNT_SID')
    // const twilioToken = Deno.env.get('TWILIO_AUTH_TOKEN')
    // const toNumbers   = (Deno.env.get('TWILIO_TO_NUMBERS') ?? '').split(',')
    // for (const to of toNumbers) {
    //   await fetch(`https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`, {
    //     method: 'POST',
    //     headers: {
    //       'Authorization': `Basic ${btoa(`${twilioSid}:${twilioToken}`)}`,
    //       'Content-Type': 'application/x-www-form-urlencoded',
    //     },
    //     body: new URLSearchParams({
    //       From: Deno.env.get('TWILIO_FROM_NUMBER') ?? '',
    //       To: to.trim(),
    //       Body: `New lead — ${name}, ${phone || email}. Check email for details.`,
    //     }),
    //   })
    // }
    // ────────────────────────────────────────────────────────────────────

    return new Response(
      JSON.stringify({ success: true }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

- [ ] **Step 2: Deploy the function**

```bash
supabase functions deploy handle-contact-form --no-verify-jwt
```

Expected: Function deployed. URL shown: `https://<ref>.supabase.co/functions/v1/handle-contact-form`

- [ ] **Step 3: Set environment secrets**

```bash
supabase secrets set RESEND_API_KEY=<your-resend-key>
supabase secrets set NOTIFICATION_EMAIL=SarenaSSmith@gmail.com
```

Note: `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are automatically available inside Edge Functions — no need to set them manually.

- [ ] **Step 4: Test manually with curl**

```bash
curl -X POST https://<ref>.supabase.co/functions/v1/handle-contact-form \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Lead","email":"test@example.com","phone":"8175550001","message":"Hello from test","source":"contact_form"}'
```

Expected response: `{"success":true}`

- [ ] **Step 5: Verify in Supabase dashboard** → Table Editor → leads → confirm test row exists

- [ ] **Step 6: Verify email received** at SarenaSSmith@gmail.com

- [ ] **Step 7: Commit**

```bash
git add supabase/functions/handle-contact-form/
git commit -m "feat: add handle-contact-form Edge Function with Resend + Twilio stub"
```

---

### Task 6: handle-subscription Edge Function

**Files:**
- Create: `supabase/functions/handle-subscription/index.ts`

- [ ] **Step 1: Create the function file**

```typescript
// supabase/functions/handle-subscription/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { email, name, source } = await req.json()

    if (!email) {
      return new Response(
        JSON.stringify({ error: 'Email is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Upsert — re-subscribes if they previously unsubscribed
    const { error: dbError } = await supabase
      .from('subscribers')
      .upsert(
        { email, name: name || null, source: source || 'c21_website', active: true },
        { onConflict: 'email' }
      )

    if (dbError) throw new Error(dbError.message)

    // Notify team
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('RESEND_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'C21 Alliance Leads <leads@notifications.c21allianceproperties.com>',
        to: [Deno.env.get('NOTIFICATION_EMAIL') ?? 'SarenaSSmith@gmail.com'],
        subject: `New Subscriber: ${email}`,
        html: `
          <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#1c1c1e;color:#f8f7f4;padding:32px;border-radius:8px;">
            <h2 style="color:#beaf87;margin:0 0 24px;font-family:Georgia,serif;">New Subscriber</h2>
            <p><strong>Email:</strong> ${email}</p>
            <p><strong>Name:</strong> ${name || '—'}</p>
            <p><strong>Source:</strong> ${source || 'c21_website'}</p>
          </div>
        `,
      }),
    })

    return new Response(
      JSON.stringify({ success: true }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

- [ ] **Step 2: Deploy**

```bash
supabase functions deploy handle-subscription --no-verify-jwt
```

- [ ] **Step 3: Test manually**

```bash
curl -X POST https://<ref>.supabase.co/functions/v1/handle-subscription \
  -H "Content-Type: application/json" \
  -d '{"email":"test@tarrent.com","name":"Blog Reader","source":"tarrent_blog"}'
```

Expected: `{"success":true}` — row in subscribers table, email notification received.

- [ ] **Step 4: Commit**

```bash
git add supabase/functions/handle-subscription/
git commit -m "feat: add handle-subscription Edge Function"
```

---

## Chunk 3: Website Form Integration

### Task 7: Replace Formspree with Supabase Edge Function

**Files:**
- Modify: `js/main.js` line 237

- [ ] **Step 1: Update the fetch URL and payload in main.js**

Find (line ~237):
```javascript
const response = await fetch('https://formspree.io/f/xlgwkdkn', {
  method: 'POST',
  headers: { 'Accept': 'application/json' },
  body: new FormData(form)
});
```

Replace with:
```javascript
const response = await fetch('https://<ref>.supabase.co/functions/v1/handle-contact-form', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name:    form.querySelector('[name="name"]').value,
    email:   form.querySelector('[name="email"]').value,
    phone:   form.querySelector('[name="phone"]')?.value || '',
    message: form.querySelector('[name="message"]').value,
    source:  'contact_form',
  }),
});
```

- [ ] **Step 2: Verify form field names match** — open `index.html`, confirm the contact form inputs have `name="name"`, `name="email"`, `name="phone"`, `name="message"` attributes. Adjust selector if different.

- [ ] **Step 3: Test in browser**

Open `index.html` locally, submit the contact form with real data. Confirm:
- Success message appears
- Row appears in Supabase leads table
- Email notification arrives

- [ ] **Step 4: Commit**

```bash
git add js/main.js
git commit -m "feat: replace Formspree with Supabase Edge Function"
```

---

### Task 8: Add subscription form handler

Note: The subscription form on the C21 site and TAR(RENT) blog both call the same Edge Function. The `source` field differentiates them.

- [ ] **Step 1: Locate or add the subscriber form in index.html**

If a subscribe form doesn't exist yet, add this where appropriate (e.g. before the footer):

```html
<section id="subscribe" class="section-subscribe">
  <div class="container">
    <h2>Stay Informed</h2>
    <p>Get market insights and property management tips from the TAR(RENT) Blog.</p>
    <form id="subscribeForm">
      <input type="text" name="name" placeholder="Your name" />
      <input type="email" name="email" placeholder="Your email" required />
      <input type="hidden" name="source" value="c21_website" />
      <button type="submit">Subscribe</button>
    </form>
    <p id="subscribeSuccess" style="display:none;">You're subscribed!</p>
  </div>
</section>
```

- [ ] **Step 2: Add subscribe handler to js/main.js**

Append before the closing `});` of DOMContentLoaded:

```javascript
/* --- SUBSCRIBE FORM --- */
const subscribeForm    = document.getElementById('subscribeForm');
const subscribeSuccess = document.getElementById('subscribeSuccess');

if (subscribeForm) {
  subscribeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = subscribeForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Subscribing...';

    const response = await fetch('https://<ref>.supabase.co/functions/v1/handle-subscription', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:   subscribeForm.querySelector('[name="name"]').value,
        email:  subscribeForm.querySelector('[name="email"]').value,
        source: subscribeForm.querySelector('[name="source"]').value || 'c21_website',
      }),
    });

    if (response.ok) {
      subscribeForm.style.display = 'none';
      subscribeSuccess.style.display = 'block';
    } else {
      btn.disabled = false;
      btn.textContent = 'Subscribe';
      alert('Something went wrong. Please try again.');
    }
  });
}
```

- [ ] **Step 3: For TAR(RENT) blog** — use the same Edge Function URL. Set `source` hidden field to `"tarrent_blog"`.

- [ ] **Step 4: Commit**

```bash
git add index.html js/main.js
git commit -m "feat: add subscription form wired to Supabase"
```

---

## Chunk 4: Team Admin Page

### Task 9: Admin page HTML shell with auth gate

**Files:**
- Create: `admin/index.html`
- Create: `admin/css/admin.css`
- Create: `admin/js/admin.js`

- [ ] **Step 1: Create admin/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Team Portal — C21 Alliance Properties</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/admin.css" />
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
</head>
<body>

  <!-- LOGIN SCREEN -->
  <div id="loginScreen" class="login-screen">
    <div class="login-card">
      <div class="login-logo">C21<span>®</span></div>
      <h1>Team Portal</h1>
      <p class="login-sub">Century 21® Alliance Properties</p>
      <form id="loginForm">
        <input type="email" id="loginEmail" placeholder="Team email" required />
        <input type="password" id="loginPassword" placeholder="Password" required />
        <button type="submit" id="loginBtn">Sign In</button>
        <p id="loginError" class="error-msg"></p>
      </form>
    </div>
  </div>

  <!-- ADMIN APP (hidden until authed) -->
  <div id="adminApp" class="admin-app hidden">

    <!-- Navbar -->
    <nav class="admin-nav">
      <div class="admin-nav-brand">C21<span>®</span> Team Portal</div>
      <div class="admin-nav-tabs">
        <button class="tab-btn active" data-tab="leads">Leads</button>
        <button class="tab-btn" data-tab="subscribers">Subscribers</button>
        <button class="tab-btn" data-tab="contacts">Contacts</button>
      </div>
      <button id="signOutBtn" class="sign-out-btn">Sign Out</button>
    </nav>

    <!-- Upcoming Dates Sidebar + Main Content -->
    <div class="admin-layout">

      <main class="admin-main">

        <!-- LEADS TAB -->
        <section id="tab-leads" class="tab-panel active">
          <div class="panel-header">
            <h2>Leads Queue</h2>
            <span id="leadsCount" class="count-badge"></span>
          </div>
          <div id="leadsList" class="card-list">
            <p class="loading">Loading leads...</p>
          </div>
        </section>

        <!-- SUBSCRIBERS TAB -->
        <section id="tab-subscribers" class="tab-panel hidden">
          <div class="panel-header">
            <h2>Subscribers</h2>
            <span id="subscribersCount" class="count-badge"></span>
          </div>
          <div id="subscribersList" class="card-list">
            <p class="loading">Loading subscribers...</p>
          </div>
        </section>

        <!-- CONTACTS TAB -->
        <section id="tab-contacts" class="tab-panel hidden">
          <div class="panel-header">
            <h2>Contacts</h2>
            <button id="newContactBtn" class="btn-gold">+ New Contact</button>
          </div>
          <div id="contactsList" class="card-list">
            <p class="loading">Loading contacts...</p>
          </div>
        </section>

      </main>

      <!-- UPCOMING DATES SIDEBAR -->
      <aside class="admin-sidebar">
        <h3>Upcoming Dates</h3>
        <p class="sidebar-sub">Next 30 days</p>
        <div id="upcomingDates">
          <p class="loading">Loading...</p>
        </div>
      </aside>

    </div>
  </div>

  <script src="js/admin.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit the HTML shell**

```bash
git add admin/index.html
git commit -m "feat: add admin page HTML shell"
```

---

### Task 10: Admin CSS — on-brand with C21 site

**Files:**
- Create: `admin/css/admin.css`

- [ ] **Step 1: Create the stylesheet**

```css
/* admin/css/admin.css
   On-brand: Dark bg, Relentless Gold, Playfair + Inter
   --------------------------------------------------- */

:root {
  --gold:      #beaf87;
  --gold-dim:  #a89b70;
  --grey:      #c4c4c5;
  --bg-dark:   #111113;
  --bg-card:   #1c1c1e;
  --bg-input:  #2a2a2e;
  --text:      #f8f7f4;
  --text-muted:#9a9a9c;
  --border:    rgba(190,175,135,0.15);
  --radius:    8px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', sans-serif;
  background: var(--bg-dark);
  color: var(--text);
  min-height: 100vh;
  font-size: 14px;
}

/* ─── LOGIN ─────────────────────────────────────── */
.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-dark);
}

.login-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 48px 40px;
  width: 100%;
  max-width: 380px;
  text-align: center;
}

.login-logo {
  font-family: 'Playfair Display', serif;
  font-size: 2rem;
  color: var(--gold);
  margin-bottom: 8px;
}

.login-logo span { font-size: 1.2rem; }

.login-card h1 {
  font-family: 'Playfair Display', serif;
  font-size: 1.5rem;
  margin-bottom: 4px;
}

.login-sub { color: var(--text-muted); margin-bottom: 32px; font-size: 13px; }

.login-card form { display: flex; flex-direction: column; gap: 12px; }

.login-card input {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.login-card input:focus { border-color: var(--gold); }

.login-card button[type="submit"] {
  background: var(--gold);
  color: #111;
  border: none;
  border-radius: var(--radius);
  padding: 13px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 4px;
}

.login-card button[type="submit"]:hover { background: var(--gold-dim); }

.error-msg { color: #e57373; font-size: 13px; min-height: 18px; }

/* ─── LAYOUT ─────────────────────────────────────── */
.hidden { display: none !important; }

.admin-app { min-height: 100vh; display: flex; flex-direction: column; }

.admin-nav {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  height: 60px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.admin-nav-brand {
  font-family: 'Playfair Display', serif;
  font-size: 1.1rem;
  color: var(--gold);
  white-space: nowrap;
  margin-right: 8px;
}

.admin-nav-brand span { font-size: 0.75rem; }

.admin-nav-tabs { display: flex; gap: 4px; flex: 1; }

.tab-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.tab-btn:hover { color: var(--text); background: rgba(255,255,255,0.05); }
.tab-btn.active { color: var(--gold); background: rgba(190,175,135,0.1); }

.sign-out-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.sign-out-btn:hover { color: var(--text); border-color: var(--gold); }

.admin-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 0;
  flex: 1;
  max-height: calc(100vh - 60px);
  overflow: hidden;
}

.admin-main {
  padding: 24px;
  overflow-y: auto;
}

.admin-sidebar {
  background: var(--bg-card);
  border-left: 1px solid var(--border);
  padding: 24px;
  overflow-y: auto;
}

.admin-sidebar h3 {
  font-family: 'Playfair Display', serif;
  color: var(--gold);
  font-size: 1rem;
  margin-bottom: 4px;
}

.sidebar-sub { color: var(--text-muted); font-size: 12px; margin-bottom: 20px; }

/* ─── PANELS ──────────────────────────────────────── */
.tab-panel { display: none; }
.tab-panel.active { display: block; }

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.panel-header h2 {
  font-family: 'Playfair Display', serif;
  font-size: 1.4rem;
}

.count-badge {
  background: rgba(190,175,135,0.15);
  color: var(--gold);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
}

/* ─── CARDS ────────────────────────────────────────── */
.card-list { display: flex; flex-direction: column; gap: 12px; }

.lead-card, .subscriber-card, .contact-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  transition: border-color 0.2s;
}

.lead-card:hover, .contact-card:hover { border-color: rgba(190,175,135,0.35); }

.card-info { flex: 1; }

.card-name { font-weight: 600; font-size: 15px; margin-bottom: 4px; }

.card-meta { color: var(--text-muted); font-size: 12px; display: flex; gap: 16px; flex-wrap: wrap; }

.card-message {
  color: var(--grey);
  font-size: 13px;
  margin-top: 8px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── STATUS BADGES ───────────────────────────────── */
.status-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.status-new       { background: rgba(99,179,237,0.15); color: #63b3ed; }
.status-contacted { background: rgba(190,175,135,0.15); color: var(--gold); }
.status-follow_up { background: rgba(252,211,77,0.15); color: #fcd34d; }
.status-converted { background: rgba(72,187,120,0.15); color: #48bb78; }

/* ─── STATUS SELECT ────────────────────────────────── */
.status-select {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 12px;
  padding: 4px 8px;
  cursor: pointer;
  outline: none;
}

/* ─── UPCOMING DATE ITEMS ──────────────────────────── */
.date-item {
  border-left: 2px solid var(--gold);
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 0 6px 6px 0;
  background: rgba(190,175,135,0.05);
}

.date-item-label { font-size: 13px; font-weight: 500; }
.date-item-name  { font-size: 12px; color: var(--text-muted); }
.date-item-days  { font-size: 11px; color: var(--gold); margin-top: 2px; }

/* ─── UTILS ──────────────────────────────────────── */
.loading { color: var(--text-muted); font-size: 13px; }
.empty   { color: var(--text-muted); font-size: 13px; font-style: italic; }

.btn-gold {
  background: var(--gold);
  color: #111;
  border: none;
  border-radius: 6px;
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-gold:hover { background: var(--gold-dim); }

@media (max-width: 768px) {
  .admin-layout { grid-template-columns: 1fr; }
  .admin-sidebar { border-left: none; border-top: 1px solid var(--border); }
}
```

- [ ] **Step 2: Commit**

```bash
git add admin/css/admin.css
git commit -m "feat: add admin CSS on-brand with C21 site"
```

---

### Task 11: Admin JavaScript — auth + data

**Files:**
- Create: `admin/js/admin.js`

- [ ] **Step 1: Create admin/js/admin.js**

```javascript
// admin/js/admin.js
// ─── CONFIG ────────────────────────────────────────────────
const SUPABASE_URL  = 'https://<ref>.supabase.co'
const SUPABASE_ANON = '<your-anon-key>'
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON)

// ─── AUTH ──────────────────────────────────────────────────
const loginScreen = document.getElementById('loginScreen')
const adminApp    = document.getElementById('adminApp')
const loginForm   = document.getElementById('loginForm')
const loginError  = document.getElementById('loginError')
const signOutBtn  = document.getElementById('signOutBtn')

sb.auth.onAuthStateChange((_event, session) => {
  if (session) {
    loginScreen.classList.add('hidden')
    adminApp.classList.remove('hidden')
    initApp()
  } else {
    loginScreen.classList.remove('hidden')
    adminApp.classList.add('hidden')
  }
})

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault()
  loginError.textContent = ''
  const btn = document.getElementById('loginBtn')
  btn.disabled = true
  btn.textContent = 'Signing in...'

  const { error } = await sb.auth.signInWithPassword({
    email:    document.getElementById('loginEmail').value,
    password: document.getElementById('loginPassword').value,
  })

  if (error) {
    loginError.textContent = error.message
    btn.disabled = false
    btn.textContent = 'Sign In'
  }
})

signOutBtn.addEventListener('click', () => sb.auth.signOut())

// ─── TABS ──────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'))
    document.querySelectorAll('.tab-panel').forEach(p => {
      p.classList.remove('active')
      p.classList.add('hidden')
    })
    btn.classList.add('active')
    const panel = document.getElementById(`tab-${tab}`)
    panel.classList.remove('hidden')
    panel.classList.add('active')
  })
})

// ─── INIT ──────────────────────────────────────────────────
function initApp() {
  loadLeads()
  loadSubscribers()
  loadContacts()
  loadUpcomingDates()
}

// ─── LEADS ────────────────────────────────────────────────
async function loadLeads() {
  const { data, error } = await sb
    .from('leads')
    .select('*')
    .order('created_at', { ascending: false })

  const el = document.getElementById('leadsList')
  document.getElementById('leadsCount').textContent = data?.length ?? 0

  if (error || !data?.length) {
    el.innerHTML = '<p class="empty">No leads yet.</p>'
    return
  }

  el.innerHTML = data.map(lead => `
    <div class="lead-card" data-id="${lead.id}">
      <div class="card-info">
        <div class="card-name">${lead.name}</div>
        <div class="card-meta">
          <span>${lead.email}</span>
          ${lead.phone ? `<span>${lead.phone}</span>` : ''}
          <span>${lead.source}</span>
          <span>${formatDate(lead.created_at)}</span>
        </div>
        ${lead.message ? `<div class="card-message">${lead.message}</div>` : ''}
      </div>
      <div>
        <select class="status-select" data-lead-id="${lead.id}" onchange="updateLeadStatus(this)">
          ${['new','contacted','follow_up','converted'].map(s =>
            `<option value="${s}" ${lead.status === s ? 'selected' : ''}>${s.replace('_',' ')}</option>`
          ).join('')}
        </select>
      </div>
    </div>
  `).join('')
}

async function updateLeadStatus(select) {
  const { error } = await sb
    .from('leads')
    .update({ status: select.value })
    .eq('id', select.dataset.leadId)
  if (error) alert('Failed to update status: ' + error.message)
}

// ─── SUBSCRIBERS ──────────────────────────────────────────
async function loadSubscribers() {
  const { data, error } = await sb
    .from('subscribers')
    .select('*')
    .eq('active', true)
    .order('subscribed_at', { ascending: false })

  const el = document.getElementById('subscribersList')
  document.getElementById('subscribersCount').textContent = data?.length ?? 0

  if (error || !data?.length) {
    el.innerHTML = '<p class="empty">No subscribers yet.</p>'
    return
  }

  el.innerHTML = data.map(s => `
    <div class="subscriber-card">
      <div class="card-info">
        <div class="card-name">${s.email}</div>
        <div class="card-meta">
          ${s.name ? `<span>${s.name}</span>` : ''}
          <span>${s.source}</span>
          <span>${formatDate(s.subscribed_at)}</span>
        </div>
      </div>
    </div>
  `).join('')
}

// ─── CONTACTS ─────────────────────────────────────────────
async function loadContacts() {
  const { data, error } = await sb
    .from('contacts')
    .select('*, contact_people(*), contact_events(*)')
    .order('created_at', { ascending: false })

  const el = document.getElementById('contactsList')

  if (error || !data?.length) {
    el.innerHTML = '<p class="empty">No contacts yet. Promote a lead to create one.</p>'
    return
  }

  el.innerHTML = data.map(c => `
    <div class="contact-card">
      <div class="card-info">
        <div class="card-name">${c.name} <span class="status-badge status-${c.type}">${c.type}</span></div>
        <div class="card-meta">
          ${c.email ? `<span>${c.email}</span>` : ''}
          ${c.phone ? `<span>${c.phone}</span>` : ''}
          ${c.property_address ? `<span>${c.property_address}</span>` : ''}
          ${c.assigned_to ? `<span>Assigned: ${c.assigned_to}</span>` : ''}
        </div>
        ${c.notes ? `<div class="card-message">${c.notes}</div>` : ''}
        ${c.contact_people?.length ? `
          <div class="card-meta" style="margin-top:8px;">
            Family: ${c.contact_people.map(p => `${p.name} (${p.relationship})`).join(', ')}
          </div>` : ''}
      </div>
    </div>
  `).join('')
}

// ─── UPCOMING DATES ────────────────────────────────────────
async function loadUpcomingDates() {
  const { data: events } = await sb
    .from('contact_events')
    .select('*, contacts(name)')

  const { data: people } = await sb
    .from('contact_people')
    .select('*, contacts(name)')
    .not('birthday', 'is', null)

  const today    = new Date()
  const in30days = new Date(today)
  in30days.setDate(today.getDate() + 30)

  const upcoming = []

  // Contact events
  ;(events || []).forEach(ev => {
    const evDate = nextOccurrence(ev.date, ev.recurs_yearly)
    if (evDate >= today && evDate <= in30days) {
      upcoming.push({ label: ev.label, name: ev.contacts?.name, date: evDate })
    }
  })

  // Birthdays from contact_people
  ;(people || []).forEach(p => {
    const bDay = nextOccurrence(p.birthday, true)
    if (bDay >= today && bDay <= in30days) {
      upcoming.push({ label: `${p.name}'s Birthday`, name: p.contacts?.name, date: bDay })
    }
  })

  upcoming.sort((a, b) => a.date - b.date)

  const el = document.getElementById('upcomingDates')
  if (!upcoming.length) {
    el.innerHTML = '<p class="empty">Nothing in the next 30 days.</p>'
    return
  }

  el.innerHTML = upcoming.map(u => {
    const days = Math.ceil((u.date - today) / (1000 * 60 * 60 * 24))
    return `
      <div class="date-item">
        <div class="date-item-label">${u.label}</div>
        ${u.name ? `<div class="date-item-name">${u.name}</div>` : ''}
        <div class="date-item-days">In ${days} day${days !== 1 ? 's' : ''} — ${u.date.toLocaleDateString('en-US',{month:'short',day:'numeric'})}</div>
      </div>
    `
  }).join('')
}

// ─── HELPERS ───────────────────────────────────────────────
function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function nextOccurrence(dateStr, recurs) {
  const d = new Date(dateStr)
  if (!recurs) return d
  const today = new Date()
  d.setFullYear(today.getFullYear())
  if (d < today) d.setFullYear(today.getFullYear() + 1)
  return d
}
```

- [ ] **Step 2: Replace `<ref>` and `<your-anon-key>`** with your actual Supabase project reference and anon key (both visible in Supabase dashboard → Settings → API).

- [ ] **Step 3: Test the admin page**

Open `admin/index.html` in browser. Sign in as one of the three team accounts. Confirm:
- Leads queue loads and shows test submissions
- Subscribers list loads
- Status dropdown updates the database on change
- Upcoming dates sidebar populates (add a test contact event in Supabase to verify)

- [ ] **Step 4: Commit**

```bash
git add admin/js/admin.js
git commit -m "feat: complete admin page with auth, leads, subscribers, contacts, upcoming dates"
```

---

### Task 12: Final wiring check

- [ ] **Step 1: Verify end-to-end flow**

Submit the contact form on the live site → row appears in leads → email arrives → admin page shows new lead with `new` status badge.

- [ ] **Step 2: Set CORS on Edge Functions** (if needed)

If the site is hosted on a custom domain, update the `Access-Control-Allow-Origin` header in both Edge Functions from `'*'` to your domain, e.g. `'https://c21allianceproperties.com'`.

- [ ] **Step 3: Update CLAUDE.md** with Supabase project details

Add to `CLAUDE.md`:
```markdown
## Supabase
- Project URL: https://<ref>.supabase.co
- Anon key: <anon-key> (safe to commit — RLS enforced)
- Admin page: /admin
- Edge Functions: handle-contact-form, handle-subscription
- MCP plugin: supabase@claude-plugins-official (enabled)
```

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Supabase project details to CLAUDE.md"
```

---

## Summary

| Chunk | What ships | Can be tested independently? |
|---|---|---|
| 1 — Schema | Tables + RLS + team auth | Yes — verify in Supabase dashboard |
| 2 — Edge Functions | Form → DB → email notification | Yes — curl test |
| 3 — Form Integration | Contact + subscribe forms live | Yes — submit form in browser |
| 4 — Admin Page | Team portal with leads/CRM/dates | Yes — open admin/index.html |
