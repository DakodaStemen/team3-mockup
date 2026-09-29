import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { PrereqMap, type NodeState } from './PrereqMap'
import { Logo } from './Logo'
import { apiFetch, STATIC, whenEngineReady } from './backend'
import { pdfToText } from './pdfText'

type Course = { id: string; title: string; catalog_units: number; roadmap_units: number | null; discrepancy_flag: boolean; term_offered: string; placeholder: boolean; requirement_groups: string[] }
type Edge = { from_course: string; to_course: string; condition: string; grade_minimum: string }
type Term = { term_label: string; courses: string[]; total_units: number; warnings: string[]; unit_cap?: number | null }
type Plan = { student_id: string; unit_cap: number; summers: string[]; winters: string[]; credited: Record<string, string>; terms: Term[] }
type Timeline = { graduation_term: string; term_count: number; total_units: number; critical_path: string[] }
type PastTerm = { term_label: string; grades: Record<string, string> }
type Student = { id: string; name: string; completed_courses: Record<string, string>; in_progress_courses: string[]; unit_load_preference: number; notes: string; history: PastTerm[] }
type Risk = Record<string, { term: string; delay: number; catch_up: string[]; after_catch_up: number }>
type Report = { terms: string[]; courses: number; transfer: string[]; unrecognized: string[]; unread: string[]; start_term: string; unit_load_preference: number; file: string }
// A slot in the year grid: a completed term from the student's history, or a planned term.
type Slot = { label: string; past?: PastTerm; term?: Term }
type Move = { course: string; from: string; to: string }
type Result = { plan: Plan; timeline: Timeline; invalidated: string[]; delta_terms: number; moved: Move[]; explanation: string
                recovery?: (Result & { adds: string[] }) | null }
type Catalog = { courses: Course[]; edges: Edge[]; priority: Record<string, number>; discrepancies: string[] }
type Event = { event_type: string; course_id: string; term_label: string; unit_load: number }
type Saved = { plan: Plan; timeline: Timeline; label: string }

const COURSE_EVENTS = ['Fail', 'Withdraw', 'Pass']
const OFF_SEASONS = ['Winter', 'Summer']
const NOT_PASSED = /^(F|W|WU|NC|I|D[+-]?)$/  // D grades pass some courses, but fall below the C most CS prerequisites need
// Core, major elective, general education, or free elective: electives get their own color so choices stand out.
const kindOf = (c?: Course) => !c ? 'core' : c.id.startsWith('FREE') ? 'free' : c.placeholder ? 'ge'
  : c.requirement_groups.some(g => g === 'CSE Elective' || g.includes(' / ')) ? 'elective' : 'core'
const KIND_LABEL: Record<string, string> = { elective: 'Elective', ge: 'Gen Ed', free: 'Free elective' }
// Offered once a year: missing the term costs a full year, so it gets a badge, not fine print.
const OnceAYear = ({ c }: { c?: Course }) => c && ['Fall', 'Spring'].includes(c.term_offered)
  ? <span className="once" title={`Offered only in ${c.term_offered}. Missing it pushes this course, and everything after it, back a full year.`}>
      <svg viewBox="0 0 12 12" aria-hidden="true"><rect x="1.5" y="2.5" width="9" height="8" rx="1.5" /><path d="M1.5 5h9M4 1.5v2M8 1.5v2" /></svg>
      {c.term_offered} only
    </span>
  : null
const OFF_TERMS: Record<string, string> = { 'Add Summer': 'Summer', 'Add Winter': 'Winter' }  // opt-in intersessions
const EVENTS = [...COURSE_EVENTS, 'Add Summer', 'Add Winter', 'Change Unit Load']
const CAPS = Array.from({ length: 19 }, (_, i) => i + 3)  // 3..21, the engine's allowed range

const NO_MOVES: Move[] = []
const UNREACHABLE = STATIC ? "The in-browser planner engine isn't responding. Reload the page." : "Can't reach the planner API. Is the backend running on port 8000?"

