/* Parse the first markdown table in a string into { headers, rows }.
   Shared by pages that read live .md files from the vault. */
export function parseMarkdownTable(md) {
  const lines = md.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('|'))
  if (lines.length < 2) return { headers: [], rows: [] }
  const split = (l) => l.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
  const headers = split(lines[0])
  const rows = lines.slice(2).map(split).filter((r) => r.length === headers.length)
  return { headers, rows }
}

export const colIndex = (headers, name) => headers.findIndex((h) => h.includes(name))
