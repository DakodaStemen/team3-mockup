import { useEffect, useMemo, useState } from 'react'
import { GraphCanvas, lightTheme, darkTheme } from 'reagraph'

type Course = { id: string; title: string; catalog_units: number; roadmap_units: number | null; discrepancy_flag: boolean; term_offered: string }
type Edge = { from_course: string; to_course: string; condition: string; grade_minimum: string }
type Term = { term_label: string; courses: string[]; total_units: number; warnings: string[] }
type Plan = { student_id: string; unit_cap: number; summers: string[]; credited: string[]; terms: Term[] }
type Timeline = { graduation_term: string; term_count: number; total_units: number; critical_path: string[] }
type Student = { id: string; name: string; completed_courses: Record<string, string>; in_progress_courses: string[] }
type Result = { plan: Plan; timeline: Timeline; invalidated: string[]; delta_terms: number; explanation: string }
type Guardrail = { input: string; outcome: string; confidence: number; reason: string | null; parsed_event: unknown }
type Audit = Guardrail & { timestamp: string }
type Catalog = { courses: Course[]; edges: Edge[]; discrepancies: string[] }

const EVENTS = ['Fail', 'Withdraw', 'Pass', 'Add Summer', 'Change Unit Load']

async function api<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText)
  return r.json()
}

