# Staff Portal Footer Link — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Staff Portal" link to the footer of all 14 pages so the team can navigate to the admin panel.

**Architecture:** Two patterns apply — root-level pages use a `.footer-trec` strip; blog pages use a `.footer-links` div. Each gets the link appended at the end, using the correct relative path. No new CSS required.

**Tech Stack:** Plain HTML — no build step, no framework.

---

## File Map

### Pattern A — `.footer-trec` strip (root-level pages, path: `admin/index.html`)
- `index.html`
- `tenant-criteria.html`
- `petscreening.html`
- `services-screening.html`
- `services-rent.html`
- `services-maintenance.html`
- `services-reporting.html`
- `services-inspections.html`
- `services-evictions.html`
- `team-starlyn.html`
- `team-sarena.html`
- `team-andrew.html`

### Pattern B — `.footer-links` div (blog pages, path: `../admin/index.html`)
- `blog/index.html`
- `blog/disclaimer.html`

---

## Chunk 1: Root-Level Pages

### Task 1: Add Staff Portal to index.html

**Files:**
- Modify: `index.html` (`.footer-trec` paragraph, line ~940)

**Current markup:**
```html
<a href="docs/andrew-chavis-iabs-2026.pdf" target="_blank" rel="noopener noreferrer">IABS — Andrew Chavis</a></p>
```

**Target markup:**
```html
<a href="docs/andrew-chavis-iabs-2026.pdf" target="_blank" rel="noopener noreferrer">IABS — Andrew Chavis</a> &bull; <a href="admin/index.html">Staff Portal</a></p>
```

- [ ] **Step 1: Make the edit in `index.html`**

  Find the `.footer-trec` paragraph (search for `IABS — Andrew Chavis</a></p>`).
  Append ` &bull; <a href="admin/index.html">Staff Portal</a>` before `</p>`.

- [ ] **Step 2: Verify in browser**

  Open `index.html` locally. Scroll to footer. Confirm "Staff Portal" appears after the IABS links with `·` separator. Click it — confirm it navigates to `admin/index.html`.

- [ ] **Step 3: Commit**

  ```bash
  git add index.html
  git commit -m "feat: add Staff Portal link to index.html footer"
  ```

---

### Task 2: Add Staff Portal to tenant-criteria.html

**Files:**
- Modify: `tenant-criteria.html` (`.footer-trec` paragraph)

- [ ] **Step 1: Make the edit**

  Same find/replace as Task 1. Append ` &bull; <a href="admin/index.html">Staff Portal</a>` before `</p>` in the `.footer-trec` paragraph.

- [ ] **Step 2: Verify in browser**

  Open `tenant-criteria.html`. Scroll to footer. Confirm link appears and navigates correctly.

- [ ] **Step 3: Commit**

  ```bash
  git add tenant-criteria.html
  git commit -m "feat: add Staff Portal link to tenant-criteria.html footer"
  ```

---

### Task 3: Add Staff Portal to petscreening.html

**Files:**
- Modify: `petscreening.html` (`.footer-trec` paragraph)

- [ ] **Step 1: Make the edit**

  Same pattern. Append ` &bull; <a href="admin/index.html">Staff Portal</a>` before `</p>`.

- [ ] **Step 2: Verify in browser**

  Open `petscreening.html`. Scroll to footer. Confirm link appears.

- [ ] **Step 3: Commit**

  ```bash
  git add petscreening.html
  git commit -m "feat: add Staff Portal link to petscreening.html footer"
  ```

---

### Task 4: Add Staff Portal to all 6 service pages

**Files:**
- Modify: `services-screening.html`
- Modify: `services-rent.html`
- Modify: `services-maintenance.html`
- Modify: `services-reporting.html`
- Modify: `services-inspections.html`
- Modify: `services-evictions.html`

- [ ] **Step 1: Make the edit in all 6 files**

  In each file, find the `.footer-trec` paragraph ending with `IABS — Andrew Chavis</a></p>` and append ` &bull; <a href="admin/index.html">Staff Portal</a>` before `</p>`.

- [ ] **Step 2: Verify one service page in browser**

  Open `services-screening.html`. Scroll to footer. Confirm link appears and navigates to the admin login screen.

- [ ] **Step 3: Commit**

  ```bash
  git add services-screening.html services-rent.html services-maintenance.html services-reporting.html services-inspections.html services-evictions.html
  git commit -m "feat: add Staff Portal link to all service page footers"
  ```

