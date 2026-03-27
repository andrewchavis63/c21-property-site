// admin/js/admin.js — C21 Alliance Properties Team Portal

const SUPABASE_URL  = 'https://zksjjekaiscwkmiibbqp.supabase.co'
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inprc2pqZWthaXNjd2ttaWliYnFwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxMzgyODIsImV4cCI6MjA4ODcxNDI4Mn0.wPlNgLu4GvaGCsSHnM5loewvgysTSqRHgLXczzrDqRo'
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
    document.getElementById('userEmail').textContent = session.user.email
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
  loadStats()
}

// ─── LEADS ─────────────────────────────────────────────────
async function loadLeads() {
  const { data, error } = await sb
    .from('leads')
    .select('*')
    .order('created_at', { ascending: false })

  const el = document.getElementById('leadsList')
  document.getElementById('leadsCount').textContent = data?.length ?? 0

  if (error || !data?.length) {
    el.innerHTML = '<p class="empty">No leads yet — submit the contact form to create the first one.</p>'
    return
  }

  el.innerHTML = data.map(lead => `
    <div class="lead-card">
      <div class="card-info">
        <div class="card-name">
          ${esc(lead.name)}
          <span class="status-badge status-${lead.status}">${lead.status.replace('_', ' ')}</span>
        </div>
        <div class="card-meta">
          <span>${esc(lead.email)}</span>
          ${lead.phone ? `<span>${esc(lead.phone)}</span>` : ''}
          <span>${esc(lead.source)}</span>
          <span>${fmtDate(lead.created_at)}</span>
        </div>
        ${lead.message ? `<div class="card-message">${esc(lead.message)}</div>` : ''}
      </div>
      <div class="card-actions">
        <select class="status-select" data-lead-id="${lead.id}" onchange="updateLeadStatus(this)">
          ${['new','contacted','follow_up','converted'].map(s =>
            `<option value="${s}" ${lead.status === s ? 'selected' : ''}>${s.replace('_', ' ')}</option>`
          ).join('')}
        </select>
        <button class="btn-gold" onclick="openPromoteModal('${lead.id}', '${esc(lead.name)}', '${esc(lead.email)}', '${esc(lead.phone || '')}')">
          → Contact
        </button>
        <button class="btn-danger" onclick="deleteLead('${lead.id}', '${esc(lead.name)}')">Delete</button>
      </div>
    </div>
  `).join('')
}

async function deleteLead(id, name) {
  if (!confirm(`Delete lead "${name}"? This cannot be undone.`)) return
  const { error } = await sb.from('leads').delete().eq('id', id)
  if (error) alert('Error: ' + error.message)
  else { loadLeads(); loadStats() }
}

async function updateLeadStatus(select) {
  const { error } = await sb
    .from('leads')
    .update({ status: select.value })
    .eq('id', select.dataset.leadId)
  if (error) alert('Failed to update: ' + error.message)
  else loadStats()
}