async function api<T>(path: string, body?: unknown): Promise<T> {
  let r: Response
  try {
    r = await apiFetch(`/api${path}`, body === undefined ? undefined : {
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

const describe = (e: Event) => OFF_TERMS[e.event_type] ? `Add ${e.term_label}`
  : e.event_type === 'Change Unit Load' ? `${e.unit_load}-unit cap from ${e.term_label}`
  : `${e.event_type} ${e.course_id} (${e.term_label})`

export default function App() {
  const [catalog, setCatalog] = useState<Catalog>()
  const [students, setStudents] = useState<Student[]>([])
  const [riskFor, setRiskFor] = useState<{ plan?: Plan; data: Risk }>({ data: {} })
  const [report, setReport] = useState<Report>()
  const [uploading, setUploading] = useState(false)
  const sampleCount = useRef(0)
  const [started, setStarted] = useState(false)  // false: the landing page
  const [dragging, setDragging] = useState(false)
  const [engineReady, setEngineReady] = useState(!STATIC)
  useEffect(() => whenEngineReady(() => setEngineReady(true)), [])
  const [sid, setSid] = useState('alex')
  const [baseCap, setBaseCap] = useState<number>()
  const [plan, setPlan] = useState<Plan>()
  const [timeline, setTimeline] = useState<Timeline>()
  const [history, setHistory] = useState<Saved[]>([])
  const [alts, setAlts] = useState<Record<string, { plan: Plan; timeline: Timeline; adds?: string[] }>>({})
  const [preview, setPreview] = useState<Result & { label: string }>()
  const [error, setError] = useState('')
  const [ev, setEv] = useState<Event>({ event_type: 'Fail', course_id: '', term_label: '', unit_load: 12 })
  const [actionBusy, setActionBusy] = useState(false)
  const [loadedKey, setLoadedKey] = useState('')  // which student+cap the shown plan belongs to
  const planKey = `${sid}:${baseCap ?? ''}`
  const busy = actionBusy || loadedKey !== planKey || !catalog
  const generation = useRef(0)  // bumped whenever the saved plan is replaced; late answers for an older plan are dropped
  const scenarioRef = useRef<HTMLElement>(null)
  const resultRef = useRef<HTMLElement>(null)
  useEffect(() => { if (preview) resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [preview])
  const [showUnplanned, setShowUnplanned] = useState(false)
  const [section, setSection] = useState('overview')
  const [view, setView] = useState<'terms' | 'map'>('terms')
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('adpp-theme', next) } catch { /* private mode: the choice lasts this visit */ }
    setTheme(next)
  }
  const [tab, setTab] = useState<'bottlenecks' | 'confirm' | 'discrepancies'>('bottlenecks')

  const courses = useMemo(() => Object.fromEntries((catalog?.courses ?? []).map(c => [c.id, c])), [catalog])
  const student = students.find(s => s.id === sid)
  const shown = preview?.plan ?? plan
  const invalid = new Set(preview?.invalidated ?? [])
  const movedFrom = Object.fromEntries((preview?.moved ?? []).map(m => [m.course, m.from]))
  const inPlan = new Set(shown?.terms.flatMap(t => t.courses) ?? [])

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
      .then(([c, s]) => { setCatalog(c); setStudents(list => [...s, ...list.filter(x => x.id.startsWith('upload-'))]) }, e => setError(errorText(e)))
  }, [])
  useEffect(() => {
    let live = true  // a slower response for a previous student/cap must not overwrite this one
    const key = `${sid}:${baseCap ?? ''}`
    api<{ plan: Plan; timeline: Timeline; alternatives: typeof alts }>('/plan', { student_id: sid, unit_cap: baseCap ?? null })
      .then(r => {
        if (!live) return
        generation.current++
        setPlan(r.plan); setTimeline(r.timeline); setAlts(r.alternatives); setHistory([]); setPreview(undefined)
        setLoadedKey(key)
      }, e => { if (live) { setError(errorText(e)); setLoadedKey(key) } })
    return () => { live = false }
  }, [sid, baseCap])

  // Measured risk for the saved plan: what failing each course would cost, and the catch-up that wins it back.
  useEffect(() => {
    if (!plan) return
    let live = true
    api<Risk>('/risk', { plan }).then(data => { if (live) setRiskFor({ plan, data }) }, () => {})  // optional context
    return () => { live = false }
  }, [plan])
  const risk = riskFor.plan === plan ? riskFor.data : {}  // never show another plan's numbers
  const protect = Object.entries(risk).filter(([, r]) => r.delay > 0)
    .sort((a, b) => b[1].delay - a[1].delay || (catalog?.priority[b[0]] ?? 0) - (catalog?.priority[a[0]] ?? 0) || a[0].localeCompare(b[0]))

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

  // Intersessions the student could add and doesn't have yet: a Summer after each Spring, a Winter (January)
  // after each Fall that isn't the plan's last term.
  const offSeason = OFF_TERMS[ev.event_type]
  const offOptions = (plan?.terms ?? []).flatMap((t, i, all) => {
    const [season, year] = t.term_label.split(' ')
    if (offSeason === 'Summer' && season === 'Spring') return [`Summer ${year}`]
    if (offSeason === 'Winter' && season === 'Fall' && i < all.length - 1) return [`Winter ${+year + 1}`]
    return []
  }).filter(s => ![...plan?.summers ?? [], ...plan?.winters ?? []].includes(s))

  // The saved plan changes under the form (keep, undo, new student), so snap the selection to what the plan has now.
  const form: Event = (() => {
    if (offSeason)
      return { ...ev, term_label: offOptions.includes(ev.term_label) ? ev.term_label : offOptions[0] ?? '' }
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
    setPlan(p); setTimeline(t); setPreview(undefined)
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
  // Transcripts go to the API as the raw file; it parses them and keeps the profile in memory only.
  const upload = async (body: Blob, file: string) => {
    setError(''); setUploading(true)
    try {
      let name = file
      if (STATIC && (body.type === 'application/pdf' || /\.pdf$/i.test(file))) {  // read the PDF here; the parser only sees text
        try { body = new Blob([await pdfToText(body)], { type: 'text/plain' }) } catch (e) {
          throw e instanceof Error && /pages/.test(e.message) ? e : new Error('Could not read that file as a PDF. Try a text or CSV export.')
        }
        name = file.replace(/\.pdf$/i, '.txt')
      }
      const r = await apiFetch(`/api/transcript?filename=${encodeURIComponent(name)}`, { method: 'POST', body })
      const data = await r.json().catch(() => undefined)
      if (!r.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : r.status === 413 ? 'That file is over the 1 MB upload limit.' : UNREACHABLE)
      const s: Student = data.student
      s.name = `${file.replace(/\.[a-z]+$/i, '')} (uploaded)`
      setStudents(list => [...list, s]); setReport({ ...data.report, file }); changeStudent(s.id); setStarted(true)
    } catch (e) {
      setError(errorText(e))
    } finally { setUploading(false) }
  }
  const uploadSample = async () => {
    const text = await apiFetch('/api/transcript/sample').then(r => r.text()).catch(() => '')
    if (text) upload(new Blob([text], { type: 'text/plain' }), `Sample transcript ${++sampleCount.current}`)
    else setError(UNREACHABLE)
  }
  const changeCap = (cap: number) => { setError(''); setBaseCap(cap) }
  const whatIf = () => {
    const event = { ...form, course_id: COURSE_EVENTS.includes(form.event_type) ? form.course_id : null,
                    unit_load: form.event_type === 'Change Unit Load' ? form.unit_load : null }
    const label = describe(form)
    run(() => api<Result>('/scenario', { plan, event }), r => setPreview({ ...r, label }))
  }



  const termCourses = plan?.terms.find(t => t.term_label === form.term_label)?.courses ?? []
  const shownTimeline = preview?.timeline ?? timeline
  const critical = new Set(shownTimeline?.critical_path ?? [])
  const isDone = (id: string) => !!student?.completed_courses[id] || !!student?.in_progress_courses.includes(id)
  const stateOf = (id: string): NodeState =>
    invalid.has(id) ? 'invalid' : isDone(id) && !inPlan.has(id) ? 'done' : critical.has(id) ? 'critical' : inPlan.has(id) ? 'planned' : 'unplanned'

  // The map's columns follow the shown plan: completed work, each term, then (optionally) what the plan leaves out.
  const mapColumns = useMemo(() => {
    if (!catalog || !shown) return []
    const planned = new Set(shown.terms.flatMap(t => t.courses))
    const done = (id: string) => !!student?.completed_courses[id] || !!student?.in_progress_courses.includes(id)
    const all = catalog.courses.filter(c => !c.placeholder).map(c => c.id)
    // Each completed term is its own column (passed courses only); transfer credit with no term gets one column.
    const past = (student && shown.student_id === student.id ? student.history : []).map(h => ({ label: h.term_label, courses: Object.entries(h.grades)
      .filter(([c, g]) => !planned.has(c) && (g === 'IP' || (!NOT_PASSED.test(g) && student?.completed_courses[c] === g))).map(([c]) => c) }))
    const inHistory = new Set(past.flatMap(p => p.courses))
    const cols = [{ label: 'Transfer', courses: all.filter(id => done(id) && !planned.has(id) && !inHistory.has(id)) },
                  ...past, ...shown.terms.map(t => ({ label: t.term_label, courses: t.courses }))]
    if (showUnplanned) cols.push({ label: 'Not in plan', courses: all.filter(id => !planned.has(id) && !done(id)) })
    return cols
  }, [catalog, shown, student, showUnplanned])

  // Term cards sit in one row per academic year (Fall through Summer), each season in a fixed column so rows line up.
  // History only joins a plan made for the same student (a new student's plan may still be loading).
  const pastTerms = student && shown?.student_id === student.id ? student.history : []
  const slots: Slot[] = [...pastTerms.map(h => ({ label: h.term_label, past: h })),
                         ...(shown?.terms ?? []).map(t => ({ label: t.term_label, term: t }))]
  const seasons = ['Fall', 'Winter', 'Spring', 'Summer'].filter(x => !OFF_SEASONS.includes(x) || slots.some(t => t.label.startsWith(x)))
  const byYear = new Map<number, Slot[]>()
  for (const t of slots) {  // an academic year runs Fall through Summer
    const [season, year] = t.label.split(' ')
    const ay = season === 'Fall' ? +year : +year - 1
    byYear.set(ay, [...byYear.get(ay) ?? [], t])
  }
  const order = ['Fall', 'Winter', 'Spring', 'Summer']  // reading and focus order match the columns
  const years = [...byYear].sort((a, b) => a[0] - b[0])
    .map(([ay, ts]) => [ay, ts.sort((x, y) => order.indexOf(x.label.split(' ')[0]) - order.indexOf(y.label.split(' ')[0]))] as const)
  const transfer = Object.entries(student?.completed_courses ?? {})
    .filter(([c]) => !(student?.history ?? []).some(h => c in h.grades))
  const earned = (student?.history ?? []).reduce((n, h) => n + Object.entries(h.grades)
    .filter(([, g]) => !NOT_PASSED.test(g) && g !== 'IP').reduce((m, [c]) => m + (courses[c]?.catalog_units ?? 0), 0), 0)

  const was = (now: number | undefined, before: number | undefined) =>
    preview && before !== undefined && now !== before ? `${before} → ${now}` : String(now ?? before ?? '')
  const delta = preview?.delta_terms ?? 0

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => setStarted(false)} title="Back to the start page">
          <Logo className="logo" />
          <span className="brand-name">Degree Pathway Planner<small>B.S. Computer Science · 2026–27 catalog</small></span>
        </button>
        <div className="top-actions">
          <button className="theme-toggle" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} title={theme === 'dark' ? 'Light theme' : 'Dark theme'}>
            {theme === 'dark'
              ? <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3.5" /><path d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M4 4l1.4 1.4M14.6 14.6 16 16M4 16l1.4-1.4M14.6 5.4 16 4" /></svg>
              : <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16.5 12.5A7 7 0 0 1 7.5 3.5a7 7 0 1 0 9 9Z" /></svg>}
          </button>
        </div>
      </header>

      {!started ? <main className="landing" data-testid="landing">
        <section className="landing-hero">
          <p className="eyebrow">CSUSB · B.S. Computer Science · 2026–27 catalog</p>
          <h1>See your path to graduation, and what a setback would change.</h1>
          <p className="lede">Upload your unofficial transcript and get a term-by-term plan. Then ask what happens if you fail, withdraw from, or delay a course, and see exactly how graduation moves.</p>
        </section>
        <section className="landing-actions">
          {error && <div className="alert" role="alert">
            <span><strong>Error: </strong>{error}</span>
            <button className="ghost small" onClick={() => setError('')}>Dismiss</button>
          </div>}
          <label className={`dropzone ${dragging ? 'drag' : ''} ${uploading ? 'busy' : ''}`}
                 onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)}
                 onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f && !uploading) upload(f, f.name) }}>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 13V3M6 7l4-4 4 4M4 13v3h12v-3" /></svg>
            <strong>{uploading ? 'Reading your transcript…' : 'Upload your transcript'}</strong>
            <span>Drop a file here, or click to choose one. PDF, text, or CSV.</span>
            <input type="file" accept=".pdf,.txt,.csv,application/pdf,text/plain,text/csv" disabled={uploading}
                   onChange={e => { const f = e.target.files?.[0]; if (f) upload(f, f.name); e.target.value = '' }} />
          </label>
          <p className="privacy">Read in your browser and kept in memory only. Nothing is uploaded or saved.</p>
          <div className="or"><span>or</span></div>
          <button className="primary wide" onClick={() => { if (sid.startsWith('upload-')) changeStudent('alex'); setStarted(true) }}>Explore with sample data</button>
          <button className="linkish" onClick={uploadSample} disabled={uploading}>Try the sample transcript instead</button>
          {!engineReady && <p className="muted engine-note">Starting the planning engine in your browser (about 10 MB the first time)…</p>}
        </section>
        <p className="landing-note">Planning aid only: not an official degree audit or advising decision.</p>
      </main> : <>
      <div className="banner">
        <div className="banner-inner">
          <div className="who">
            <h1>{student?.name ?? 'Loading…'}</h1>
            {!engineReady && <p className="who-note"><span>Starting the planning engine in your browser (about 10 MB the first time)…</span></p>}
            {student && <p className="who-note">
              <span className="sample">{student.id.startsWith('upload-') ? 'Uploaded transcript · not saved' : 'Sample student · synthetic data'}</span>
              {student.notes && <span>{student.notes}</span>}
              {student.history.length > 0 && <span className="chip">{student.history.length} term{student.history.length === 1 ? '' : 's'} completed · <b>{earned} units</b></span>}
              {transfer.length > 0 && <span className="chip">{transfer.length} transfer credit{transfer.length === 1 ? '' : 's'}</span>}
              {student.in_progress_courses.length > 0 && <span className="chip now">{student.in_progress_courses.length} in progress</span>}
            </p>}
          </div>
          <div className="controls">
            <label>Student
              <select value={sid} onChange={e => changeStudent(e.target.value)}>
                <optgroup label="Sample students (synthetic data)">
                  {students.filter(s => !s.id.startsWith('upload-')).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </optgroup>
                {students.some(s => s.id.startsWith('upload-')) && <optgroup label="Uploaded transcripts (this session only)">
                  {students.filter(s => s.id.startsWith('upload-')).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </optgroup>}
              </select>
            </label>
            <label>Unit cap
              <select value={plan?.unit_cap ?? ''} onChange={e => changeCap(+e.target.value)}>
                {CAPS.map(c => <option key={c} value={c}>{c}{c === student?.unit_load_preference ? ' (preferred)' : ''}</option>)}
              </select>
            </label>
            <div className="upload">
              <span className="upload-label">Your transcript</span>
              <label className={`upload-btn ${uploading ? 'busy' : ''}`}>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 13V3M6 7l4-4 4 4M4 13v3h12v-3" /></svg>
                {uploading ? 'Reading…' : 'Upload transcript'}
                <input type="file" accept=".pdf,.txt,.csv,application/pdf,text/plain,text/csv" disabled={uploading}
                       onChange={e => { const f = e.target.files?.[0]; if (f) upload(f, f.name); e.target.value = '' }} />
              </label>
              <button className="linkish" onClick={uploadSample} disabled={uploading}>or try a sample</button>
            </div>
          </div>
        </div>
      </div>

      <nav className="sectionnav" aria-label="Sections">
        <div className="sectionnav-inner">
          {([['overview', 'Overview'], ['plan', 'Plan'], ['details', 'Bottlenecks & data']] as const).map(([id, name]) => (
            <a key={id} href={`#${id}`} className={section === id ? 'active' : ''} aria-current={section === id ? 'true' : undefined} onClick={() => setSection(id)}>{name}</a>
          ))}
          <p className="nav-note">Planning aid only: not an official degree audit or advising decision.</p>
        </div>
        <div className={`progress ${busy ? 'on' : ''}`} aria-hidden="true" />
      </nav>

      <main className="layout">
        <section className="summary" id="overview">
          {error && <div className="alert" role="alert">
            <span><strong>Error: </strong>{error}</span>
            <button className="ghost small" onClick={() => setError('')}>Dismiss</button>
          </div>}

          {timeline && <div className="stats">
            <Stat label="Graduation" hero tone={preview ? (delta > 0 ? 'bad' : 'ok') : undefined}
                  value={preview ? `${timeline.graduation_term} → ${preview.timeline.graduation_term}` : timeline.graduation_term} />
            <Stat label="Terms" value={was(preview?.timeline.term_count, timeline.term_count)} />
            <Stat label="Units" value={was(preview?.timeline.total_units, timeline.total_units)} />
          </div>}

          {report && student?.id.startsWith('upload-') && <div className="report" role="status">
            <p><strong>Read {report.file}:</strong> {report.terms.length} term{report.terms.length === 1 ? '' : 's'} ({report.terms[0]}–{report.terms.at(-1)}), {report.courses} course attempts{report.transfer.length ? `, ${report.transfer.length} transfer credits` : ''}. The plan starts {report.start_term} at {report.unit_load_preference} units, the average of your past regular terms.</p>
            {report.unrecognized.length > 0 && <p className="muted">Not in the B.S. CS catalog, so not counted: {report.unrecognized.join(', ')}.</p>}
            {report.unread.length > 0 && <p className="muted">Could not read a grade on: {report.unread.join('; ')}.</p>}
            <p className="muted">Kept in memory for this session only; nothing is saved. Check every term against your official record.</p>
          </div>}

          <div className="plan-tools">
            {shownTimeline && <p className="critical"><span className="muted">Critical path</span> {shownTimeline.critical_path.join(' → ')}</p>}
            {protect.length > 0 && <div className="protect">
              <span className="muted">Protect these</span>
              {protect.slice(0, 3).map(([c, r]) => (
                <button key={c} className="risk-chip" onClick={() => { setEv(e => ({ ...e, event_type: 'Fail' })); pick(c) }}
                        title={`Failing ${c} in ${r.term} delays graduation by ${r.delay} term${r.delay === 1 ? '' : 's'}.${r.catch_up.length ? ` Catch-up: ${r.catch_up.join(' + ')}${r.after_catch_up <= 0 ? ' (back on time)' : ` (${r.after_catch_up} left)`}.` : ' No summer or winter term can win it back.'} Click to test it.`}>
                  <b>{c}</b> <span className="bad-text">+{r.delay}</span>
                </button>
              ))}
            </div>}
            {Object.keys(alts).length > 0 && <div className="alts">
              <span className="muted">Other pathways</span>
              {Object.entries(alts).map(([name, a]) => (
                <button key={name} className="alt" onClick={() => adopt(a.plan, a.timeline, `${name} pathway`)}
                        title={`${a.plan.unit_cap}-unit cap · peak ${Math.max(...a.plan.terms.map(t => t.total_units))}u${a.adds ? ` · adds ${a.adds.join(', ')}` : ''}`}>
                  <span className="alt-name">{name}</span> <span className="alt-grad">{a.timeline.graduation_term}</span>
                </button>
              ))}
            </div>}
            {history.length > 0 && <div className="history">
              <span className="muted">{history.length} kept change{history.length === 1 ? '' : 's'} since baseline ({history[0].timeline.graduation_term}): {history.map(h => h.label).join(', ')}</span>
              <button className="ghost small" onClick={undo}>Undo last</button>
              <button className="ghost small" onClick={reset}>Reset to baseline</button>
            </div>}
          </div>
        </section>

        <aside className="panel">
          <section className="block" ref={scenarioRef}>
            <h2>What if…</h2>
            <p className="muted hint">Pick what happens, or click a course in the plan.</p>
            <div className="fields">
              <div className="field" role="radiogroup" aria-label="Event">
                <span>What happens?</span>
                <div className="chips">
                  {EVENTS.map(x => <button key={x} type="button" role="radio" aria-checked={form.event_type === x} className="chip"
                    onClick={() => setEv({ ...form, event_type: x })}>{x}</button>)}
                </div>
              </div>
              <div className="pair">
              {offSeason
                ? offOptions.length
                  ? <label className="field">{offSeason} term
                      <select aria-label={`${offSeason} term`} value={form.term_label} onChange={e => setEv({ ...form, term_label: e.target.value })}>
                        {offOptions.map(s => <option key={s}>{s}</option>)}
                      </select>
                      {offSeason === 'Winter' && <span className="muted field-note">Three-week January session; up to 4 units (Registrar limit).</span>}
                    </label>
                  : <p className="muted">Every {offSeason.toLowerCase()} term in this plan is already on.</p>
                : <label className="field">Term
                    <select aria-label="Term" value={form.term_label} onChange={e => setEv({ ...form, term_label: e.target.value, course_id: '' })}>
                      {plan?.terms.map(t => <option key={t.term_label}>{t.term_label}</option>)}
                    </select>
                  </label>}
              {COURSE_EVENTS.includes(form.event_type) &&
                <label className="field">Course
                  <select aria-label="Course" value={form.course_id} onChange={e => setEv({ ...form, course_id: e.target.value })}>
                    {termCourses.map(c => <option key={c}>{c}</option>)}
                  </select>
                </label>}
              {form.event_type === 'Change Unit Load' &&
                <label className="field">New unit load
                  <select aria-label="New unit load" value={form.unit_load} onChange={e => setEv({ ...form, unit_load: +e.target.value })}>
                    {CAPS.map(c => <option key={c} value={c}>{c} units</option>)}
                  </select>
                </label>}
              </div>
            </div>
            <button className="primary wide" disabled={busy || !plan || !form.term_label || (COURSE_EVENTS.includes(form.event_type) && !form.course_id)} onClick={whatIf}>Run what-if</button>
          </section>

          {preview && <section className={`result ${delta > 0 ? 'bad' : 'ok'}`} data-testid="whatif" ref={resultRef} aria-live="polite">
            <p className="result-head">
              <strong>{preview.label}</strong>
              <span className="delta">{delta > 0 ? `+${delta} term${delta === 1 ? '' : 's'}` : delta < 0 ? `${delta} term${delta === -1 ? '' : 's'}` : 'No delay'}</span>
            </p>
            <p>{preview.explanation}</p>
            {preview.moved.length > 0 && <details className="moved">
              <summary>{preview.moved.length} course{preview.moved.length === 1 ? '' : 's'} moved</summary>
              <ul>{preview.moved.map(m => <li key={m.course}><b>{m.course}</b> {m.from} → {m.to}</li>)}</ul>
            </details>}
            <div className="row">
              <button className="primary" onClick={() => adopt(preview.plan, preview.timeline, preview.label)}>Keep this plan</button>
              <button className="ghost" onClick={() => { setPreview(undefined) }}>Discard</button>
            </div>
            {preview.recovery && <div className="catchup">
              <p><strong>Catch up with {preview.recovery.adds.join(' + ')}</strong></p>
              <p>{preview.recovery.explanation}</p>
              <button className="ghost small" onClick={() => setPreview({ ...preview.recovery!, label: `${preview.label} + ${preview.recovery!.adds.join(' + ')}` })}>
                Preview catch-up plan
              </button>
            </div>}
          </section>}
        </aside>

        <section className="plancard" id="plan">
          <div className="section-head">
            <h2>Plan</h2>
            <div className="seg" role="group" aria-label="Plan view">
              <button aria-pressed={view === 'terms'} onClick={() => setView('terms')}>Terms</button>
              <button aria-pressed={view === 'map'} onClick={() => setView('map')}>Prerequisite map</button>
            </div>
          </div>

          {view === 'terms' && <ul className="legend kinds">
            <li><i className="sw k-elective" />Elective</li><li><i className="sw k-ge" />General education</li><li><span className="once">Fall only</span>Offered once a year</li>
            <li><span className="risk">+2</span>Terms lost if failed (2 or more)</li>
          </ul>}
          {view === 'terms' && <div className="terms" data-testid="terms" style={{ '--tpl': `4.5rem ${seasons.map(x => OFF_SEASONS.includes(x) ? 'minmax(0, .8fr)' : 'minmax(0, 1fr)').join(' ')}` } as CSSProperties}>
            {years.map(([ay, terms]) => (
              <div key={ay} className="year">
                <p className="year-label">{ay}–{String(ay + 1).slice(2)}</p>
                {terms.map(slot => {
                  const season = slot.label.split(' ')[0]
                  const column = { gridColumn: seasons.indexOf(season) + 2 }
                  if (slot.past) return (
                    <div key={`past-${slot.label}`} className={`term past ${OFF_SEASONS.includes(season) ? 'off' : ''}`} style={column}>
                      <h3>{slot.label} <span className="past-tag">{Object.values(slot.past.grades).includes('IP') ? 'In progress' : 'Completed'}</span></h3>
                      {Object.entries(slot.past.grades).map(([c, g]) => (
                        <div key={c} className={`course static k-${kindOf(courses[c])}`}>
                          <span className="code">{c} <span className={`grade ${g === 'IP' ? 'ip' : NOT_PASSED.test(g) ? 'low' : ''}`}>{g === 'IP' ? 'in progress' : g}</span>
                            {NOT_PASSED.test(g) && student?.completed_courses[c] !== g && <span className="was"> retaken later</span>}
                          </span>
                          <span className="meta"><span className="title">{courses[c]?.title?.replace(/^[^:]*:\s*/, '') ?? ''}</span><span className="muted nowrap">{courses[c]?.catalog_units ?? '?'}u</span></span>
                        </div>
                      ))}
                    </div>
                  )
                  const t = slot.term!
                  const notes = t.warnings.filter(w => !/confirm|disagree/.test(w))
                  return (
                    <div key={t.term_label} className={`term ${OFF_SEASONS.includes(season) ? 'off' : ''}`} style={column}>
                      <h3>{t.term_label} <span className="units">{t.total_units}<span className="muted"> / {t.unit_cap ?? shown!.unit_cap}u</span></span></h3>
                      {t.courses.map(c => (
                        <button key={c} type="button" className={`course k-${kindOf(courses[c])} ${invalid.has(c) ? 'invalid' : ''} ${shown!.credited[c] ? 'passed' : ''} ${critical.has(c) ? 'crit' : ''}`}
                                title={`${courses[c]?.title ?? c}. Click to load into the what-if form.`} onClick={() => pick(c)}>
                          <span className="code">{c}{shown!.credited[c] && <><span className="sr-only"> ✓</span><svg className="check" viewBox="0 0 12 12" role="img" aria-label="passed"><path d="M2.5 6.5 5 9l4.5-6" /></svg></>}{invalid.has(c) && ' (affected)'}
                            {movedFrom[c] && <span className="was"> was {movedFrom[c]}</span>}
                            {KIND_LABEL[kindOf(courses[c])] && <span className={`kind k-${kindOf(courses[c])}`}>{KIND_LABEL[kindOf(courses[c])]}</span>}
                            <OnceAYear c={courses[c]} />
                            {!preview && risk[c]?.delay >= 2 && <span className="risk" title={`Failing it delays graduation by ${risk[c].delay} term(s)${risk[c].catch_up.length ? `; catch-up: ${risk[c].catch_up.join(' + ')}` : ''}`}>+{risk[c].delay}<span className="sr-only"> terms if failed</span></span>}
                          </span>
                          <span className="meta">
                            <span className="title">{courses[c]?.title?.replace(/^[^:]*:\s*/, '') ?? ''}</span>
                            <span className="muted nowrap">
                              {courses[c]?.catalog_units}u
                              {courses[c]?.discrepancy_flag && <svg className="flag" viewBox="0 0 12 12" role="img" aria-label={`roadmap says ${courses[c].roadmap_units} units`}><title>{`Roadmap says ${courses[c].roadmap_units}u`}</title><path d="M3 11V1.5M3 2h6.5L8 4.5 9.5 7H3" /></svg>}
                            </span>
                          </span>
                        </button>
                      ))}
                      {!t.courses.length && <p className="muted empty">No courses fit this term.</p>}
                      {notes.length > 0 && <details className="notes">
                        <summary>{notes.length} scheduling note{notes.length === 1 ? '' : 's'}</summary>
                        <ul>{notes.map(w => <li key={w}>{w}</li>)}</ul>
                      </details>}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>}

          {view === 'map' && catalog && <>
            <div className="map-bar">
              <ul className="legend">
                <li><i className="sw done" />Completed</li>
                <li><i className="sw planned" />Planned</li>
                <li><i className="sw critical" />Critical path</li>
                <li><i className="sw invalid" />Affected</li>
                {showUnplanned && <li><i className="sw unplanned" />Not in plan</li>}
                {preview && preview.moved.length > 0 && <li><i className="sw ghost" />Where a moved course was</li>}
                <li><i className="once-sw" />Offered once a year</li>
                <li><i className="ln" />Required</li>
                <li><i className="ln or" />One of several</li>
              </ul>
              <label className="toggle"><input type="checkbox" checked={showUnplanned} onChange={e => setShowUnplanned(e.target.checked)} /> Show the rest of the catalog</label>
            </div>
            <p className="muted hint">Columns are terms, so every arrow points forward in time. Hover a course to trace its chain; click to test it.</p>
            <PrereqMap columns={mapColumns} edges={catalog.edges} stateOf={stateOf} criticalPath={shownTimeline?.critical_path ?? []} moved={preview?.moved ?? NO_MOVES}
                       onceAYear={id => ['Fall', 'Spring'].includes(courses[id]?.term_offered)} onPick={pick} />
          </>}
        </section>

        {catalog && <section className="details" id="details">
          <div className="tabs" role="tablist">
            {([['bottlenecks', 'Bottlenecks', bottlenecks.length], ['confirm', 'To confirm', toConfirm.length],
               ['discrepancies', 'Discrepancies', catalog.discrepancies.length]] as const).map(([id, name, n]) => (
              <button key={id} role="tab" aria-selected={tab === id} className="tab" onClick={() => setTab(id)}>
                {name} <span className="count">{n}</span>
              </button>
            ))}
          </div>
          <div role="tabpanel" className="tabpanel">
            {tab === 'bottlenecks' && <>
              <p className="muted hint">Top 10 planned courses by priority score (direct dependents + longest downstream chain + 1 if offered once a year). "Gates" counts the later courses in this plan that depend on it. "If failed" is measured: the engine fails the course and replans. Click a row to test it.</p>
              <div className="table-wrap"><table>
                <thead><tr><th>Course</th><th>Title</th><th className="num">Priority</th><th className="num">Gates</th><th className="num">If failed</th><th>Catch-up</th></tr></thead>
                <tbody>
                  {bottlenecks.map(b => (
                    <tr key={b.id} className="clickable" onClick={() => pick(b.id)}>
                      <td className="code nowrap">{b.id}</td><td className="muted">{b.title}</td><td className="num">{b.priority}</td><td className="num">{b.gates}</td>
                      <td className="num">{risk[b.id] ? (risk[b.id].delay > 0 ? `+${risk[b.id].delay}` : 'none') : '…'}</td>
                      <td className="muted">{risk[b.id]?.catch_up.length ? `${risk[b.id].catch_up.join(' + ')}${risk[b.id].after_catch_up <= 0 ? ' (on time)' : ''}` : risk[b.id]?.delay > 0 ? 'none possible' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </>}
            {tab === 'confirm' && (!toConfirm.length ? <p className="muted">Every placement in this plan is confirmed by the roadmaps.</p> : <>
              <p className="muted hint">The plan assumes these offerings. The data can't confirm them: the course is on no roadmap, roadmaps disagree, or summer and winter sections aren't published.</p>
              <ul className="list">{toConfirm.map(({ term, w }) => <li key={term + w}><b>{term}</b> {w}</li>)}</ul>
            </>)}
            {tab === 'discrepancies' && <>
              <p className="muted hint">Catalog/roadmap discrepancies flagged for advisor review. The catalog wins; nothing is auto-resolved.</p>
              <ul className="list">{catalog.discrepancies.map(d => <li key={d}>{d}</li>)}</ul>
            </>}
          </div>
        </section>}
      </main>
      </>}
    </>
  )
}

function Stat({ label, value, hero, tone }: { label: string; value: string; hero?: boolean; tone?: 'ok' | 'bad' }) {
  return <div className={`stat ${hero ? 'hero' : ''} ${tone ?? ''}`}><span className="label">{label}</span><span className="value">{value}</span></div>
}
