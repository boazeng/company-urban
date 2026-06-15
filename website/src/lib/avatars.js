/* Per-agent avatar portraits shown on the org-chart cards.
   Keyed by the agent's identity (the "סוכן" column in structure/Structure.md).
   Each value is the slug of a JPG in website/public/avatars/<slug>.jpg.

   The portraits are AI-generated (gpt-image-1), age- and gender-matched —
   employees read ~30-40, VPs ~40-50. Regenerate any of them with
   `python scripts/gen_avatars.py <slug>` (edit the prompt there first), or
   just drop a new JPG at public/avatars/<slug>.jpg — no code change needed. */

const AVATARS = {
  // ── הנהלה (VPs / management, ~40-50) ──
  'מנכ״ל':         { slug: 'ceo',            gender: 'm', age: '50-55' },
  'סמנכ״ל כספים':  { slug: 'cfo',            gender: 'm', age: '45-50' },
  'סמנכ״ל תפעול':  { slug: 'coo',            gender: 'm', age: '45-50' },
  'רונית':         { slug: 'ronit',          gender: 'f', age: '42-48' },
  'יובל':          { slug: 'yuval',          gender: 'm', age: '44-50' },
  'אמיר':          { slug: 'amir',           gender: 'm', age: '46-50' },
  'מרכז שליטה':    { slug: 'control-center', gender: 'm', age: '44-50' },
  'סמנכ״ל SaaS':   { slug: 'saas',           gender: 'm', age: '44-50' },

  // ── סוכנים / עוזרים (employees, ~30-40) ──
  'רן':            { slug: 'ran',            gender: 'm', age: '32-38' },
  'סוכן לידים':    { slug: 'leads',          gender: 'm', age: '34-40' },
  'ירון':          { slug: 'yaron',          gender: 'm', age: '30-36' },
  'גיא':           { slug: 'guy',            gender: 'm', age: '32-38' },
  'זובין':         { slug: 'zubin',          gender: 'm', age: '34-40' },
  'סיכום מיילים':  { slug: 'email-summary',  gender: 'm', age: '30-36' },
  'עומרי':         { slug: 'omri',           gender: 'm', age: '30-36' },
  'דפנה':          { slug: 'dafna',          gender: 'f', age: '32-38' },
  'דרור':          { slug: 'dror',           gender: 'm', age: '33-39' },
}

/* Public URL of an agent's portrait, or '' if none is mapped. */
export function avatarFor(name) {
  const a = AVATARS[name]
  return a ? `${import.meta.env.BASE_URL}avatars/${a.slug}.jpg` : ''
}

/* Initials shown while/if the portrait fails to load (graceful fallback). */
export function initialsFor(name) {
  if (!name) return '?'
  const clean = String(name).replace(/[״"׳']/g, '').trim()
  const parts = clean.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0])
  return clean.slice(0, 2)
}