export default function App() {
  const [catalog, setCatalog] = useState<Catalog>()
  const [students, setStudents] = useState<Student[]>([])
  const [sid, setSid] = useState('alex')
  const [plan, setPlan] = useState<Plan>()
  const [timeline, setTimeline] = useState<Timeline>()
  const [alts, setAlts] = useState<Record<string, { plan: Plan; timeline: Timeline }>>({})
  const [preview, setPreview] = useState<Result>()
  const [guard, setGuard] = useState<Guardrail>()
  const [audit, setAudit] = useState<Audit[]>([])
  const [error, setError] = useState('')
  const [ev, setEv] = useState({ event_type: 'Fail', course_id: '', term_label: '', unit_load: 12 })
  const [query, setQuery] = useState('What if I fail CSE 2020 in Spring 2027?')
  const [busy, setBusy] = useState(false)

  const courses = useMemo(() => Object.fromEntries((catalog?.courses ?? []).map(c => [c.id, c])), [catalog])
  const student = students.find(s => s.id === sid)
  const shown = preview?.plan ?? plan
  const invalid = new Set(preview?.invalidated ?? [])

  const refreshAudit = () => api<Audit[]>('/audit?limit=15').then(setAudit)
  const run = async (fn: () => Promise<void>) => {
    setError(''); setBusy(true)
    try { await fn() } catch (e) { setError(String((e as Error).message)) } finally { setBusy(false) }
  }

  useEffect(() => { run(async () => {
    setCatalog(await api('/catalog')); setStudents(await api('/students')); await refreshAudit()
  }) }, [])
  useEffect(() => { run(async () => {
    const r = await api<{ plan: Plan; timeline: Timeline; alternatives: typeof alts }>('/plan', { student_id: sid })
    setPlan(r.plan); setTimeline(r.timeline); setAlts(r.alternatives); setPreview(undefined); setGuard(undefined)
    const t = r.plan.terms[0]
    setEv(e => ({ ...e, term_label: t.term_label, course_id: t.courses[0] }))
  }) }, [sid])

  const adopt = (p: Plan, t: Timeline) => { setPlan(p); setTimeline(t); setPreview(undefined) }
  const whatIf = () => run(async () => {
    const event = { ...ev, course_id: ev.event_type.startsWith('Add') || ev.event_type.startsWith('Change') ? null : ev.course_id }
    setGuard(undefined); setPreview(await api<Result>('/scenario', { plan, event }))
  })
  const ask = () => run(async () => {
    const r = await api<{ guardrail: Guardrail; result: Result | null }>('/query', { text: query, plan })
    setGuard(r.guardrail); setPreview(r.result ?? undefined); await refreshAudit()
  })

  const termCourses = plan?.terms.find(t => t.term_label === ev.term_label)?.courses ?? []
  const status = (id: string) =>
    invalid.has(id) ? 'invalid' : student?.completed_courses[id] || student?.in_progress_courses.includes(id) ? 'done' : 'planned'

  return (
    <main>
      <header>
        <div>
          <h1>Degree Pathway Planner</h1>
          <p className="muted">Mock · deterministic engine schedules, AI only parses questions</p>
        </div>
        <label>Student
          <select value={sid} onChange={e => setSid(e.target.value)}>
            {students.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
      </header>

      {error && <div className="banner bad" role="alert">{error}</div>}

      {catalog && <details className="banner warn">
        <summary>{catalog.discrepancies.length} catalog/roadmap discrepancies flagged for advisor review (catalog wins, never auto-resolved)</summary>
        <ul>{catalog.discrepancies.map(d => <li key={d}>{d}</li>)}</ul>
      </details>}

      {student && <section className="card">
        <h2>Starting point</h2>
        <p className="chips">
          {Object.entries(student.completed_courses).map(([c, g]) => <span key={c} className="chip done">{c} · {g}</span>)}
          {student.in_progress_courses.map(c => <span key={c} className="chip">{c} · in progress</span>)}
          {!Object.keys(student.completed_courses).length && <span className="muted">No completed courses.</span>}
        </p>
      </section>}

      {timeline && <section className="stats">
        <Stat label="Graduation" value={preview ? `${timeline.graduation_term} → ${preview.timeline.graduation_term}` : timeline.graduation_term} />
        <Stat label="Terms" value={String(preview?.timeline.term_count ?? timeline.term_count)} />
        <Stat label="Units" value={String(preview?.timeline.total_units ?? timeline.total_units)} />
        <Stat label="Unit cap" value={String(shown?.unit_cap)} />
        <div className="stat wide"><span className="muted">Critical path</span><span>{(preview?.timeline ?? timeline).critical_path.join(' → ')}</span></div>
      </section>}

      {preview && <div className={`banner ${preview.delta_terms > 0 ? 'bad' : 'ok'}`}>
        <strong>What-if: </strong>{preview.explanation}
        <span className="actions">
          <button onClick={() => adopt(preview.plan, preview.timeline)}>Keep this plan</button>
          <button className="ghost" onClick={() => { setPreview(undefined); setGuard(undefined) }}>Discard</button>
        </span>
      </div>}

      <section className="grid2">
        <div className="card">
          <h2>Scenario</h2>
          <div className="form">
            <select value={ev.event_type} onChange={e => setEv({ ...ev, event_type: e.target.value })}>
              {EVENTS.map(x => <option key={x}>{x}</option>)}
            </select>
            {ev.event_type === 'Add Summer'
              ? <input value={ev.term_label} onChange={e => setEv({ ...ev, term_label: e.target.value })} placeholder="Summer 2027" />
              : <select value={ev.term_label} onChange={e => {
                  const t = plan?.terms.find(t => t.term_label === e.target.value)
                  setEv({ ...ev, term_label: e.target.value, course_id: t?.courses[0] ?? '' })
                }}>{plan?.terms.map(t => <option key={t.term_label}>{t.term_label}</option>)}</select>}
            {['Fail', 'Withdraw', 'Pass'].includes(ev.event_type) &&
              <select value={ev.course_id} onChange={e => setEv({ ...ev, course_id: e.target.value })}>
                {termCourses.map(c => <option key={c}>{c}</option>)}
              </select>}
            {ev.event_type === 'Change Unit Load' &&
              <input type="number" min={3} max={21} value={ev.unit_load} onChange={e => setEv({ ...ev, unit_load: +e.target.value })} />}
            <button disabled={busy || !plan} onClick={whatIf}>Run what-if</button>
          </div>
        </div>
        <div className="card">
          <h2>Ask in plain language</h2>
          <div className="form">
            <input className="grow" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && ask()} />
            <button disabled={busy || !plan} onClick={ask}>Ask</button>
          </div>
          {guard && <p className={`guard ${guard.outcome}`}>
            <strong>{guard.outcome.replace(/_/g, ' ')}</strong> · confidence {guard.confidence.toFixed(2)}
            {guard.reason && <> · {guard.reason}</>}
          </p>}
        </div>
      </section>

      <section className="card">
        <h2>Alternative pathways</h2>
        <div className="form">
          {Object.entries(alts).map(([name, a]) => (
            <button key={name} className="ghost" onClick={() => adopt(a.plan, a.timeline)}>
              {name} ({a.plan.unit_cap}u cap): {a.timeline.graduation_term}, peak {Math.max(...a.plan.terms.map(t => t.total_units))}u
            </button>
          ))}
        </div>
      </section>

      <section className="terms">
        {shown?.terms.map(t => (
          <div key={t.term_label} className="term">
            <h3>{t.term_label} <span className="muted">{t.total_units}u</span></h3>
            {t.courses.map(c => (
              <div key={c} className={`course ${invalid.has(c) ? 'invalid' : ''}`} title={courses[c]?.title}>
                <span>{c}</span>
                <span className="muted">
                  {courses[c]?.term_offered !== 'Both' && `${courses[c]?.term_offered} only · `}{courses[c]?.catalog_units}u
                  {courses[c]?.discrepancy_flag && <span className="flag" title={`Roadmap says ${courses[c].roadmap_units}u`}> ⚑</span>}
                </span>
              </div>
            ))}
            {t.warnings.map(w => <p key={w} className="warning">{w}</p>)}
          </div>
        ))}
      </section>

      {catalog && <section className="card">
        <h2>Prerequisite DAG</h2>
        <p className="muted">Grey = completed · blue = planned · red = invalidated by the current what-if</p>
        <div className="graph">
          <GraphCanvas
            theme={matchMedia('(prefers-color-scheme: dark)').matches ? darkTheme : lightTheme}
            layoutType="treeTd2d"
            nodes={catalog.courses.map(c => ({ id: c.id, label: c.id, fill: { invalid: '#d64545', done: '#9aa3ad', planned: '#3a7bd5' }[status(c.id)] }))}
            edges={catalog.edges.map(e => ({ id: `${e.from_course}>${e.to_course}`, source: e.from_course, target: e.to_course, dashed: e.condition === 'OR' }))}
          />
        </div>
      </section>}

      <section className="card">
        <h2>Guardrail audit trail</h2>
        {!audit.length && <p className="muted">No AI decisions yet.</p>}
        <table>
          <tbody>
            {audit.map((a, i) => (
              <tr key={i}>
                <td className="muted">{a.timestamp.slice(0, 19).replace('T', ' ')}</td>
                <td className={`guard ${a.outcome}`}>{a.outcome}</td>
                <td>{a.confidence?.toFixed(2)}</td>
                <td>{a.input}</td>
                <td className="muted">{a.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="stat"><span className="muted">{label}</span><span>{value}</span></div>
}
