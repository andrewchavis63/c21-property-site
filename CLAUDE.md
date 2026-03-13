# C21 Alliance Properties — Website

## Project Overview
Single-page property management website for Century 21 Alliance Properties.
Target audience: remote investors in Tarrant & Parker County, North Texas.

## Stack
- Pure HTML + CSS + JS — no framework, no build step
- `index.html` — main single-page site + homepage blog teaser
- `css/styles.css` — all styles
- `js/main.js` — scroll effects, mobile menu, form, counter animations
- `TARRENT/index.html` — blog page (posts rendered via JS modal, images hardcoded in HTML)
- `TARRENT/img/` — blog post images (source originals in C:\Users\achav\OneDrive\Desktop\FW Royalty Free Pics)

## Business Info
- **Company:** Century 21® Alliance Properties
- **Office:** 120 West McLeroy Blvd., Saginaw, TX 76179
- **Phone:** (817) 995-3722
- **Email:** SarenaSSmith@gmail.com
- **Hours:** Mon–Fri 9:00 AM – 4:00 PM, excluding holidays; weekends by appointment

## Brand
- **Relentless Gold:** `#beaf87`
- **Obsessed Grey:** `#c4c4c5`
- Dark bg: `#1c1c1e` / `#111113` | Light bg: `#f8f7f4`
- Headings: Playfair Display | Body: Inter (Google Fonts)

## Team
1. **Starlyn Smith** — Lead REALTOR® · Owner Liaison | (817) 995-3722 | Starlyn.Smith21@gmail.com
2. **Sarena Smith** — Leasing Specialist · Property Manager | (817) 201-0410 | SarenaSSmith@gmail.com
3. **Andrew Chavis** — Maintenance Coordinator · Digital Marketing | (817) 420-0833 | AndrewChavis63@gmail.com

## Public Stats (use these numbers everywhere)
- 75+ properties managed (not 80, not 80+)
- 93% avg. occupancy | 30+ yrs combined experience | 4.9★ owner satisfaction

## Contact Form
- Formspree endpoint: `https://formspree.io/f/xlgwkdkn`
- Submissions → SarenaSSmith@gmail.com
- Free tier: 50 submissions/month

## Sections
- Sticky navbar, Hero (stat counters), Services (6 cards), Why Choose Us, Team, Contact, Footer

## Blog Architecture
- Posts stored in a `const posts` JS object keyed by id (e.g. `'featured'`, `'tar-representation'`)
- `openPost(id)` renders post content in a modal — triggered by `onclick` on cards
- Featured card is a separate section from the posts grid; filter tabs only filter grid cards
- To make a post filterable, it must be a `.post-card` in the grid with a matching `data-cat` attribute
- **GOTCHA:** A `DOMContentLoaded` block previously injected images from `posts.featured.img` into `.featured-img`, overwriting hardcoded HTML images. That block has been removed — images are now hardcoded in HTML. Do not re-add dynamic image injection.
- Blog card order = newest → oldest by date

## Blog Post IDs & Dates
- `tar-representation` — March 2026 (featured + grid)
- `featured` (FW Market post) — March 2026
- `saginaw` — March 2026
- `seller-mistakes` — February 2026
- `absentee` — January 2026
- `first-time` — January 2026
- `rates` — December 2025
- `azle` — November 2025

## Filter Tab → data-cat Mapping
- `buyers-tenants` → Buyers & Tenants (tar-representation, first-time)
- `market` → Market Updates (featured/FW Market, rates)
- `sellers` → Seller Tips (seller-mistakes)
- `neighborhoods` → Neighborhoods (saginaw, azle)
- `investing` → Investing (absentee)

## Conventions
- Always include `&reg;` after "Century 21" — e.g. Century 21®
- Keep it vanilla — no npm, no bundler, no frameworks
- Mobile-first, responsive

## Open Tasks
- [ ] Starlyn's bio (needs interview/bullet points)
- [ ] Headshots (scheduled 2026-03-12) — swap placeholders after shoot
- [ ] Connect Netlify to GitHub repo
- [ ] Choose and connect domain
- [ ] Restrict Google Maps API key to production domain
