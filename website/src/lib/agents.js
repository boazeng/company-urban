/* Canonical agent roster + short role labels, shared across pages.
   Kept in the frontend so labels render without depending on a backend deploy;
   the comms backend's /agents.roles (when present) takes precedence at runtime. */

export const AGENT_ORDER = [
  'רונית', 'רן', 'מנכ״ל', 'סמנכ״ל כספים', 'סמנכ״ל תפעול', 'עומרי', 'גיא', 'זובין',
]

export const AGENT_ROLES = {
  'רונית': 'סמנכ״לית שיווק',
  'רן': 'עוזר אישי ומרכזן',
  'מנכ״ל': 'CEO',
  'סמנכ״ל כספים': 'CFO',
  'סמנכ״ל תפעול': 'COO',
  'עומרי': 'ניטור מתקני חניה',
  'גיא': 'שירות לקוחות חניה',
  'זובין': 'מנצח — תזמון',
}
