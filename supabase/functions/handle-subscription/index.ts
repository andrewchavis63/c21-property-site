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

    const { error: dbError } = await supabase
      .from('subscribers')
      .upsert(
        { email, name: name || null, source: source || 'c21_website', active: true },
        { onConflict: 'email' }
      )

    if (dbError) throw new Error(dbError.message)

    // Add subscriber to Beehiiv
    await fetch(`https://api.beehiiv.com/v2/publications/${Deno.env.get('BEEHIIV_PUBLICATION_ID')}/subscriptions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('BEEHIIV_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        reactivate_existing: false,
        send_welcome_email: true,
        utm_source: source || 'c21_website',
      }),
    })

    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('RESEND_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'C21 Alliance Leads <onboarding@resend.dev>',
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
