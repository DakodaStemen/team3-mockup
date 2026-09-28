import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { GraphCanvas, lightTheme, darkTheme } from 'reagraph'

type Course = { id: string; title: string; catalog_units: number; roadmap_units: number | null; discrepancy_flag: boolean; term_offered: string; placeholder: boolean }
type Edge = { from_course: string; to_course: string; condition: string; grade_minimum: string }
type Term = { term_label: string; courses: string[]; total_units: number; warnings: string[] }
type Plan = { student_id: string; unit_cap: number; summers: string[]; credited: Record<string, string>; terms: Term[] }
type Timeline = { graduation_term: string; term_count: number; total_units: number; critical_path: string[] }
type Student = { id: string; name: string; completed_courses: Record<string, string>; in_progress_courses: string[]; unit_load_preference: number; notes: string }
type Move = { course: string; from: string; to: string }
type Result = { plan: Plan; timeline: Timeline; invalidated: string[]; delta_terms: number; moved: Move[]; explanation: string }
type Guardrail = { input: string; outcome: string; confidence: number; reason: string | null; parsed_event: unknown }
type Audit = Guardrail & { timestamp: string }
type Catalog = { courses: Course[]; edges: Edge[]; priority: Record<string, number>; discrepancies: string[] }
type Health = { engine: boolean; ollama: boolean; model: string; unit_load_range: [number, number] }
type Event = { event_type: string; course_id: string; term_label: string; unit_load: number }
type Saved = { plan: Plan; timeline: Timeline; label: string }

const COURSE_EVENTS = ['Fail', 'Withdraw', 'Pass']
const EVENTS = [...COURSE_EVENTS, 'Add Summer', 'Change Unit Load']
const CAPS = Array.from({ length: 19 }, (_, i) => i + 3)  // 3..21, the engine's allowed range

const UNREACHABLE = "Can't reach the planner API. Is the backend running on port 8000?"

