/**
 * Pure trace logic for the static UI: outcome roll-up, field claims, the
 * markdown sliver and the status marks.
 *
 * Ported from the Lit build. Everything that used to return a `TemplateResult`
 * now returns real DOM, built node by node, so text stays escaped by
 * construction and nothing here ever touches innerHTML.
 */

const SVG_NS = 'http://www.w3.org/2000/svg'

/* ------------------------------------------------------------------ status */

/** A null outcome means the row has not resolved yet. */
export function activityStatusFromOutcome(outcome) {
  switch (outcome) {
    case 'PASS':
      return 'verified'
    case 'CAUGHT':
      return 'caught'
    case 'ERROR':
      return 'error'
    default:
      return 'pending'
  }
}

/**
 * Rolls per-row outcomes up to the header badge.
 *
 * Caught outranks everything: a trace that caught a hallucination must say so
 * even while another claim is still resolving. A trace with no intercepted
 * calls resolved nothing, so it reports `error` rather than sitting on a
 * spinner forever.
 */
export function rollUpStatus(intercepts) {
  if (intercepts.length === 0) return 'error'

  const outcomes = intercepts.map((i) => i.outcome)
  if (outcomes.includes('CAUGHT')) return 'caught'
  if (outcomes.includes('ERROR')) return 'error'
  if (outcomes.includes(null)) return 'verifying'
  return 'verified'
}

/* ------------------------------------------------------------------ claims */

/**
 * The SDK stores `claimed_value` as a JSON string holding
 * `[{path, value, sourcerykit_ref}]`, and `actual_value` as an object keyed by
 * the same path. `sourcerykit_ref` is an internal handle and never reaches the
 * screen.
 */

