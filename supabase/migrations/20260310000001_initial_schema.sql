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

create policy "team delete leads"
  on leads for delete to authenticated using (true);

-- subscribers: anyone can insert, only auth users can read/edit
create policy "public insert subscribers"
  on subscribers for insert to anon with check (true);

create policy "team read subscribers"
  on subscribers for select to authenticated using (true);

create policy "team delete subscribers"
  on subscribers for delete to authenticated using (true);

-- contacts + related: auth users only
create policy "team all contacts"
  on contacts for all to authenticated using (true);

create policy "team all contact_people"
  on contact_people for all to authenticated using (true);

create policy "team all contact_events"
  on contact_events for all to authenticated using (true);
