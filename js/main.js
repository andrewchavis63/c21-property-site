/* ============================================
   C21 ALLIANCE PROPERTIES — MAIN JS (v2)
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* --- SCROLL PROGRESS BAR --- */
  const progressBar = document.getElementById('scroll-progress');

  /* --- NAVBAR SCROLL EFFECT + PARALLAX --- */
  const navbar    = document.getElementById('navbar');
  const heroBg    = document.querySelector('.hero-bg');
  const heroWmL   = document.querySelector('.hero-wm-left');
  const heroWmR   = document.querySelector('.hero-wm-right');

  window.addEventListener('scroll', () => {
    const scrollY   = window.scrollY;
    const docHeight = document.body.scrollHeight - window.innerHeight;

    /* progress bar */
    if (progressBar) progressBar.style.width = `${(scrollY / docHeight) * 100}%`;

    /* navbar */
    navbar.classList.toggle('scrolled', scrollY > 40);

    /* hero parallax */
    if (heroBg)   heroBg.style.transform   = `translateY(${scrollY * 0.28}px)`;
    if (heroWmL)  heroWmL.style.transform  = `translateY(${scrollY * 0.16}px)`;
    if (heroWmR)  heroWmR.style.transform  = `translateY(${scrollY * 0.12}px)`;
  }, { passive: true });


  /* --- MOBILE MENU --- */
  const hamburger  = document.querySelector('.hamburger');
  const mobileMenu = document.querySelector('.mobile-menu');
  const mobileLinks = mobileMenu.querySelectorAll('a');

  const toggleMenu = (open) => {
    hamburger.classList.toggle('open', open);
    mobileMenu.classList.toggle('open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  };

  hamburger.addEventListener('click', () => {
    toggleMenu(!hamburger.classList.contains('open'));
  });

  mobileLinks.forEach(link => {
    link.addEventListener('click', () => toggleMenu(false));
  });


  /* --- HERO FADE-IN ON LOAD --- */
  setTimeout(() => {
    document.querySelectorAll('.hero-label, .hero-title, .hero-subtitle, .hero-actions, .hero-photo-wrap').forEach(el => {
      el.classList.add('animate');
    });
  }, 120);


  /* --- HERO FLOAT CARDS --- */
  setTimeout(() => {
    document.querySelectorAll('.hero-float-left, .hero-float-right').forEach(el => {
      el.classList.add('loaded');
    });
  }, 900);


  /* --- WORD-BY-WORD REVEAL (section titles on scroll) --- */
  function splitWords(el, delayPerWord = 0.08) {
    const nodes = Array.from(el.childNodes);
    el.innerHTML = '';
    let idx = 0;

    nodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) {
        node.textContent.split(/(\s+)/).forEach(part => {
          if (/\S/.test(part)) {
            const span = document.createElement('span');
            span.className = 'word';
            span.style.transitionDelay = `${idx * delayPerWord}s`;
            span.textContent = part;
            el.appendChild(span);
            idx++;
          } else if (part) {
            el.appendChild(document.createTextNode(part));
          }
        });
      } else if (node.nodeName === 'EM' || node.nodeName === 'STRONG') {
        const wrapper = document.createElement(node.nodeName.toLowerCase());
        node.textContent.split(/(\s+)/).forEach(part => {
          if (/\S/.test(part)) {
            const span = document.createElement('span');
            span.className = 'word';
            span.style.transitionDelay = `${idx * delayPerWord}s`;
            span.textContent = part;
            wrapper.appendChild(span);
            idx++;
          } else if (part) {
            wrapper.appendChild(document.createTextNode(part));
          }
        });
        el.appendChild(wrapper);
      } else {
        el.appendChild(node.cloneNode(true));
      }
    });
  }

  const titleObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          titleObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.25, rootMargin: '0px 0px -30px 0px' }
  );

  document.querySelectorAll('.section-title').forEach(el => {
    el.classList.remove('reveal', 'reveal-delay-1', 'reveal-delay-2', 'reveal-delay-3');
    splitWords(el, 0.09);
    titleObserver.observe(el);
  });


  /* --- SCROLL REVEAL --- */
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => {
    revealObserver.observe(el);
  });


  /* --- FLUID NAV (shared factory) --- */
  function initFluidNav(navId, triggerId, itemsId) {
    const nav     = document.getElementById(navId);
    const trigger = document.getElementById(triggerId);
    const items   = document.getElementById(itemsId);
    if (!nav || !trigger || !items) return null;

    const open = () => {
      nav.classList.add('expanded');
      trigger.setAttribute('aria-expanded', 'true');
    };

    const close = () => {
      items.querySelectorAll('.fn-item').forEach(item => {
        item.style.transitionDelay = '0ms';
      });
      nav.classList.remove('expanded');
      trigger.setAttribute('aria-expanded', 'false');
      setTimeout(() => {
        items.querySelectorAll('.fn-item').forEach(item => {
          item.style.transitionDelay = '';
        });
      }, 320);
    };

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      nav.classList.contains('expanded') ? close() : open();
    });

    return { nav, close };
  }

  const nav = initFluidNav('fluidNavRight', 'fnTriggerRight', 'fnItemsRight');

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (nav && nav.nav.classList.contains('expanded') && !nav.nav.contains(e.target)) nav.close();
  });


  /* --- ACTIVE NAV LINK ON SCROLL --- */
  const sections   = document.querySelectorAll('section[id]');
  const navAnchors = document.querySelectorAll('#fnItemsRight .fn-item[href^="#"]');

  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          navAnchors.forEach(a => {
            const matches = a.getAttribute('href') === `#${id}`;
            a.classList.toggle('active', matches);
          });
        }
      });
    },
    { threshold: 0.4 }
  );

  sections.forEach(s => sectionObserver.observe(s));


  /* --- BACK TO TOP --- */
  const backToTop = document.getElementById('backToTop');

  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }


  /* --- CONTACT FORM --- */
  const form        = document.getElementById('contactForm');
  const formWrap    = document.getElementById('formWrap');
  const formSuccess = document.getElementById('formSuccess');

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const btn = form.querySelector('.form-submit');
      btn.disabled = true;
      btn.textContent = 'Sending...';

      const name    = `${form.querySelector('[name="firstName"]').value} ${form.querySelector('[name="lastName"]').value}`.trim();
      const email   = form.querySelector('[name="email"]').value;
      const phone   = form.querySelector('[name="phone"]')?.value || '';
      const message = [
        form.querySelector('[name="propertyAddress"]')?.value ? `Property: ${form.querySelector('[name="propertyAddress"]').value}` : '',
        form.querySelector('[name="propertyType"]')?.value    ? `Type: ${form.querySelector('[name="propertyType"]').value}` : '',
        form.querySelector('[name="currentStatus"]')?.value   ? `Status: ${form.querySelector('[name="currentStatus"]').value}` : '',
        form.querySelector('[name="message"]')?.value         || '',
      ].filter(Boolean).join('\n');

      // 1. Save to admin portal (Supabase)
      await fetch('https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/handle-contact-form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, phone, message, source: 'contact_form' }),
      }).catch(() => {}); // non-blocking — DB failure shouldn't block email

      // 2. Send email notification (Formspree)
      const formData = new FormData();
      formData.append('name', name);
      formData.append('email', email);
      formData.append('phone', phone);
      formData.append('message', message);
      const response = await fetch('https://formspree.io/f/xlgwkdkn', {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        body: formData,
      });

      if (response.ok) {
        formWrap.style.display = 'none';
        formSuccess.classList.add('visible');
      } else {
        btn.disabled = false;
        btn.innerHTML = 'Send My Request <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
        alert('Something went wrong. Please try again or email us directly at SarenaSSmith@gmail.com.');
      }
    });
  }


  /* --- COUNTER ANIMATION --- */
  const counters = document.querySelectorAll('[data-count]');
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  counters.forEach(c => counterObserver.observe(c));

  function animateCounter(el) {
    const target   = parseFloat(el.dataset.count);
    const suffix   = el.dataset.suffix || '';
    const prefix   = el.dataset.prefix || '';
    const duration = 1600;
    const start    = performance.now();
    const isDecimal = String(target).includes('.');

    const tick = (now) => {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      const value    = eased * target;
      el.textContent = prefix + (isDecimal ? value.toFixed(1) : Math.floor(value)) + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }


  /* --- FAQ ACCORDION --- */
  document.querySelectorAll('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      // close all
      document.querySelectorAll('.faq-q').forEach(b => {
        b.setAttribute('aria-expanded', 'false');
        b.nextElementSibling.classList.remove('open');
        b.closest('.faq-item').classList.remove('open');
      });
      // open clicked if it was closed
      if (!expanded) {
        btn.setAttribute('aria-expanded', 'true');
        btn.nextElementSibling.classList.add('open');
        btn.closest('.faq-item').classList.add('open');
      }
    });
  });


  /* --- HERO BEAM ANIMATION --- */
  (function initHeroBeams() {
    const hero = document.getElementById('home')
               || document.querySelector('.criteria-hero')
               || document.querySelector('.ps-hero')
               || document.querySelector('.svc-hero');
    if (!hero) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'heroBeamsCanvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;filter:blur(28px);opacity:0.55;';
    const heroBgEl = hero.querySelector('.hero-bg');
    if (heroBgEl) {
      heroBgEl.insertAdjacentElement('afterend', canvas);
    } else {
      hero.insertBefore(canvas, hero.firstChild);
    }

    const ctx = canvas.getContext('2d');
    const BEAM_COUNT = 22;
    let beams = [];

    function createBeam(w, h) {
      return {
        x: Math.random() * w * 1.5 - w * 0.25,
        y: Math.random() * h * 1.5 - h * 0.25,
        width: 28 + Math.random() * 55,
        length: h * 2.5,
        angle: -35 + Math.random() * 10,
        speed: 0.5 + Math.random() * 1.0,
        opacity: 0.10 + Math.random() * 0.14,
        hue: 36 + Math.random() * 18,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.018 + Math.random() * 0.025,
      };
    }

    function resetBeam(beam, index, w, h) {
      const col     = index % 3;
      const spacing = w / 3;
      beam.y        = h + 100;
      beam.x        = col * spacing + spacing / 2 + (Math.random() - 0.5) * spacing * 0.5;
      beam.width    = 90 + Math.random() * 90;
      beam.speed    = 0.45 + Math.random() * 0.4;
      beam.hue      = 36 + (index * 18) / BEAM_COUNT;
      beam.opacity  = 0.14 + Math.random() * 0.10;
    }

    function resize() {
      const dpr      = window.devicePixelRatio || 1;
      const w        = hero.offsetWidth;
      const h        = hero.offsetHeight;
      canvas.width   = w * dpr;
      canvas.height  = h * dpr;
      canvas.style.width  = w + 'px';
      canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);
      beams = Array.from({ length: BEAM_COUNT }, () => createBeam(w, h));
    }

    function drawBeam(beam) {
      ctx.save();
      ctx.translate(beam.x, beam.y);
      ctx.rotate(beam.angle * Math.PI / 180);
      const pulsingOpacity = beam.opacity * (0.8 + Math.sin(beam.pulse) * 0.2);
      const g = ctx.createLinearGradient(0, 0, 0, beam.length);
      g.addColorStop(0,   `hsla(${beam.hue},70%,62%,0)`);
      g.addColorStop(0.1, `hsla(${beam.hue},70%,62%,${pulsingOpacity * 0.5})`);
      g.addColorStop(0.4, `hsla(${beam.hue},70%,62%,${pulsingOpacity})`);
      g.addColorStop(0.6, `hsla(${beam.hue},70%,62%,${pulsingOpacity})`);
      g.addColorStop(0.9, `hsla(${beam.hue},70%,62%,${pulsingOpacity * 0.5})`);
      g.addColorStop(1,   `hsla(${beam.hue},70%,62%,0)`);
      ctx.fillStyle = g;
      ctx.fillRect(-beam.width / 2, 0, beam.width, beam.length);
      ctx.restore();
    }

    function animate() {
      const w = hero.offsetWidth;
      const h = hero.offsetHeight;
      ctx.clearRect(0, 0, w, h);
      beams.forEach((beam, i) => {
        beam.y     -= beam.speed;
        beam.pulse += beam.pulseSpeed;
        if (beam.y + beam.length < -100) resetBeam(beam, i, w, h);
        drawBeam(beam);
      });
      requestAnimationFrame(animate);
    }

    resize();
    window.addEventListener('resize', resize, { passive: true });
    animate();
  })();

});
