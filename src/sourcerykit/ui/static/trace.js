/**
 * Renders a trace from GET /api/traces/{id}.
 *
 * The SDK stores one row per intercepted call. The Question, claim, proof,
 * verdict and Final Answer steps are all derived from that list. Model names,
 * per-step durations and a "fetching tools" step have no source in the data and
 * are left out rather than faked.
 *
 * Nothing here uses innerHTML: every value from the wire reaches the page as a
 * text node, so an agent answer containing markup stays inert.
 */
import { icon } from './trace-icons.js'
import {
  activityStatusFromOutcome,
  allFieldClaims,
  fieldClaims,
  markdown,
  rollUpStatus,
  statusMark,
} from './trace-data.js'

const NO_ANSWER = 'No answer recorded'

const STATUS_LABEL = {
  verified: 'Verified',
  verifying: 'Verifying',
  caught: 'Caught',
  error: 'Error',
  healed: 'Healed',
  pending: 'Pending',
  intercepted: 'Intercepted',
}

const STEP_GLYPH = {
  question: 'messageCircleQuestion',
  tool_call: 'wrench',
  claim: 'quote',
  handover: 'bot',
  proof: 'badgeCheck',
  evaluation: 'badgeCheck',
  final: 'flag',
}

// ---------------------------------------------------------------- DOM helpers

/**
 * `el('div.card', {attr: value}, ...children)`. Children may be nodes, strings,
 * arrays, or null for "render nothing".
 */
function el(spec, attrs, ...children) {
  const [tag, ...classes] = spec.split('.')
  const node = document.createElement(tag || 'div')
  if (classes.length) node.className = classes.join(' ')
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue
    if (name === 'onclick') node.addEventListener('click', value)
    else node.setAttribute(name, value === true ? '' : String(value))
  }
  append(node, children)
  return node
}

function append(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)))
  }
}

function sized(glyph, size) {
  glyph.setAttribute('width', size)
  glyph.setAttribute('height', size)
  return glyph
}

// -------------------------------------------------------------------- helpers

