# Design: Staff Portal Link in Footer
**Date:** 2026-03-10
**Project:** C21 Alliance Properties Website
**Scope:** Part B of admin-website connection — add team navigation to admin panel

---

## Problem

The admin panel (`admin/index.html`) is fully functional but unreachable from the main website. Team members must bookmark the URL or know it by memory.

## Solution

Add a "Staff Portal" text link to the `.footer-trec` legal strip that already exists on every page. It sits inline with the TREC license, Consumer Protection Notice, and IABS links — visually camouflaged as legal fine print, but accessible to team members who know to look for it.

## Design

### Placement
Appended to the end of the `.footer-trec` paragraph, separated by the same `·` character used between existing legal links.

### Result line
> TREC Lic. No. 9014679 · Consumer Protection Notice · Sarena Smith IABS · Andrew Chavis IABS · Staff Portal

### Styling
Inherits `.footer-trec a` — no new CSS. Same dimmed color and gold hover as the existing legal links.

### Link paths
- Root-level pages → `admin/index.html`
- Blog pages → `../admin/index.html`

---

## Affected Pages (14 total)

### Root-level (path: `admin/index.html`)
1. `index.html`
2. `tenant-criteria.html`
3. `petscreening.html`
4. `services-screening.html`
5. `services-rent.html`
6. `services-maintenance.html`
7. `services-reporting.html`
8. `services-inspections.html`
9. `services-evictions.html`
10. `team-starlyn.html`
11. `team-sarena.html`
12. `team-andrew.html`

### Blog subdirectory (path: `../admin/index.html`)
13. `blog/index.html`
14. `blog/disclaimer.html`

---

## What Is Not Changing
- No new CSS
- No changes to `admin/` files
- No changes to Supabase or auth logic
- The link does not appear in the main nav or anywhere else

---

## Success Criteria
- All 14 pages have the "Staff Portal" link in their `.footer-trec` strip
- Clicking it navigates to the admin login screen
- The link is visually indistinguishable from the other legal links
- Paths are correct for both root and blog pages
