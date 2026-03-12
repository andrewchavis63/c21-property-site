import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://allpantherproperties.com',
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
        from: 'C21 Alliance Leads <onboarding@resend.dev>',
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
