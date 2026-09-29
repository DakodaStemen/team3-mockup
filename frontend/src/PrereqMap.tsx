import { useMemo, useState } from 'react'

type Edge = { from_course: string; to_course: string; condition: string }
type Move = { course: string; from: string; to: string }
export type NodeState = 'done' | 'planned' | 'critical' | 'invalid' | 'unplanned'

// Layout constants in SVG user units.
const NODE_W = 86, NODE_H = 30, NARROW_W = 44, GAP = 32, ROW_H = 42, LANE_H = 10, TOP = 52, PAD = 12

type Link = { key: string; from: string; to: string; kind: 'AND' | 'OR' | 'move' }
const isDummy = (id: string) => id.includes('@')
const isGhost = (id: string) => id.startsWith('~')

/**
 * The prerequisite graph laid out on the plan's own timeline: one column per term (terms with no linked
 * courses stay as narrow bands), so every arrow points forward in time and a what-if visibly pushes courses
 * right. A moved course leaves a dashed ghost in its old term. Long edges route through reserved row slots
 * (Sugiyama-style dummy points in thin lanes), so they never pass behind another course.
 * Hovering a course lights its full prerequisite chain and everything it unlocks.
 */
export function PrereqMap({ columns, edges, stateOf, criticalPath, moved, onceAYear, onPick }: {
  columns: { label: string; courses: string[] }[]
  edges: Edge[]
  stateOf: (id: string) => NodeState
  criticalPath: string[]
  moved: Move[]
  onceAYear: (id: string) => boolean  // Fall- or Spring-only: marked on the node
  onPick: (id: string) => void
}) {
  const [focus, setFocus] = useState<string>()

  const layout = useMemo(() => {
    const colOf = new Map<string, number>()
    columns.forEach((c, i) => c.courses.forEach(id => colOf.set(id, i)))
    const visible = edges.filter(e => colOf.has(e.from_course) && colOf.has(e.to_course))
    // Only courses that take part in a dependency belong on a dependency map.
    const linked = new Set(visible.flatMap(e => [e.from_course, e.to_course]))
    const links: Link[] = visible.map(e => ({ key: `${e.from_course}>${e.to_course}`, from: e.from_course, to: e.to_course, kind: e.condition === 'OR' ? 'OR' : 'AND' }))
    const cols = columns.map(c => c.courses.filter(id => linked.has(id)))
    // Ghosts: where each moved course sat before the what-if.
    for (const m of moved) {
      const from = columns.findIndex(c => c.label === m.from)
      if (from < 0 || !linked.has(m.course)) continue
      const ghost = `~${m.course}`
      cols[from].push(ghost); colOf.set(ghost, from)
      links.push({ key: `${ghost}>${m.course}`, from: ghost, to: m.course, kind: 'move' })
    }
    const wide = cols.map(c => c.length > 0)

    // Long forward edges get one dummy point per column they cross.
    const route = new Map<string, string[]>()
    for (const l of links) {
      const a = colOf.get(l.from)!, b = colOf.get(l.to)!, dummies: string[] = []
      for (let c = a + 1; c < b; c++) { const d = `${l.key}@${c}`; cols[c].push(d); dummies.push(d) }
      route.set(l.key, [l.from, ...dummies, l.to])
    }
    for (const c of cols) c.sort()

    // Barycenter ordering over the segments: sweeps that pull each item toward its neighbours' rows.
    // ponytail: heuristic, not crossing-minimal; fine at ~70 nodes.
    const prev: Record<string, string[]> = {}, next: Record<string, string[]> = {}
    for (const pts of route.values()) for (let i = 1; i < pts.length; i++) {
      if (colOf.get(pts[i - 1]) === colOf.get(pts[i])) continue
      ;(prev[pts[i]] ??= []).push(pts[i - 1]); (next[pts[i - 1]] ??= []).push(pts[i])
    }
    const row = new Map<string, number>()
    cols.forEach(cs => cs.forEach((id, r) => row.set(id, r)))
    const mean = (ids: string[] | undefined, own: number) =>
      ids?.length ? ids.reduce((s, id) => s + (row.get(id) ?? 0), 0) / ids.length : own
    for (let sweep = 0; sweep < 8; sweep++) {
      const nb = sweep % 2 ? next : prev
      for (const i of sweep % 2 ? [...cols.keys()].reverse() : cols.keys()) {
        cols[i] = cols[i].map(id => [id, mean(nb[id], row.get(id)!)] as const).sort((a, b) => a[1] - b[1]).map(([id]) => id)
        cols[i].forEach((id, r) => row.set(id, r))
      }
    }

    // Empty ends drop (no completed work, nothing left out); empty terms in between stay as narrow bands.
    const first = wide.indexOf(true), last = wide.lastIndexOf(true)
    const shown = first < 0 ? [] : [...cols.keys()].slice(first, last + 1)
    const left: number[] = [], width: number[] = []
    let x = PAD
    for (const i of shown) { left[i] = x; width[i] = wide[i] ? NODE_W : NARROW_W; x += width[i] + GAP }
    const pos = new Map<string, { x: number; y: number }>()
    // Courses take a full row; a long edge passing through only needs a thin lane.
    let bottom = TOP
    for (const i of shown) {
      let y = TOP
      for (const id of cols[i]) {
        if (isDummy(id)) { pos.set(id, { x: left[i], y: y - NODE_H / 2 + LANE_H / 2 }); y += LANE_H }
        else { pos.set(id, { x: left[i], y }); y += ROW_H }
      }
      bottom = Math.max(bottom, y)
    }

    // Spread each node's ports down its side so arrowheads don't pile up at one point.
    const port = new Map<string, number>()
    const outs: Record<string, string[]> = {}, ins: Record<string, string[]> = {}
    for (const [key, pts] of route) { (outs[pts[0]] ??= []).push(key); (ins[pts.at(-1)!] ??= []).push(key) }
    for (const [lists, end] of [[outs, 'out'], [ins, 'in']] as const) for (const [id, keys] of Object.entries(lists)) {
      const other = (k: string) => { const p = route.get(k)!; return pos.get(end === 'out' ? p[1] : p.at(-2)!)?.y ?? 0 }
      keys.sort((a, b) => other(a) - other(b))
        .forEach((k, i) => port.set(`${end}:${k}`, (pos.get(id)?.y ?? 0) + NODE_H * (i + 1) / (keys.length + 1)))
    }

    return { links, route, shown, left, width, wide, pos, port, prev, next, w: Math.max(x - GAP + PAD, 1), h: Math.max(bottom, TOP + ROW_H) }
  }, [columns, edges, moved])

  // The focused course's whole chain: everything before it and everything it unlocks.
  const chain = useMemo(() => {
    if (!focus) return undefined
    const seen = new Set([focus])
    for (const dir of [layout.prev, layout.next]) {
      const stack = [focus]
      while (stack.length) for (const n of dir[stack.pop()!] ?? []) if (!seen.has(n)) { seen.add(n); stack.push(n) }
    }
    return seen
  }, [focus, layout])

  const critical = new Set(criticalPath.flatMap((c, i) => i ? [`${criticalPath[i - 1]}>${c}`] : []))

  const path = (l: Link) => {
    const pts = layout.route.get(l.key)!
    const a = layout.pos.get(pts[0]), b = layout.pos.get(pts.at(-1)!)
    if (!a || !b) return ''
    const y0 = layout.port.get(`out:${l.key}`)!, y1 = layout.port.get(`in:${l.key}`)!
    if (a.x === b.x)  // same term (corequisite): loop out to the right
      return `M${a.x + NODE_W} ${y0} C${a.x + NODE_W + 26} ${y0} ${a.x + NODE_W + 26} ${y1} ${a.x + NODE_W} ${y1}`
    if (b.x < a.x)  // backward: an alternative outside the plan feeding a planned course
      return `M${a.x} ${y0} C${a.x - 40} ${y0} ${b.x + NODE_W + 40} ${y1} ${b.x + NODE_W + 2} ${y1}`
    // Forward: curve across each gap, run straight through each reserved slot.
    let d = `M${a.x + NODE_W} ${y0}`, x = a.x + NODE_W, y = y0
    const curve = (x2: number, y2: number) => { const m = (x + x2) / 2; d += ` C${m} ${y} ${m} ${y2} ${x2} ${y2}`; x = x2; y = y2 }
    for (const id of pts.slice(1, -1)) {
      const col = +id.slice(id.lastIndexOf('@') + 1), ry = layout.pos.get(id)!.y + NODE_H / 2
      curve(layout.left[col], ry)
      x = layout.left[col] + layout.width[col]; d += ` L${x} ${ry}`
    }
    curve(b.x - 2, y1)
    return d
  }

  const { w, h } = layout
  return (
    <div className="map-scroll">
      <svg className="map" viewBox={`0 0 ${w} ${h}`} style={{ minWidth: w, maxWidth: w * 1.5 }}
           role="group" aria-roledescription="prerequisite map">
        <defs>
          <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" className="hatch-bg" />
            <line x1="0" y1="0" x2="0" y2="6" className="hatch-line" />
          </pattern>
          {['arrow', 'arrow-hi', 'arrow-move'].map(id => (
            <marker key={id} id={id} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 8 4 0 8z" className={id} />
            </marker>
          ))}
        </defs>

        {layout.shown.map((i, n) => {
          const [season, year] = columns[i].label.split(' ')
          const cx = layout.left[i] + layout.width[i] / 2
          return (
            <g key={columns[i].label}>
              {n % 2 === 1 && <rect className="map-band" x={layout.left[i] - GAP / 2} y={0} width={layout.width[i] + GAP} height={h} />}
              <text className={`map-col ${layout.wide[i] ? '' : 'empty'}`} textAnchor="middle">
                <tspan x={cx} y={18}>{season}</tspan>{year && <tspan x={cx} y={32}>{year}</tspan>}
              </text>
            </g>
          )
        })}

        {layout.links.map(l => {
          const lit = chain?.has(l.from) && chain.has(l.to)
          const history = stateOf(l.from) === 'done' && stateOf(l.to) === 'done'  // both already behind the student
          const cls = ['edge', history && 'past', l.kind === 'OR' && 'or', l.kind === 'move' && 'move', critical.has(l.key) && 'crit',
                       l.kind !== 'move' && stateOf(l.to) === 'invalid' && 'bad', lit && 'lit', chain && !lit && 'dim'].filter(Boolean).join(' ')
          const marker = l.kind === 'move' ? 'url(#arrow-move)' : lit ? 'url(#arrow-hi)' : 'url(#arrow)'
          return <path key={l.key} d={path(l)} className={cls} markerEnd={marker} />
        })}

        {[...layout.pos].filter(([id]) => !isDummy(id)).map(([id, p]) => {
          if (isGhost(id)) return (
            <g key={id} className={`node ghost ${chain && !chain.has(id) ? 'dim' : ''}`} transform={`translate(${p.x} ${p.y})`} aria-hidden="true">
              <rect width={NODE_W} height={NODE_H} rx={6} />
              <text x={NODE_W / 2} y={NODE_H / 2 + 4.5} textAnchor="middle">{id.slice(1)}</text>
            </g>
          )
          const s = stateOf(id)
          const cls = ['node', s, chain && (chain.has(id) ? 'lit' : 'dim'), focus === id && 'focus'].filter(Boolean).join(' ')
          return (
            <g key={id} className={cls} transform={`translate(${p.x} ${p.y})`} tabIndex={0} role="button"
               aria-label={`${id}${s === 'invalid' ? ', affected' : s === 'done' ? ', completed' : s === 'unplanned' ? ', not in plan' : ''}`}
               onMouseEnter={() => setFocus(id)} onMouseLeave={() => setFocus(undefined)}
               onFocus={() => setFocus(id)} onBlur={() => setFocus(undefined)}
               onClick={() => onPick(id)} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(id))}>
              <rect width={NODE_W} height={NODE_H} rx={6} />
              <text x={NODE_W / 2} y={NODE_H / 2 + 4.5} textAnchor="middle">{id}</text>
              {onceAYear(id) && <circle className="once-dot" cx={NODE_W - 1} cy={1} r={4.5}><title>Offered once a year</title></circle>}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
