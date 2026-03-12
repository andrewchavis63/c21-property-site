# Supabase Form Wiring — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy both Supabase Edge Functions, set required env vars, and wire the blog subscribe form so leads and subscribers flow into the admin panel.

**Architecture:** Two Edge Functions (already written) receive POST requests from the website and insert rows into Supabase. The contact form in `main.js` is already wired — only the blog email strip needs JS added. Functions are deployed via the Supabase CLI and called without JWT auth (public endpoints).

**Tech Stack:** Supabase Edge Functions (Deno), Supabase CLI, vanilla JS, Resend (email notifications)

---

## File Map

| File | Change |
|---|---|
| `blog/index.html` | Add ~25 lines of inline JS below `.email-strip` |
| `supabase/functions/handle-contact-form/index.ts` | Deploy only — no code changes |
| `supabase/functions/handle-subscription/index.ts` | Deploy only — no code changes |

---

## Chunk 1: Set Secrets & Deploy Edge Functions

> ⚠️ **You will need two keys for this chunk:**
> - **Supabase service role key:** `supabase.com/dashboard/project/zksjjekaiscwkmiibbqp/settings/api` → "service_role" (under Project API keys — click to reveal)
> - **Resend API key:** `resend.com/api-keys` → Create API Key

---

### Task 1: Link Supabase CLI to your project

**Files:** none

- [ ] **Step 1: Open a terminal in the project root**

  ```bash
  cd C:\Users\achav\c21-property-site
  ```

- [ ] **Step 2: Check if Supabase CLI is available**

  ```bash
  supabase --version
  ```

  If you get "command not found", install it:
  ```bash
  npm install -g supabase
  ```

- [ ] **Step 3: Log in to Supabase**

  ```bash
  supabase login
  ```

  This opens a browser — sign in with your Supabase account. You only need to do this once.

- [ ] **Step 4: Link to your remote project**

  ```bash
  supabase link --project-ref zksjjekaiscwkmiibbqp
  ```

  It will ask for your database password. If you don't know it, go to:
  `supabase.com/dashboard/project/zksjjekaiscwkmiibbqp/settings/database` → Reset password if needed.

  Expected output:
  ```
  Finished supabase link.
  ```

---

### Task 2: Set environment variable secrets

**Files:** none (secrets stored on Supabase, never in files)

- [ ] **Step 1: Set your Supabase service role key**

  ```bash
  supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<paste-your-service-role-key-here>
  ```

- [ ] **Step 2: Set your Resend API key**

  ```bash
  supabase secrets set RESEND_API_KEY=<paste-your-resend-api-key-here>
  ```

- [ ] **Step 3: Set the notification email**

  ```bash
  supabase secrets set NOTIFICATION_EMAIL=SarenaSSmith@gmail.com
  ```

- [ ] **Step 4: Verify all three secrets are set**

  ```bash
  supabase secrets list
  ```

  Expected output — all three should appear:
  ```
  SUPABASE_SERVICE_ROLE_KEY  ...
  RESEND_API_KEY             ...
  NOTIFICATION_EMAIL         ...
  ```

---

### Task 3: Deploy both Edge Functions

**Files:** none (code already written in `supabase/functions/`)

- [ ] **Step 1: Deploy the contact form function**

  ```bash
  supabase functions deploy handle-contact-form --no-verify-jwt
  ```

  `--no-verify-jwt` is required because the website calls this function without a logged-in user.

  Expected output:
  ```
  Deployed Function handle-contact-form on project zksjjekaiscwkmiibbqp
  ```

- [ ] **Step 2: Deploy the subscription function**

  ```bash
  supabase functions deploy handle-subscription --no-verify-jwt
  ```

  Expected output:
  ```
  Deployed Function handle-subscription on project zksjjekaiscwkmiibbqp
  ```

- [ ] **Step 3: Verify both functions are live**

  Go to: `supabase.com/dashboard/project/zksjjekaiscwkmiibbqp/functions`

  Both `handle-contact-form` and `handle-subscription` should appear with a green "Active" status.

- [ ] **Step 4: Smoke test the contact form function**

  ```bash
  curl -X POST https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/handle-contact-form \
    -H "Content-Type: application/json" \
    -d '{"name":"Test Lead","email":"test@example.com","source":"contact_form"}'
  ```

  Expected response:
  ```json
  {"success":true}
  ```

  Then verify in Supabase → Table Editor → `leads` that a row was inserted.

- [ ] **Step 5: Smoke test the subscription function**

  ```bash
  curl -X POST https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/handle-subscription \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","source":"tarrent_blog"}'
  ```

  Expected response:
  ```json
  {"success":true}
  ```

  Verify in Supabase → Table Editor → `subscribers` that a row was inserted.