function scalar(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

/** Reads the indexed value at `path`, tolerating both key shapes the API uses. */
function indexedAt(actual, path) {
  if (actual === null || actual === undefined) return null
  if (typeof actual !== 'object') return scalar(actual)

  if (path in actual) return scalar(actual[path])

  // `$.current.temperature_2m` may also arrive as a nested object.
  const segments = path.replace(/^\$\.?/, '').split('.').filter(Boolean)
  let cursor = actual
  for (const segment of segments) {
    if (cursor === null || typeof cursor !== 'object') return null
    cursor = cursor[segment]
  }
  return cursor === undefined ? null : scalar(cursor)
}

/**
 * Expands one intercept into its field claims. An intercept whose
 * `claimed_value` is not the structured form yields a single claim carrying the
 * raw string, so nothing is silently dropped.
 */
export function fieldClaims(ic) {
  const base = {
    actionName: ic.action_name,
    verificationMode: ic.verification_mode,
    agrees: ic.outcome === 'PASS',
    outcome: ic.outcome,
    details: ic.details ?? '',
  }

  if (!ic.claimed_value) return []

  let parsed
  try {
    parsed = JSON.parse(ic.claimed_value)
  } catch {
    return [
      { ...base, path: '', claimed: ic.claimed_value, indexed: indexedAt(ic.actual_value, '') },
    ]
  }

  const list = Array.isArray(parsed) ? parsed : [parsed]
  return list.map((entry) => {
    const raw = entry ?? {}
    const path = typeof raw.path === 'string' ? raw.path : ''
    return {
      ...base,
      path,
      claimed: scalar(raw.value ?? entry),
      indexed: indexedAt(ic.actual_value, path),
    }
  })
}

/** Every field claim across a trace, in intercept order. */
export function allFieldClaims(intercepts) {
  return intercepts.flatMap(fieldClaims)
}

/* ---------------------------------------------------------------- markdown */

/**
 * The sliver of markdown the old CLI dashboard rendered in the agent's answer:
 * `**bold**`, `` `code` `` and `- ` list items. Agents return formatted
 * answers, so without this the raw asterisks and backticks show up on screen.
 */

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`)/g
const BULLET = /^\s*[-*]\s+(.*)$/

/** Splits one line into plain runs, bold runs and code runs. */
function inline(line) {
  const nodes = []
  for (const part of line.split(INLINE)) {
    if (part === '') continue
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      const strong = document.createElement('strong')
      strong.appendChild(document.createTextNode(part.slice(2, -2)))
      nodes.push(strong)
      continue
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      const code = document.createElement('code')
      code.appendChild(document.createTextNode(part.slice(1, -1)))
      nodes.push(code)
      continue
    }
    nodes.push(document.createTextNode(part))
  }
  return nodes
}

/**
 * Renders `text` as a list of blocks. Runs of bullet lines collapse into one
 * list; everything else stays a paragraph that keeps its own line breaks.
 */
export function markdown(text) {
  if (!text) return []

  const blocks = []
  let bullets = []
  let paragraph = []

  const flushBullets = () => {
    if (bullets.length === 0) return
    const ul = document.createElement('ul')
    for (const b of bullets) {
      const li = document.createElement('li')
      for (const node of inline(b)) li.appendChild(node)
      ul.appendChild(li)
    }
    blocks.push(ul)
    bullets = []
  }

  const flushParagraph = () => {
    if (paragraph.length === 0) return
    const p = document.createElement('p')
    p.className = 'prose'
    for (const node of inline(paragraph.join('\n'))) p.appendChild(node)
    blocks.push(p)
    paragraph = []
  }

  for (const line of text.split('\n')) {
    const bullet = BULLET.exec(line)
    if (bullet) {
      flushParagraph()
      bullets.push(bullet[1] ?? '')
      continue
    }
    if (line.trim() === '') {
      flushBullets()
      flushParagraph()
      continue
    }
    flushBullets()
    paragraph.push(line)
  }
  flushBullets()
  flushParagraph()

  return blocks
}

/* ------------------------------------------------------------------- marks */

/**
 * SourceryKit status marks.
 *
 * Each mark is a 3x3 grid of 5x5 cells on a 20x20 box, with a per-status
 * opacity pattern. The exported SVGs hardcode the status hex; here the fill is
 * `currentColor` so the same geometry works on a tinted and an on-colour
 * surface, and the opacity pattern is reproduced cell for cell.
 *
 * Cell order below is row-major: top-left, top-centre, top-right, then middle,
 * then bottom. A value of 0 means the cell is absent from the export.
 */

/** Verified: a solid plus, corners dimmed. */
const VERIFIED = [0.2, 1, 0.2, 1, 0.2, 1, 0.2, 1, 0.2]

/** Error: the inverse of verified, a solid X. */
const ERROR = [1, 0.2, 1, 0.2, 1, 0.2, 1, 0.2, 1]

/** Caught: a solid frame with a dimmed centre. */
const CAUGHT = [1, 1, 1, 1, 0.2, 1, 1, 1, 1]

/** Healed: a frame with the top and bottom centres dimmed. */
const HEALED = [1, 0.2, 1, 1, 1, 1, 1, 0.2, 1]

/** Loading: the export's ramp, kept as the still frame under reduced motion. */
const LOADING = [0.6, 0.8, 1, 0.4, 0, 0, 0.2, 0.1, 0]

const PATTERNS = {
  verified: VERIFIED,
  error: ERROR,
  caught: CAUGHT,
  healed: HEALED,
  verifying: LOADING,
}

/** Cell origins on the 20x20 box: 0, 7.5, 15 on both axes. */
const AXIS = [0, 7.5, 15]

/**
 * The eight outer cells, clockwise from the top left. The centre is left out:
 * the loading state runs the brightness around this ring.
 */
const RING = [0, 1, 2, 5, 8, 7, 6, 3]

function cell(index, opacity, cls = '') {
  const x = AXIS[index % 3]
  const y = AXIS[Math.floor(index / 3)]
  const path = document.createElementNS(SVG_NS, 'path')
  path.setAttribute('class', cls)
  path.setAttribute('style', cls ? `--i:${RING.indexOf(index)}` : '')
  path.setAttribute('d', `M${x} ${y}H${x + 5}V${y + 5}H${x}V${y}Z`)
  path.setAttribute('fill', 'currentColor')
  path.setAttribute('fill-opacity', String(opacity))
  return path
}

export function statusMark(status) {
  // Verifying is a chase: every ring cell is drawn, and CSS walks the highlight
  // around them. Rotating the whole mark instead reads as a stutter, because
  // the grid lands back on itself every quarter turn.
  const cells =
    status === 'verifying'
      ? RING.map((i) => cell(i, 1, 'chase'))
      : PATTERNS[status]
          .map((opacity, i) => ({ opacity, i }))
          .filter(({ opacity }) => opacity !== 0)
          .map(({ opacity, i }) => cell(i, opacity))

  const svg = document.createElementNS(SVG_NS, 'svg')
  svg.setAttribute('viewBox', '0 0 20 20')
  svg.setAttribute('fill', 'none')
  svg.setAttribute('aria-hidden', 'true')
  for (const node of cells) svg.appendChild(node)
  return svg
}