function pretty(value) {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

/** server.py sends a naive UTC timestamp, so read it as UTC and say so. */
function formatStamp(iso) {
  if (!iso) return ''
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`
  )
}

function formatProofDate(iso) {
  return formatStamp(iso) || '—'
}

function verdictSubtitle(disagreed, unverified, total) {
  const noun = total === 1 ? 'claim' : 'claims'
  if (disagreed > 0 && unverified > 0) {
    return `${disagreed} of ${total} ${noun} disagreed, ${unverified} could not be verified`
  }
  if (disagreed > 0) return `${disagreed} of ${total} ${noun} disagreed`
  return `${unverified} of ${total} ${noun} could not be verified`
}

function interceptBlocks(ic) {
  const blocks = [{ caption: 'URL', value: ic.source_url }]
  if (ic.actual_value !== undefined && ic.actual_value !== null) {
    blocks.push({ caption: 'Response', tag: 'JSON', value: pretty(ic.actual_value) })
  }
  return blocks
}

function proofBlocks(ic) {
  const blocks = []
  if (ic.query_id) blocks.push({ caption: 'Query record', value: ic.query_id })
  blocks.push({ caption: 'Verification mode', value: ic.verification_mode })
  for (const fc of fieldClaims(ic)) {
    blocks.push({ caption: 'Claimed', tag: fc.path, value: fc.claimed })
    blocks.push({ caption: 'Indexed', tag: fc.path, value: fc.indexed ?? 'nothing indexed' })
  }
  if (ic.details) blocks.push({ caption: 'Details', value: ic.details })
  return blocks
}

function hasBody(step) {
  return step.blocks.length > 0 || step.prose.length > 0 || step.claims.length > 0
}

function proofStatusOf(outcome) {
  const status = activityStatusFromOutcome(outcome)
  return status === 'intercepted' ? 'pending' : status
}

// --------------------------------------------------------------------- pieces

function statusBadge(status) {
  return el(
    'span.sk-status',
    { status, variant: 'mark' },
    el('span.sr-only', {}, `Trace status: `),
    el(
      'span.badge',
      {},
      el('span.bare', {}, statusMark(status)),
      el('span', {}, STATUS_LABEL[status]),
    ),
  )
}

function activityBadge(status) {
  const showDot = ['verified', 'caught', 'error', 'healed'].includes(status)
  return el(
    'span.sk-abadge',
    { status },
    el(
      'span.badge',
      {},
      status === 'intercepted' ? sized(icon('scanLine'), 12) : null,
      status === 'pending' ? sized(icon('loaderCircle'), 12) : null,
      showDot ? el('span.dot', {}) : null,
      el('span', {}, STATUS_LABEL[status]),
    ),
  )
}

function detailBlock({ caption, tag, value, tone = 'default' }) {
  const copyButton = el('button.icon-button.copy', {
    'aria-label': `Copy ${caption}`,
    onclick: (event) => {
      const button = event.currentTarget
      navigator.clipboard?.writeText(String(value))
      button.replaceChildren(icon('check'))
      button.setAttribute('aria-label', 'Copied')
      setTimeout(() => {
        button.replaceChildren(icon('copy'))
        button.setAttribute('aria-label', `Copy ${caption}`)
      }, 1200)
    },
  })
  copyButton.append(icon('copy'))

  return el(
    'div.sk-detail',
    { tone },
    caption ? el('span.caption', {}, caption) : null,
    el(
      'div.box',
      {},
      tag ? el('div.tag', {}, tag) : null,
      el('pre.value', {}, String(value)),
      copyButton,
    ),
  )
}

function claimCard(claim) {
  const tone = claim.agrees ? 'default' : claim.outcome === 'ERROR' ? 'error' : 'caught'
  const label = claim.agrees
    ? 'Agrees'
    : claim.outcome === 'ERROR'
      ? 'Not verified'
      : 'Disagrees'

  return el(
    'div.sk-claim',
    { tone },
    el(
      'div.card',
      {},
      el(
        'div.head',
        {},
        claim.path ? el('span.path', { title: claim.path }, claim.path) : null,
        claim.verificationMode ? el('span.chip', {}, claim.verificationMode) : null,
        el('span.action', {}, claim.actionName),
        el(
          'span.mark',
          { title: label },
          el('span.dot', {}),
          el('span.sr-only', {}, label),
        ),
      ),
      el(
        'div.rows',
        {},
        el(
          'div.row',
          {},
          el('span.label', {}, 'Claimed:'),
          el('span.value.claimed', {}, claim.claimed),
        ),
        el(
          'div.row',
          {},
          el('span.label', {}, 'Indexed:'),
          el(
            'span.value',
            {},
            claim.indexed === null
              ? el('span.missing', {}, 'nothing indexed')
              : claim.indexed,
          ),
        ),
      ),
      !claim.agrees && claim.details ? el('p.details', {}, claim.details) : null,
    ),
  )
}

function summaryCard(counts) {
  const row = (glyphName, name, value) =>
    el(
      'div.row',
      {},
      el('span.name', {}, sized(icon(glyphName), 12), el('span', {}, name)),
      el('span.value', {}, value),
    )

  // The host and the card stay separate elements, as they were when this was a
  // custom element: the card carries the border and fill, the host the layout.
  const host = el('div.sk-summary', {})
  const card = el('section.card', { 'aria-labelledby': 'summary-heading' })
  host.append(card)

  const paint = () => {
    const collapsed = host.hasAttribute('collapsed')
    const toggle = el('button.icon-button', {
      'aria-expanded': collapsed ? 'false' : 'true',
      'aria-label': collapsed ? 'Expand summary' : 'Collapse summary',
      onclick: () => {
        host.toggleAttribute('collapsed', !collapsed)
        paint()
      },
    })
    toggle.append(icon(collapsed ? 'chevronDown' : 'chevronUp'))

    const children = [
      el('div.head', {}, el('h2', { id: 'summary-heading' }, 'Summary'), toggle),
    ]
    if (!collapsed) {
      children.push(
        el(
          'div.rows',
          {},
          row('wrench', 'Tool calls', String(counts.toolCalls)),
          row('badgeCheck', 'Proofs', String(counts.proofs)),
          row('quote', 'Claims', String(counts.claims)),
          row('triangleAlert', 'Caught', String(counts.caught)),
          // The SDK records no timings, so the row stays hidden.
          counts.durationSeconds === null
            ? null
            : row('clock4', 'Duration', `${counts.durationSeconds.toFixed(1)}s`),
        ),
      )
    }
    card.replaceChildren(...children)
  }

  paint()
  return host
}

function proofList(proofs) {
  const many = proofs.length > 1
  const host = el('div.sk-proofs', {})
  const card = el('section.card', { 'aria-labelledby': 'proofs-heading' })
  host.append(card)

  const disabledButton = (spec, label, glyphName, ariaLabel) => {
    const button = el(spec, { disabled: true, 'aria-disabled': 'true', 'aria-label': ariaLabel })
    button.append(icon(glyphName))
    if (label) button.append(el('span', {}, label))
    return button
  }

  const item = (p, last) =>
    el(
      `div.item${last ? '.last' : ''}`,
      {},
      el(
        'div.item-head',
        {},
        el('span.file-glyph', {}, icon('file')),
        el(
          'span.meta',
          {},
          el(
            'span.name',
            {},
            el(
              'span.status',
              { 'data-status': p.status },
              el('span.dot', {}),
              el('span', {}, STATUS_LABEL[p.status]),
            ),
            el('span.text', { title: p.queryId }, p.queryId),
          ),
          el('span.date', {}, formatProofDate(p.generatedAt)),
        ),
      ),
      el(
        'div.item-actions',
        {},
        disabledButton('button.outline-button', 'Re-verify', 'rotateCcw', null),
        disabledButton(
          'button.outline-button.square',
          null,
          'download',
          `Download proof ${p.queryId}`,
        ),
      ),
    )

  // The items are direct children of the card, as in the design: no wrapper
  // element, so collapsing re-renders rather than hiding a box.
  const paint = () => {
    const collapsed = host.hasAttribute('collapsed')
    const actions = el('span.actions', { style: 'min-height:24px' })
    if (many) {
      actions.append(
        disabledButton('button.icon-button.tight', null, 'rotateCcw', 'Re-verify all proofs'),
        disabledButton('button.icon-button.tight', null, 'download', 'Download all proofs'),
      )
      const toggle = el('button.icon-button.tight', {
        'aria-expanded': collapsed ? 'false' : 'true',
        'aria-label': collapsed ? 'Expand proofs' : 'Collapse proofs',
        onclick: () => {
          host.toggleAttribute('collapsed', !collapsed)
          paint()
        },
      })
      toggle.append(icon(collapsed ? 'chevronDown' : 'chevronUp'))
      actions.append(toggle)
    }

    const children = [
      el(
        'div.head',
        {},
        el('h2', { id: 'proofs-heading' }, many ? 'Proofs' : 'Proof'),
        many ? el('span.count', {}, String(proofs.length)) : null,
        actions,
      ),
    ]

    if (!collapsed) {
      if (proofs.length === 0) {
        children.push(el('p.empty', {}, 'No proofs recorded for this trace.'))
      } else {
        children.push(...proofs.map((p, i) => item(p, i === proofs.length - 1)))
        if (many) {
          children.push(
            el(
              'div.footer',
              {},
              disabledButton('button.outline-button', 'Re-verify all', 'rotateCcw', null),
              disabledButton('button.outline-button', 'Download all', 'download', null),
            ),
          )
        }
      }
    }

    card.replaceChildren(...children)
  }

  paint()
  return host
}

function activityStep(step, index, total, isOpen, onToggle) {
  const bodied = hasBody(step)
  const glyphName =
    step.tone === 'error'
      ? 'circleX'
      : step.tone === 'caught'
        ? 'triangleAlert'
        : step.kind === 'proof'
          ? 'badgeCheck'
          : STEP_GLYPH[step.kind]

  const base = step.subtitle ? `${step.label} ${step.subtitle}` : step.label
  const name = `${base}, step ${index + 1} of ${total}`

  const headerContent = [
    el(
      'span.title',
      {},
      el('span', { id: `step-label-${index}`, title: step.label }, step.label),
      step.subtitle ? el('span.subtitle', {}, step.subtitle) : null,
    ),
    el(
      'span.trailing',
      {},
      step.status ? activityBadge(step.status) : null,
      // Always the down chevron: CSS rotates it when the step is open, so the
      // turn animates instead of the glyph swapping under the pointer.
      bodied ? el('span.chevron', { 'aria-hidden': 'true' }, icon('chevronDown')) : null,
    ),
  ]

  const header = bodied
    ? el(
        'button.header',
        {
          'aria-expanded': isOpen ? 'true' : 'false',
          'aria-controls': isOpen ? `step-content-${index}` : null,
          'aria-label': isOpen ? `Collapse ${name}` : `Expand ${name}`,
          onclick: onToggle,
        },
        headerContent,
      )
    : el('div.header', {}, headerContent)

  const content =
    bodied && isOpen
      ? el(
          'div.content',
          {
            id: `step-content-${index}`,
            role: 'region',
            'aria-labelledby': `step-label-${index}`,
          },
          step.prose
            ? step.richProse
              ? markdown(step.prose)
              : el('p.prose', {}, step.prose)
            : null,
          step.claims.length
            ? el('div.claim-cards', {}, step.claims.map(claimCard))
            : null,
          step.blocks.length
            ? el('div.blocks', {}, step.blocks.map(detailBlock))
            : null,
        )
      : null

  return el(
    'div.sk-step',
    {
      kind: step.kind,
      tone: step.tone,
      first: index === 0,
      last: index === total - 1,
      open: isOpen,
      'no-content': !bodied,
      separator: step.separator,
    },
    el(
      'div.rail',
      { 'aria-hidden': 'true' },
      el('span.line.top', {}),
      el('span.glyph', {}, icon(glyphName)),
      el('span.line.rest', {}),
    ),
    el('div.body', {}, el('div.card', {}, header, content)),
  )
}

// ----------------------------------------------------------------- the view

/**
 * Turns the flat intercept list into the step timeline the design shows.
 */
function buildSteps(data) {
  const steps = [
    {
      kind: 'question',
      label: 'Question',
      subtitle: '',
      blocks: [],
      prose: data.trace.task,
      richProse: false,
      claims: [],
      separator: false,
      status: null,
      tone: 'default',
      openByDefault: true,
    },
  ]

  for (const ic of data.intercepts) {
    steps.push({
      kind: 'tool_call',
      label: ic.action_name,
      subtitle: '',
      blocks: interceptBlocks(ic),
      prose: '',
      richProse: false,
      claims: [],
      separator: false,
      status: 'intercepted',
      tone: 'default',
      openByDefault: false,
    })
  }

  const drafted = allFieldClaims(data.intercepts)
  if (drafted.length > 0) {
    steps.push({
      kind: 'claim',
      label: drafted.length === 1 ? 'Drafted claim' : `Drafted ${drafted.length} claims`,
      subtitle: '',
      blocks: drafted.map((fc) => ({
        caption: 'Claimed',
        tag: fc.path || fc.actionName,
        value: fc.claimed,
      })),
      prose: '',
      richProse: false,
      claims: [],
      separator: false,
      status: null,
      tone: 'default',
      openByDefault: false,
    })
  }

  const proofs = data.intercepts.filter((ic) => ic.query_id)
  proofs.forEach((ic, i) => {
    const status = activityStatusFromOutcome(ic.outcome)
    steps.push({
      kind: 'proof',
      label: 'Proof',
      subtitle: `${i + 1} of ${proofs.length}`,
      blocks: proofBlocks(ic),
      prose: '',
      richProse: false,
      claims: [],
      separator: false,
      status,
      tone: status === 'caught' ? 'caught' : status === 'error' ? 'error' : 'default',
      openByDefault: false,
    })
  })

  if (proofs.length > 0) {
    steps.push({
      kind: 'handover',
      label: 'Claims handed over to agent',
      subtitle: '',
      blocks: [],
      prose: '',
      richProse: false,
      claims: [],
      separator: true,
      status: null,
      tone: 'default',
      openByDefault: false,
    })
  }

  const cards = allFieldClaims(data.intercepts)
  const disagreed = cards.filter((c) => c.outcome === 'CAUGHT')
  const unverified = cards.filter((c) => c.outcome === 'ERROR')

  if (disagreed.length > 0 || unverified.length > 0) {
    steps.push({
      kind: 'evaluation',
      label: disagreed.length > 0 ? 'Drift caught' : 'Verification error',
      // The summary shows every claim, passing ones included, so the
      // denominator is visible rather than asserted.
      subtitle: verdictSubtitle(disagreed.length, unverified.length, cards.length),
      blocks: [],
      prose: '',
      richProse: false,
      claims: cards,
      separator: false,
      status: disagreed.length > 0 ? 'caught' : 'error',
      tone: disagreed.length > 0 ? 'caught' : 'error',
      openByDefault: true,
    })
  }

  // With no answer, a card headed "Final Answer" invites the reader to take the
  // placeholder for the answer. A bare row cannot be misread.
  steps.push({
    kind: 'final',
    label: data.trace.answer ? 'Final Answer' : NO_ANSWER,
    subtitle: '',
    blocks: [],
    prose: data.trace.answer,
    richProse: Boolean(data.trace.answer),
    claims: [],
    separator: !data.trace.answer,
    status: null,
    tone: 'default',
    openByDefault: true,
  })

  return steps
}

function countsFor(data) {
  return {
    toolCalls: data.intercepts.length,
    proofs: data.intercepts.filter((i) => i.query_id).length,
    claims: allFieldClaims(data.intercepts).length,
    caught: data.intercepts.filter((i) => i.outcome === 'CAUGHT').length,
    durationSeconds: null,
  }
}

function proofItemsFor(data) {
  return data.intercepts
    .filter((i) => i.query_id)
    .map((i) => ({
      queryId: i.query_id,
      // The endpoint sends no proof timestamp yet.
      generatedAt: null,
      status: proofStatusOf(i.outcome),
    }))
}

export class TraceView {
  constructor(host) {
    this.host = host
    this.host.classList.add('sk-view')
    this.data = null
    this.openSteps = new Set()
    this.inFlight = null
  }

  async load(traceId, baseUrl = '') {
    // The page sets the id after the module loads, so an empty id is "not yet",
    // not an error. Only a fetch that was actually attempted can fail.
    if (!traceId) {
      this.renderEmpty()
      return
    }

    this.inFlight?.abort()
    const controller = new AbortController()
    this.inFlight = controller
    this.renderSkeleton()

    try {
      const origin = (baseUrl || window.location.origin).replace(/\/$/, '')
      const res = await fetch(`${origin}/api/traces/${encodeURIComponent(traceId)}`, {
        signal: controller.signal,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Request failed with ${res.status}`)
      }
      this.data = await res.json()
      const steps = buildSteps(this.data)
      this.openSteps = new Set(
        steps.flatMap((s, i) => (s.openByDefault ? [i] : [])),
      )
      this.render()
    } catch (error) {
      if (controller.signal.aborted) return
      this.renderError(error instanceof Error ? error.message : String(error))
    }
  }

  renderEmpty() {
    const message = el('p.state', {})
    append(message, [
      'No trace selected. Open this page with ',
      el('code', {}, '?id=<trace id>'),
      ', or run ',
      el('code', {}, 'sourcerykit trace <id>'),
      '.',
    ])
    this.host.replaceChildren(message)
  }

  renderError(text) {
    this.data = null
    this.host.replaceChildren(el('p.state.error', { role: 'alert' }, text))
  }

  renderSkeleton() {
    const rows = [0, 1, 2, 3, 4].map(() =>
      el(
        'div.skeleton-row',
        {},
        el('span.skeleton-bar.glyph', {}),
        el('span.skeleton-bar.card', {}),
      ),
    )
    this.host.replaceChildren(
      el(
        'div.layout',
        { 'aria-busy': 'true' },
        el(
          'div.main',
          {},
          el('div.title-bar', {}, el('span.skeleton-bar.skeleton-title', {})),
          el('div.trail-bar', {}, el('span.skeleton-bar.skeleton-trail', {})),
          el('div.trail-skeleton', { 'aria-label': 'Loading trace' }, rows),
        ),
        el('div.divider', { 'aria-hidden': 'true' }),
        el(
          'div.aside',
          {},
          el(
            'div.aside-inner',
            {},
            el('span.skeleton-bar.skeleton-side', {}),
            el('span.skeleton-bar.skeleton-side', {}),
          ),
        ),
      ),
    )
  }

  get allOpen() {
    const expandable = buildSteps(this.data).filter(hasBody)
    return this.openSteps.size >= expandable.length && expandable.length > 0
  }

  toggleAll() {
    if (this.allOpen) {
      this.openSteps = new Set()
    } else {
      this.openSteps = new Set(
        buildSteps(this.data).flatMap((s, i) => (hasBody(s) ? [i] : [])),
      )
    }
    this.render()
  }

  render() {
    const { trace } = this.data
    const steps = buildSteps(this.data)
    const status = rollUpStatus(this.data.intercepts)
    const copy = (text) => navigator.clipboard?.writeText(text)

    const idButton = el('button.outline-button.trace-id', {
      title: trace.id,
      'aria-label': 'Copy trace id',
      onclick: () => copy(trace.id),
    })
    append(idButton, [
      el('span.muted', {}, 'ID:'),
      el('span.value', {}, trace.id),
      icon('copy'),
    ])

    const copyLink = el('button.icon-button', {
      'aria-label': 'Copy trace link',
      onclick: () => copy(window.location.href),
    })
    copyLink.append(icon('copy'))

    const expandAll = el('button.icon-button', {
      'aria-expanded': this.allOpen ? 'true' : 'false',
      'aria-label': this.allOpen ? 'Collapse all steps' : 'Expand all steps',
      onclick: () => this.toggleAll(),
    })
    expandAll.append(icon('chevronsUpDown'))

    const trail = el('ol.trail', {
      role: 'list',
      // tabindex makes the scroller reachable, so PageDown and the arrow keys
      // work. Chromium's focusable-scroller heuristic does not cover it: the
      // trail is full of buttons.
      tabindex: '0',
      'aria-labelledby': 'trail-heading',
    })
    steps.forEach((step, i) => {
      trail.append(
        el(
          'li',
          {},
          activityStep(step, i, steps.length, this.openSteps.has(i), () => {
            if (this.openSteps.has(i)) this.openSteps.delete(i)
            else this.openSteps.add(i)
            this.render()
          }),
        ),
      )
    })

    const asideInner = el('div.aside-inner', {})
    if (trace.answer) {
      // A long trail pushes the Final Answer step off the bottom, so the answer
      // is repeated here where it stays in view.
      asideInner.append(
        el(
          'section.answer-card',
          { 'aria-labelledby': 'answer-heading' },
          el('div.answer-head', {}, el('h2', { id: 'answer-heading' }, 'Final answer')),
          el('div.answer-body', {}, markdown(trace.answer)),
        ),
      )
    }
    asideInner.append(summaryCard(countsFor(this.data)), proofList(proofItemsFor(this.data)))

    this.host.replaceChildren(
      el(
        'div.layout',
        {},
        el(
          'div.main',
          {},
          el(
            'div.title-bar',
            {},
            el('h1', {}, 'Trace'),
            el('div.title-actions', {}, idButton, statusBadge(status)),
          ),
          el(
            'div.trail-bar',
            {},
            el(
              'div.trail-left',
              {},
              el('h2', { id: 'trail-heading' }, 'Activity Trail'),
              el(
                'span.steps-pill',
                {},
                `${steps.filter((s) => !s.separator).length} steps`,
              ),
              el('span.timestamp', {}, formatStamp(trace.created_at)),
            ),
            el('span.title-actions', {}, copyLink, expandAll),
          ),
          trail,
        ),
        el('div.divider', { 'aria-hidden': 'true' }),
        el(
          'div.aside',
          { role: 'region', tabindex: '0', 'aria-label': 'Trace summary and proofs' },
          asideInner,
        ),
      ),
    )
  }
}