---

### Task 5: Add Staff Portal to all 3 team pages

**Files:**
- Modify: `team-starlyn.html`
- Modify: `team-sarena.html`
- Modify: `team-andrew.html`

- [ ] **Step 1: Make the edit in all 3 files**

  Same pattern. Append ` &bull; <a href="admin/index.html">Staff Portal</a>` before `</p>` in each `.footer-trec` paragraph.

- [ ] **Step 2: Verify one team page in browser**

  Open `team-starlyn.html`. Scroll to footer. Confirm link appears.

- [ ] **Step 3: Commit**

  ```bash
  git add team-starlyn.html team-sarena.html team-andrew.html
  git commit -m "feat: add Staff Portal link to team page footers"
  ```

---

## Chunk 2: Blog Pages

Blog pages use a different footer structure — `.footer-links` div with individual `<a>` tags, not `.footer-trec`. The "Staff Portal" link is appended as the last item in that div. Path is `../admin/index.html` (one level up from `blog/`).

---

### Task 6: Add Staff Portal to blog/index.html

**Files:**
- Modify: `blog/index.html` (`.footer-links` div, line ~805)

**Current markup:**
```html
  <div class="footer-links">
    <a href="#">Privacy</a>
    <a href="disclaimer.html">Disclaimer</a>
    ...
    <a href="https://www.trec.texas.gov/forms/consumer-protection-notice" target="_blank">Consumer Protection Notice</a>
  </div>
```

**Target markup — add one line before `</div>`:**
```html
  <div class="footer-links">
    <a href="#">Privacy</a>
    <a href="disclaimer.html">Disclaimer</a>
    ...
    <a href="https://www.trec.texas.gov/forms/consumer-protection-notice" target="_blank">Consumer Protection Notice</a>
    <a href="../admin/index.html">Staff Portal</a>
  </div>
```

- [ ] **Step 1: Make the edit in `blog/index.html`**

  Find the `.footer-links` div. Insert `    <a href="../admin/index.html">Staff Portal</a>` as the last item before `</div>`.

- [ ] **Step 2: Verify in browser**

  Open `blog/index.html`. Scroll to footer. Confirm "Staff Portal" appears in the footer links row. Click it — confirm it navigates to `admin/index.html` (the login screen).

- [ ] **Step 3: Commit**

  ```bash
  git add blog/index.html
  git commit -m "feat: add Staff Portal link to blog/index.html footer"
  ```

---

### Task 7: Add Staff Portal to blog/disclaimer.html

**Files:**
- Modify: `blog/disclaimer.html` (`.footer-links` div, line ~544)

**Current markup:**
```html
  <div class="footer-links">
    <a href="#">Privacy</a>
    <a href="disclaimer.html" class="active">Disclaimer</a>
    ...
    <a href="https://www.trec.texas.gov/forms/consumer-protection-notice" target="_blank" rel="noopener">Consumer Protection Notice</a>
  </div>
```

**Target markup:**
```html
  <div class="footer-links">
    <a href="#">Privacy</a>
    <a href="disclaimer.html" class="active">Disclaimer</a>
    ...
    <a href="https://www.trec.texas.gov/forms/consumer-protection-notice" target="_blank" rel="noopener">Consumer Protection Notice</a>
    <a href="../admin/index.html">Staff Portal</a>
  </div>
```

- [ ] **Step 1: Make the edit in `blog/disclaimer.html`**

  Find the `.footer-links` div. Insert `    <a href="../admin/index.html">Staff Portal</a>` as the last item before `</div>`.

- [ ] **Step 2: Verify in browser**

  Open `blog/disclaimer.html`. Scroll to footer. Confirm link appears and path resolves correctly.

- [ ] **Step 3: Commit**

  ```bash
  git add blog/disclaimer.html
  git commit -m "feat: add Staff Portal link to blog/disclaimer.html footer"
  ```

---

## Final Verification

- [ ] Open all 14 pages (spot-check at minimum: index.html, one service page, one team page, blog/index.html, blog/disclaimer.html)
- [ ] Confirm "Staff Portal" appears in every footer
- [ ] Confirm clicking it reaches the admin login screen from each page
- [ ] Confirm no broken paths (especially blog pages using `../admin/index.html`)