// ─── SUBSCRIBERS ───────────────────────────────────────────
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
        <div class="card-name">${esc(s.email)}</div>
        <div class="card-meta">
          ${s.name ? `<span>${esc(s.name)}</span>` : ''}
          <span>${esc(s.source)}</span>
          <span>${fmtDate(s.subscribed_at)}</span>
        </div>
      </div>
      <div class="card-actions">
        <button class="btn-danger" onclick="deleteSubscriber('${s.id}', '${esc(s.email)}')">Delete</button>
      </div>
    </div>
  `).join('')
}

async function deleteSubscriber(id, email) {
  if (!confirm(`Remove ${email} from subscribers?`)) return
  const { error } = await sb.from('subscribers').delete().eq('id', id)
  if (error) alert('Error: ' + error.message)
  else { loadSubscribers(); loadStats() }
}

// ─── CONTACTS ──────────────────────────────────────────────
async function loadContacts() {
  const { data, error } = await sb
    .from('contacts')
    .select('*, contact_people(*), contact_events(*)')
    .order('created_at', { ascending: false })

  const el = document.getElementById('contactsList')

  if (error || !data?.length) {
    el.innerHTML = '<p class="empty">No contacts yet. Use the → Contact button on a lead to create one.</p>'
    return
  }

  el.innerHTML = data.map(c => `
    <div class="contact-card">
      <div class="card-info">
        <div class="card-name">
          ${esc(c.name)}
          <span class="status-badge status-${c.type}">${c.type}</span>
          ${c.assigned_to ? `<span style="font-size:12px;color:var(--text-muted);font-weight:400;">${esc(c.assigned_to)}</span>` : ''}
        </div>
        <div class="card-meta">
          ${c.email            ? `<span>${esc(c.email)}</span>` : ''}
          ${c.phone            ? `<span>${esc(c.phone)}</span>` : ''}
          ${c.property_address ? `<span>${esc(c.property_address)}</span>` : ''}
        </div>
        ${c.notes ? `<div class="card-message">${esc(c.notes)}</div>` : ''}
        ${c.contact_people?.length ? `
          <div class="card-meta" style="margin-top:8px;color:var(--grey);">
            Family: ${c.contact_people.map(p =>
              `${esc(p.name)} (${p.relationship}${p.birthday ? ', b. ' + p.birthday : ''})`
            ).join(' · ')}
          </div>` : ''}
        ${c.contact_events?.length ? `
          <div class="card-meta" style="margin-top:4px;color:var(--grey);">
            Dates: ${c.contact_events.map(e => `${esc(e.label)} — ${e.date}`).join(' · ')}
          </div>` : ''}
      </div>
      <div class="card-actions">
        <button class="btn-danger" onclick="deleteContact('${c.id}', '${esc(c.name)}')">Delete</button>
      </div>
    </div>
  `).join('')
}

async function deleteContact(id, name) {
  if (!confirm(`Delete contact "${name}"? This cannot be undone.`)) return
  const { error } = await sb.from('contacts').delete().eq('id', id)
  if (error) alert('Error: ' + error.message)
  else { loadContacts(); loadStats() }
}

// ─── PROMOTE MODAL ─────────────────────────────────────────
function openPromoteModal(leadId, name, email, phone) {
  document.getElementById('promoteLeadId').value = leadId
  document.getElementById('promoteModal').classList.remove('hidden')
}

document.getElementById('promoteCancelBtn').addEventListener('click', () => {
  document.getElementById('promoteModal').classList.add('hidden')
})

document.getElementById('promoteConfirmBtn').addEventListener('click', async () => {
  const leadId = document.getElementById('promoteLeadId').value
  const { data: lead } = await sb.from('leads').select('*').eq('id', leadId).single()

  const { error } = await sb.from('contacts').insert({
    lead_id:         leadId,
    name:            lead.name,
    email:           lead.email,
    phone:           lead.phone,
    type:            document.getElementById('promoteType').value,
    assigned_to:     document.getElementById('promoteAssigned').value || null,
    notes:           document.getElementById('promoteNotes').value || null,
  })

  if (error) {
    alert('Error creating contact: ' + error.message)
    return
  }

  // Mark lead as converted
  await sb.from('leads').update({ status: 'converted' }).eq('id', leadId)

  document.getElementById('promoteModal').classList.add('hidden')
  document.getElementById('promoteNotes').value = ''
  loadLeads()
  loadContacts()
  loadStats()
})

// ─── UPCOMING DATES ────────────────────────────────────────
async function loadUpcomingDates() {
  const [{ data: events }, { data: people }] = await Promise.all([
    sb.from('contact_events').select('*, contacts(name)'),
    sb.from('contact_people').select('*, contacts(name)').not('birthday', 'is', null),
  ])

  const today    = new Date(); today.setHours(0,0,0,0)
  const in30     = new Date(today); in30.setDate(today.getDate() + 30)
  const upcoming = []

  ;(events || []).forEach(ev => {
    const d = nextOccurrence(ev.date, ev.recurs_yearly)
    if (d >= today && d <= in30)
      upcoming.push({ label: ev.label, name: ev.contacts?.name, date: d })
  })

  ;(people || []).forEach(p => {
    const d = nextOccurrence(p.birthday, true)
    if (d >= today && d <= in30)
      upcoming.push({ label: `${p.name}'s Birthday`, name: p.contacts?.name, date: d })
  })

  upcoming.sort((a, b) => a.date - b.date)

  const el = document.getElementById('upcomingDates')
  if (!upcoming.length) {
    el.innerHTML = '<p class="empty">Nothing in the next 30 days.</p>'
    return
  }

  el.innerHTML = upcoming.map(u => {
    const days = Math.ceil((u.date - today) / 86400000)
    return `
      <div class="date-item">
        <div class="date-item-label">${esc(u.label)}</div>
        ${u.name ? `<div class="date-item-name">${esc(u.name)}</div>` : ''}
        <div class="date-item-days">
          ${days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : `In ${days} days`}
          — ${u.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </div>
      </div>
    `
  }).join('')
}

// ─── QUICK STATS ───────────────────────────────────────────
async function loadStats() {
  const [leads, subscribers, contacts, converted] = await Promise.all([
    sb.from('leads').select('id', { count: 'exact' }).eq('status', 'new'),
    sb.from('subscribers').select('id', { count: 'exact' }).eq('active', true),
    sb.from('contacts').select('id', { count: 'exact' }),
    sb.from('leads').select('id', { count: 'exact' }).eq('status', 'converted'),
  ])

  document.getElementById('statNewLeads').textContent    = leads.count ?? '—'
  document.getElementById('statSubscribers').textContent = subscribers.count ?? '—'
  document.getElementById('statContacts').textContent    = contacts.count ?? '—'
  document.getElementById('statConverted').textContent   = converted.count ?? '—'
}

// ─── HELPERS ───────────────────────────────────────────────
function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function nextOccurrence(dateStr, recurs) {
  const d = new Date(dateStr + 'T00:00:00')
  if (!recurs) return d
  const today = new Date(); today.setHours(0,0,0,0)
  d.setFullYear(today.getFullYear())
  if (d < today) d.setFullYear(today.getFullYear() + 1)
  return d
}

function esc(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