---

## Chunk 2: Wire Blog Subscribe Form

### Task 4: Add subscribe JS to blog/index.html

**Files:**
- Modify: `blog/index.html` (after the `.email-strip` closing div, ~line 796)

The email strip currently looks like this (no JS):
```html
<!-- EMAIL STRIP -->
<div class="email-strip">
  <div class="email-strip-text">
    <h3>Get the <em>TAR(RENT)</em></h3>
    <p>TAR(RENT) delivers weekly insights...</p>
  </div>
  <div class="email-form">
    <input type="email" placeholder="your@email.com"/>
    <button>Subscribe Free</button>
  </div>
</div>
```

- [ ] **Step 1: Add the subscribe script immediately after the closing `</div>` of `.email-strip`**

  Insert this block right after `</div>` that closes `.email-strip` (before `<!-- FOOTER -->`):

  ```html
  <script>
  (function () {
    const strip  = document.querySelector('.email-strip')
    const input  = strip.querySelector('input[type="email"]')
    const btn    = strip.querySelector('button')
    const FN_URL = 'https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/handle-subscription'

    btn.addEventListener('click', async () => {
      const email = input.value.trim()
      if (!email || !email.includes('@')) {
        input.style.borderColor = '#e05'
        input.focus()
        return
      }

      btn.disabled  = true
      input.disabled = true
      btn.textContent = 'Subscribing…'

      try {
        const res = await fetch(FN_URL, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ email, source: 'tarrent_blog' }),
        })

        if (res.ok) {
          input.value     = ''
          btn.textContent = "You're in ✓"
          btn.style.background = '#4a7c59'
        } else {
          throw new Error('Server error')
        }
      } catch {
        btn.disabled   = false
        input.disabled = false
        btn.textContent = 'Subscribe Free'
        input.style.borderColor = '#e05'
        let err = strip.querySelector('.sub-error')
        if (!err) {
          err = document.createElement('p')
          err.className = 'sub-error'
          err.style.cssText = 'color:#e05;font-size:12px;margin-top:8px;width:100%;'
          strip.querySelector('.email-form').insertAdjacentElement('afterend', err)
        }
        err.textContent = 'Something went wrong — please try again.'
      }
    })

    input.addEventListener('input', () => {
      input.style.borderColor = ''
      const err = strip.querySelector('.sub-error')
      if (err) err.textContent = ''
    })
  })()
  </script>
  ```

- [ ] **Step 2: Verify the JS is placed correctly**

  The structure should be:
  ```
  </div>  ← closing .email-strip
  <script>...</script>  ← new block
  <!-- FOOTER -->
  <footer>
  ```

- [ ] **Step 3: Open blog/index.html locally and test**

  - Click "Subscribe Free" with an empty field → input border turns red, no request sent
  - Enter a valid email and click → button shows "Subscribing…" then "You're in ✓" (green)
  - Check Supabase → Table Editor → `subscribers` → new row with `source = 'tarrent_blog'`
  - Check admin panel (`admin/index.html`) → Subscribers tab → entry appears

- [ ] **Step 4: Commit**

  ```bash
  git add blog/index.html
  git commit -m "feat: wire blog subscribe form to Supabase handle-subscription"
  ```

---

## Chunk 3: End-to-End Verification

### Task 5: Full end-to-end test

- [ ] **Step 1: Test the contact form on index.html**

  Open `index.html` locally. Fill out the contact form with a real name, email, phone, and message. Submit.

  Expected:
  - Success state appears (form hides, success message shows)
  - Row appears in Supabase → `leads` table with `status = 'new'`
  - Row appears in admin panel → Leads tab
  - Notification email arrives at SarenaSSmith@gmail.com (Resend)

- [ ] **Step 2: Test the blog subscribe form**

  Open `blog/index.html` locally. Enter an email and click Subscribe Free.

  Expected:
  - Button shows "You're in ✓" in green
  - Row appears in Supabase → `subscribers` table with `source = 'tarrent_blog'`
  - Row appears in admin panel → Subscribers tab
  - Notification email arrives at SarenaSSmith@gmail.com

- [ ] **Step 3: Test duplicate subscribe (same email)**

  Enter the same email again in the blog form and click Subscribe.

  Expected:
  - Button shows "You're in ✓" (no error — upsert silently succeeds)
  - No duplicate row in `subscribers` (existing row updated)

- [ ] **Step 4: Confirm admin panel shows all data**

  Open `admin/index.html`. Sign in. Check:
  - Leads tab shows the test lead from Step 1
  - Subscribers tab shows the test subscriber from Step 2
  - Quick Stats sidebar shows updated counts