async function api<T>(path: string, body?: unknown): Promise<T> {
  let r: Response
  try {
    r = await fetch(`/api${path}`, body === undefined ? undefined : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
  } catch {
    throw new Error(UNREACHABLE)
  }
  const data = await r.json().catch(() => undefined)
  if (!r.ok) {
    // FastAPI sends a string for our 400/422s and a list of {loc, msg} for request validation errors.
    const detail = data?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (Array.isArray(detail) && detail.length) {
      const [d] = detail, where = (d.loc ?? []).filter((l: unknown) => l !== 'body').slice(-2).join('.')
      throw new Error(`${where ? `${where}: ` : ''}${d.msg}${detail.length > 1 ? ` (+${detail.length - 1} more)` : ''}`)
    }
    if (r.status === 413) throw new Error('That request is too large for the planner API.')
    throw new Error(r.status >= 500 ? UNREACHABLE : `${r.status} ${r.statusText}`)
  }
  if (data === undefined) throw new Error(UNREACHABLE)  // e.g. the dev server's HTML fallback
  return data as T
}

const errorText = (e: unknown) => e instanceof Error ? e.message : String(e)

// Follow the OS theme live, not just at first render.
const DARK = matchMedia('(prefers-color-scheme: dark)')
const useDark = () => useSyncExternalStore(cb => { DARK.addEventListener('change', cb); return () => DARK.removeEventListener('change', cb) }, () => DARK.matches)

const describe = (e: Event) => e.event_type === 'Add Summer' ? `Add ${e.term_label}`
  : e.event_type === 'Change Unit Load' ? `${e.unit_load}-unit cap from ${e.term_label}`
  : `${e.event_type} ${e.course_id} (${e.term_label})`

export default function App() {
  const [catalog, setCatalog] = useState<Catalog>()
  const [students, setStudents] = useState<Student[]>([])
  const [health, setHealth] = useState<Health>()
  const [sid, setSid] = useState('alex')
  const [baseCap, setBaseCap] = useState<number>()
  const [plan, setPlan] = useState<Plan>()
  const [timeline, setTimeline] = useState<Timeline>()
  const [history, setHistory] = useState<Saved[]>([])
  const [alts, setAlts] = useState<Record<string, { plan: Plan; timeline: Timeline }>>({})
  const [preview, setPreview] = useState<Result & { label: string }>()
  const [guard, setGuard] = useState<Guardrail>()
  const [audit, setAudit] = useState<Audit[]>([])
  const [error, setError] = useState('')
  const [ev, setEv] = useState<Event>({ event_type: 'Fail', course_id: '', term_label: '', unit_load: 12 })
  const [query, setQuery] = useState('What if I fail CSE 2020 in Spring 2027?')
  const [actionBusy, setActionBusy] = useState(false)
  const [loadedKey, setLoadedKey] = useState('')  // which student+cap the shown plan belongs to
  const planKey = `${sid}:${baseCap ?? ''}`
  const busy = actionBusy || loadedKey !== planKey || !catalog
  const generation = useRef(0)  // bumped whenever the saved plan is replaced; late answers for an older plan are dropped
  const scenarioRef = useRef<HTMLDivElement>(null)

  const courses = useMemo(() => Object.fromEntries((catalog?.courses ?? []).map(c => [c.id, c])), [catalog])
  const student = students.find(s => s.id === sid)
  const shown = preview?.plan ?? plan
  const invalid = new Set(preview?.invalidated ?? [])
  const movedFrom = Object.fromEntries((preview?.moved ?? []).map(m => [m.course, m.from]))
  const inPlan = new Set(shown?.terms.flatMap(t => t.courses) ?? [])
  const dark = useDark()

  const refreshAudit = () => api<Audit[]>('/audit?limit=15').then(setAudit)
  const refreshHealth = () => api<Health>('/health').then(setHealth, () => setHealth(undefined))
  // Runs a user action against the current saved plan; `apply` is skipped if the plan was replaced meanwhile.
  const run = async <T,>(fn: () => Promise<T>, apply: (r: T) => void) => {
    const gen = generation.current
    setError(''); setActionBusy(true)
    try {
      const r = await fn()
      if (gen === generation.current) apply(r)
    } catch (e) {
      if (gen === generation.current) setError(errorText(e))
    } finally { setActionBusy(false) }
  }

  useEffect(() => {
    Promise.all([api<Catalog>('/catalog'), api<Student[]>('/students')])
      .then(([c, s]) => { setCatalog(c); setStudents(s) }, e => setError(errorText(e)))
    refreshHealth()
    refreshAudit().catch(() => {})  // the audit trail is optional context
  }, [])
  useEffect(() => {
    let live = true  // a slower response for a previous student/cap must not overwrite this one
    const key = `${sid}:${baseCap ?? ''}`
    api<{ plan: Plan; timeline: Timeline; alternatives: typeof alts }>('/plan', { student_id: sid, unit_cap: baseCap ?? null })
      .then(r => {
        if (!live) return
        generation.current++
        setPlan(r.plan); setTimeline(r.timeline); setAlts(r.alternatives); setHistory([]); setPreview(undefined); setGuard(undefined)
        setLoadedKey(key)
      }, e => { if (live) { setError(errorText(e)); setLoadedKey(key) } })
    return () => { live = false }
  }, [sid, baseCap])

  // Planned courses ranked by the engine's priority score, with how many later planned courses each one gates.
  const bottlenecks = useMemo(() => {
    if (!catalog || !plan) return []
    const planned = new Set(plan.terms.flatMap(t => t.courses))
    const next: Record<string, string[]> = {}
    for (const e of catalog.edges) (next[e.from_course] ??= []).push(e.to_course)
    const gates = (id: string) => {
      const seen = new Set<string>(), stack = [id]
      while (stack.length) for (const d of next[stack.pop()!] ?? []) if (!seen.has(d)) { seen.add(d); stack.push(d) }
      return [...seen].filter(d => planned.has(d)).length
    }
    return catalog.courses.filter(c => planned.has(c.id) && !c.placeholder && catalog.priority[c.id] !== undefined)
      .sort((a, b) => catalog.priority[b.id] - catalog.priority[a.id] || a.id.localeCompare(b.id)).slice(0, 10)
      .map(c => ({ id: c.id, title: c.title, priority: catalog.priority[c.id], gates: gates(c.id) }))
  }, [catalog, plan])

  // Placements the data can't confirm: unknown offerings, roadmap disagreements, unpublished summer sections.
  const toConfirm = (shown?.terms ?? []).flatMap(t => t.warnings.filter(w => /confirm|disagree/.test(w)).map(w => ({ term: t.term_label, w })))

  // Summers the student could add: one after each Spring in the plan that isn't already on.
  const summerOptions = (plan?.terms ?? []).filter(t => t.term_label.startsWith('Spring'))
    .map(t => `Summer ${t.term_label.split(' ')[1]}`).filter(s => !plan?.summers.includes(s))

  // The saved plan changes under the form (keep, undo, new student), so snap the selection to what the plan has now.
  const form: Event = (() => {
    if (ev.event_type === 'Add Summer')
      return { ...ev, term_label: summerOptions.includes(ev.term_label) ? ev.term_label : summerOptions[0] ?? '' }
    const t = plan?.terms.find(t => t.term_label === ev.term_label) ?? plan?.terms[0]
    return { ...ev, term_label: t?.term_label ?? '', course_id: t?.courses.includes(ev.course_id) ? ev.course_id : t?.courses[0] ?? '' }
  })()
  const pick = (id: string) => {
    const t = plan?.terms.find(t => t.courses.includes(id))
    if (!t) return
    setEv(e => ({ ...e, event_type: COURSE_EVENTS.includes(e.event_type) ? e.event_type : 'Fail', term_label: t.term_label, course_id: id }))
    scenarioRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  const replacePlan = (p: Plan, t: Timeline) => {
    generation.current++
    setPlan(p); setTimeline(t); setPreview(undefined); setGuard(undefined)
  }

  const adopt = (p: Plan, t: Timeline, label: string) => {
    if (plan && timeline) setHistory(h => [...h, { plan, timeline, label }])
    replacePlan(p, t)
  }
  const undo = () => {
    const last = history.at(-1)
    if (!last) return
    replacePlan(last.plan, last.timeline); setHistory(h => h.slice(0, -1))
  }
  const reset = () => {
    const first = history[0]
    if (!first) return
    replacePlan(first.plan, first.timeline); setHistory([])
  }
  const changeStudent = (id: string) => { setError(''); setBaseCap(undefined); setSid(id) }
  const changeCap = (cap: number) => { setError(''); setBaseCap(cap) }
  const whatIf = () => {
    const event = { ...form, course_id: COURSE_EVENTS.includes(form.event_type) ? form.course_id : null,
                    unit_load: form.event_type === 'Change Unit Load' ? form.unit_load : null }
    const label = describe(form)
    setGuard(undefined)
    run(() => api<Result>('/scenario', { plan, event }), r => setPreview({ ...r, label }))
  }
  const ask = () => {
    const text = query
    run(() => api<{ guardrail: Guardrail; result: Result | null }>('/query', { text, plan }), r => {
      setGuard(r.guardrail); setPreview(r.result ? { ...r.result, label: `“${text}”` } : undefined)
    }).then(() => { refreshAudit().catch(() => {}); refreshHealth() })
  }

  const termCourses = plan?.terms.find(t => t.term_label === form.term_label)?.courses ?? []
  const status = (id: string) =>
    invalid.has(id) ? 'invalid' : student?.completed_courses[id] || student?.in_progress_courses.includes(id) ? 'done'
      : inPlan.has(id) ? 'planned' : 'unplanned'

  return (
    <main>
      <header>
        <div>
          <h1>Degree Pathway Planner</h1>
          <p className="muted">Mock · the deterministic engine schedules; AI only parses questions</p>
        </div>
        <div className="controls">
          {busy && <span className="pill">working…</span>}
          {health && <span role="status" className={`pill ${health.ollama ? 'on' : 'off'}`} title={health.ollama ? `Using ${health.model}` : 'Start Ollama to enable plain-language parsing'}>
            AI parser {health.ollama ? 'online' : 'offline'}
          </span>}
          <label>Student
            <select value={sid} onChange={e => changeStudent(e.target.value)}>
              {students.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label>Unit cap
            <select value={plan?.unit_cap ?? ''} onChange={e => changeCap(+e.target.value)}>
              {CAPS.map(c => <option key={c} value={c}>{c}{c === student?.unit_load_preference ? ' (preferred)' : ''}</option>)}
            </select>
          </label>
        </div>
      </header>

      <p className="banner notice" role="note">
        Planning aid only: this is not an official degree audit or advising decision. Confirm your plan with an advisor.
      </p>

      {error && <div className="banner bad" role="alert">
        <span><strong>Error: </strong>{error}</span>
        <span className="actions"><button className="ghost" onClick={() => setError('')}>Dismiss</button></span>
      </div>}

      {catalog && <details className="banner warn">
        <summary>{catalog.discrepancies.length} catalog/roadmap discrepancies flagged for advisor review (catalog wins, never auto-resolved)</summary>
        <ul>{catalog.discrepancies.map(d => <li key={d}>{d}</li>)}</ul>
      </details>}

      {student && <section className="card">
        <h2>Starting point</h2>
        {student.notes && <p className="muted note">{student.notes}</p>}
        <p className="chips">
          {Object.entries(student.completed_courses).map(([c, g]) => <span key={`done-${c}`} className="chip done">{c} · {g}</span>)}
          {student.in_progress_courses.map(c => <span key={`now-${c}`} className="chip">{c} · in progress</span>)}
          {!Object.keys(student.completed_courses).length && !student.in_progress_courses.length && <span className="muted">No completed courses.</span>}
        </p>
      </section>}

      {timeline && <section className="stats">
        <Stat label="Graduation" value={preview ? `${timeline.graduation_term} → ${preview.timeline.graduation_term}` : timeline.graduation_term} />
        <Stat label="Terms" value={String(preview?.timeline.term_count ?? timeline.term_count)} />
        <Stat label="Units" value={String(preview?.timeline.total_units ?? timeline.total_units)} />
        <Stat label="Unit cap" value={String(shown?.unit_cap)} />
        <div className="stat wide"><span className="muted">Critical path</span><span>{(preview?.timeline ?? timeline).critical_path.join(' → ')}</span></div>
      </section>}

      {preview && <div className={`banner ${preview.delta_terms > 0 ? 'bad' : 'ok'}`} data-testid="whatif">
        <div className="grow">
          <p><strong>What-if ({preview.label}): </strong>{preview.explanation}</p>
          {preview.moved.length > 0 && <details className="moved">
            <summary>{preview.moved.length} course{preview.moved.length === 1 ? '' : 's'} moved</summary>
            <ul>{preview.moved.map(m => <li key={m.course}>{m.course}: {m.from} → {m.to}</li>)}</ul>
          </details>}
        </div>
        <span className="actions">
          <button onClick={() => adopt(preview.plan, preview.timeline, preview.label)}>Keep this plan</button>
          <button className="ghost" onClick={() => { setPreview(undefined); setGuard(undefined) }}>Discard</button>
        </span>
      </div>}

      <section className="grid2">
        <div className="card" ref={scenarioRef}>
          <h2>What-if scenario</h2>
          <p className="muted hint">Tip: click any course in the plan or the graph to load it here.</p>
          <div className="form">
            <select aria-label="Event" value={form.event_type} onChange={e => setEv({ ...form, event_type: e.target.value })}>
              {EVENTS.map(x => <option key={x}>{x}</option>)}
            </select>
            {form.event_type === 'Add Summer'
              ? summerOptions.length
                ? <select aria-label="Summer term" value={form.term_label} onChange={e => setEv({ ...form, term_label: e.target.value })}>
                    {summerOptions.map(s => <option key={s}>{s}</option>)}
                  </select>
                : <span className="muted">Every summer in this plan is already on.</span>
              : <select aria-label="Term" value={form.term_label} onChange={e => setEv({ ...form, term_label: e.target.value, course_id: '' })}>
                  {plan?.terms.map(t => <option key={t.term_label}>{t.term_label}</option>)}
                </select>}
            {COURSE_EVENTS.includes(form.event_type) &&
              <select aria-label="Course" value={form.course_id} onChange={e => setEv({ ...form, course_id: e.target.value })}>
                {termCourses.map(c => <option key={c}>{c}</option>)}
              </select>}
            {form.event_type === 'Change Unit Load' &&
              <select aria-label="New unit load" value={form.unit_load} onChange={e => setEv({ ...form, unit_load: +e.target.value })}>
                {CAPS.map(c => <option key={c} value={c}>{c} units</option>)}
              </select>}
            <button disabled={busy || !plan || !form.term_label || (COURSE_EVENTS.includes(form.event_type) && !form.course_id)} onClick={whatIf}>Run what-if</button>
          </div>
        </div>
        <div className="card">
          <h2>Ask in plain language</h2>
          {health && !health.ollama && <p className="muted hint">The AI parser is offline, so questions are escalated to a human. That is the guardrail working.</p>}
          <div className="form">
            <input aria-label="Question" className="grow" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && !busy && ask()} />
            <button disabled={busy || !plan} onClick={ask}>Ask</button>
          </div>
          {guard && <p className={`guard ${guard.outcome}`} data-testid="guard">
            <strong>{guard.outcome.replace(/_/g, ' ')}</strong> · confidence {guard.confidence?.toFixed(2) ?? "n/a"}
            {guard.reason && <> · {guard.reason}</>}
          </p>}
        </div>
      </section>

      <section className="grid2">
        <div className="card">
          <h2>Alternative pathways</h2>
          <div className="form">
            {Object.entries(alts).map(([name, a]) => (
              <button key={name} className="ghost" onClick={() => adopt(a.plan, a.timeline, `${name} pathway`)}>
                {name} ({a.plan.unit_cap}u cap): {a.timeline.graduation_term}, peak {Math.max(...a.plan.terms.map(t => t.total_units))}u
              </button>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>Plan history</h2>
          {!history.length ? <p className="muted">Showing the engine's baseline plan. Kept what-ifs stack up here.</p> : <>
            <ol className="history">
              <li className="muted">Baseline: {history[0].timeline.graduation_term}</li>
              {history.map((h, i) => <li key={i}>{h.label} → {(history[i + 1]?.timeline ?? timeline)?.graduation_term}</li>)}
            </ol>
            <div className="form">
              <button className="ghost" onClick={undo}>Undo last</button>
              <button className="ghost" onClick={reset}>Reset to baseline</button>
            </div>
          </>}
        </div>
      </section>

      <section className="terms" data-testid="terms">
        {shown?.terms.map(t => (
          <div key={t.term_label} className="term">
            <h3>{t.term_label} <span className="muted">{t.total_units}u</span></h3>
            {t.courses.map(c => (
              <button key={c} type="button" className={`course ${invalid.has(c) ? 'invalid' : ''} ${shown.credited[c] ? 'passed' : ''}`}
                      title={`${courses[c]?.title ?? c}. Click to load into the what-if form.`} onClick={() => pick(c)}>
                <span>{c}{shown.credited[c] && <span aria-label="passed"> ✓</span>}{invalid.has(c) && ' (affected)'}
                  {movedFrom[c] && <span className="was"> was {movedFrom[c]}</span>}
                </span>
                <span className="muted">
                  {['Fall', 'Spring'].includes(courses[c]?.term_offered) && `${courses[c]?.term_offered} only · `}{courses[c]?.catalog_units}u
                  {courses[c]?.discrepancy_flag && <span className="flag" title={`Roadmap says ${courses[c].roadmap_units}u`} aria-label={`roadmap says ${courses[c].roadmap_units} units`}> ⚑</span>}
                </span>
              </button>
            ))}
            {t.warnings.filter(w => !/confirm|disagree/.test(w)).map(w => <p key={w} className="warning">{w}</p>)}
          </div>
        ))}
      </section>

      {toConfirm.length > 0 && <details className="card confirm">
        <summary><h2>{toConfirm.length} placements to confirm with the department</h2></summary>
        <p className="muted">The plan assumes these offerings. The data can't confirm them: the course is on no roadmap, roadmaps disagree, or summer sections aren't published.</p>
        <ul>{toConfirm.map(({ term, w }) => <li key={term + w}><strong>{term}:</strong> {w}</li>)}</ul>
      </details>}

      {bottlenecks.length > 0 && <section className="card">
        <h2>Bottleneck courses in this plan</h2>
        <p className="muted">Top 10 planned courses by priority score (direct dependents + longest downstream chain + 1 if offered once a year). "Gates" counts the later courses in this plan that depend on it.</p>
        <table>
          <thead><tr><th>Course</th><th>Priority</th><th>Gates</th><th>Title</th></tr></thead>
          <tbody>
            {bottlenecks.map(b => (
              <tr key={b.id} className="clickable" onClick={() => pick(b.id)}>
                <td>{b.id}</td><td>{b.priority}</td><td>{b.gates} course{b.gates === 1 ? '' : 's'}</td>
                <td className="muted">{b.title}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>}

      {catalog && <section className="card">
        <h2>Prerequisite DAG</h2>
        <p className="muted">Grey = completed · blue = planned · red = affected by the current what-if · faded = not in this plan. Dashed = one of several alternatives. Click a node to load it.</p>
        <div className="graph">
          <GraphCanvas
            theme={dark ? darkTheme : lightTheme}
            layoutType="treeTd2d"
            onNodeClick={n => pick(n.id)}
            nodes={catalog.courses.map(c => ({ id: c.id, label: c.id, fill: { invalid: '#d64545', done: '#9aa3ad', planned: '#3a7bd5', unplanned: dark ? '#3a3f47' : '#dde1e6' }[status(c.id)] }))}
            edges={catalog.edges.map(e => ({ id: `${e.from_course}>${e.to_course}`, source: e.from_course, target: e.to_course, dashed: e.condition === 'OR' }))}
          />
        </div>
      </section>}

      <section className="card">
        <h2>Guardrail audit trail</h2>
        {!audit.length ? <p className="muted">No AI decisions yet.</p> : <table>
          <thead><tr><th>Time</th><th>Outcome</th><th>Confidence</th><th>Question</th><th>Reason</th></tr></thead>
          <tbody>
            {audit.map((a, i) => (
              <tr key={i}>
                <td className="muted">{a.timestamp.slice(0, 19).replace('T', ' ')}</td>
                <td className={`guard ${a.outcome}`}>{a.outcome.replace(/_/g, ' ')}</td>
                <td>{a.confidence?.toFixed(2)}</td>
                <td>{a.input}</td>
                <td className="muted">{a.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>}
      </section>
    </main>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="stat"><span className="muted">{label}</span><span>{value}</span></div>
}
