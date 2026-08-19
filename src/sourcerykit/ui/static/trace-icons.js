/**
 * Lucide glyphs used by the dashboard. Each path sits on a 24x24 box with
 * stroke-width 2 and is scaled by the consuming rule. `icon()` returns a fresh
 * element each call, so one glyph can appear in several places at once.
 */

const SVG_NS = 'http://www.w3.org/2000/svg'

const PATHS = {
  check: '<path d="M20 6 9 17l-5-5" />',
  x: '<path d="M18 6 6 18" /><path d="m6 6 12 12" />',
  copy:
    '<rect width="14" height="14" x="8" y="8" rx="2" ry="2" />' +
    '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />',
  download:
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />' +
    '<polyline points="7 10 12 15 17 10" />' +
    '<line x1="12" x2="12" y1="15" y2="3" />',
  chevronDown: '<path d="m6 9 6 6 6-6" />',
  chevronUp: '<path d="m18 15-6-6-6 6" />',
  chevronsUpDown: '<path d="m7 15 5 5 5-5" /><path d="m7 9 5-5 5 5" />',
  messageCircleQuestion:
    '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z" />' +
    '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />' +
    '<path d="M12 17h.01" />',
  wrench:
    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />',
  scanLine:
    '<path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" />' +
    '<path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" />' +
    '<path d="M7 12h10" />',
  quote:
    '<path d="M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1a1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" />' +
    '<path d="M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1a1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" />',
  badgeCheck:
    '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76" />' +
    '<path d="m9 12 2 2 4-4" />',
  flag:
    '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />' +
    '<line x1="4" x2="4" y1="22" y2="15" />',
  loaderCircle: '<path d="M21 12a9 9 0 1 1-6.219-8.56" />',
  triangleAlert:
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />' +
    '<path d="M12 9v4" /><path d="M12 17h.01" />',
  clock4: '<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />',
  rotateCcw:
    '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />' +
    '<path d="M3 3v5h5" />',
  file:
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />' +
    '<path d="M14 2v4a2 2 0 0 0 2 2h4" />',
  circleX:
    '<circle cx="12" cy="12" r="10" /><path d="m15 9-6 6" /><path d="m9 9 6 6" />',
  bot:
    '<path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" />' +
    '<path d="M2 14h2" /><path d="M20 14h2" />' +
    '<path d="M15 13v2" /><path d="M9 13v2" />',
}

const parser = new DOMParser()
const cache = new Map()

/** One glyph by name. The markup is author-written and static. */
export function icon(name) {
  if (!cache.has(name)) {
    const inner = PATHS[name]
    if (inner === undefined) throw new Error(`Unknown icon: ${name}`)
    const doc = parser.parseFromString(
      `<svg xmlns="${SVG_NS}" viewBox="0 0 24 24" fill="none"` +
        ' stroke="currentColor" stroke-width="2" stroke-linecap="round"' +
        ` stroke-linejoin="round" aria-hidden="true">${inner}</svg>`,
      'image/svg+xml',
    )
    cache.set(name, doc.documentElement)
  }
  return cache.get(name).cloneNode(true)
}
