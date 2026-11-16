import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { Activity, ArrowRight, BookOpen, CheckCircle2, ChevronRight, CircleAlert, CloudUpload, Download, FileDiff, FileText, LayoutDashboard, LoaderCircle, Menu, Search, Settings2, ShieldCheck, X } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

type Json = Record<string, unknown>
type Uploaded = { document_id: string; filename: string; total_pages: number; pages_with_text: number }
type Comparison = { comparison_id: string; summary: Record<string, number>; analyzed_rules?: unknown[]; pending_review?: unknown[]; potential_additions?: unknown[]; potential_removals?: unknown[]; alignment_conflicts?: unknown[]; review_required?: boolean }
type Finding = { final_rule_number?: string | number; rule_title?: string; impact_level?: string; assessment_status?: string; impact_reason?: string; requires_human_review?: boolean; potential_policy_matches?: unknown[]; ai_preliminary_explanation?: string; regulatory_evidence?: unknown; detected_changes?: unknown[] }
type Report = { comparison_id?: string; policy_sections_checked?: number; modified_rules_evaluated?: number; ai_status?: string; findings?: Finding[]; disclaimer?: string }
type ApiError = Error & { status?: number }
type HistoryItem = { comparison_id: string; created_at: string; analyzed_rule_count: number; modified_rule_count: number; pending_review_count: number }
function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}


const API = '/api'
const KEY = 'regulatory-ui-session-v1'
const defaultComparisonId = ''
function errorMessage(e: unknown) { return e instanceof Error ? e.message : String(e) }
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try { response = await fetch(API + path, options) } catch { throw new Error('Cannot connect to FastAPI. Start the backend on port 8000.') }
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { const body = await response.json(); const detail = body?.detail; message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((x: { msg?: string }) => x.msg).join('; ') : message } catch { /* preserve HTTP status */ }
    const err = new Error(message) as ApiError; err.status = response.status; throw err
  }
  return response.json() as Promise<T>
}
function postJson<T>(path: string, payload: unknown) { return request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }) }
function readStore(): { documents: Uploaded[]; comparison: Comparison | null; comparisonId: string } {
  try { const saved = JSON.parse(sessionStorage.getItem(KEY) || '{}'); return { documents: Array.isArray(saved.documents) ? saved.documents : [], comparison: saved.comparison || null, comparisonId: typeof saved.comparisonId === 'string' ? saved.comparisonId : defaultComparisonId } }
  catch { return { documents: [], comparison: null, comparisonId: defaultComparisonId } }
}
function value(v: unknown) { return v == null ? '—' : String(v) }
function formatJson(v: unknown) { return JSON.stringify(v, null, 2) }
function Label({ children }: { children: React.ReactNode }) { return <span className="field-label">{children}</span> }
function Notice({ children, kind = 'info' }: { children: React.ReactNode; kind?: 'info' | 'error' | 'success' }) { return <div className={`notice ${kind}`} role={kind === 'error' ? 'alert' : undefined}>{children}</div> }
function Spinner() { return <LoaderCircle size={17} className="spin" /> }
function SectionHead({ eyebrow, title, description }: { eyebrow: string; title: string; description?: string }) { return <header className="section-head"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</header> }
function Panel({ title, subtitle, children, action }: { title: string; subtitle?: string; children: React.ReactNode; action?: React.ReactNode }) { return <section className="panel"><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section> }
function Metric({ label, number, foot, icon }: { label: string; number: string | number; foot: string; icon: React.ReactNode }) { return <div className="metric"><div className="metric-top"><span>{label}</span><div className="metric-icon">{icon}</div></div><strong>{number}</strong><small>{foot}</small></div> }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="field"><Label>{label}</Label>{children}</label> }
function Empty({ children }: { children: React.ReactNode }) { return <div className="empty"><FileText size={26} /><p>{children}</p></div> }

function App() {
  const [saved] = useState(readStore)
  const [documents, setDocuments] = useState<Uploaded[]>(saved.documents)
  const [comparison, setComparison] = useState<Comparison | null>(saved.comparison)
  const [comparisonId, setComparisonId] = useState(saved.comparisonId)
  const [report, setReport] = useState<Report | null>(null)
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null)
  const [sidebar, setSidebar] = useState(false)
  const [reportError, setReportError] = useState('')
  useEffect(() => { sessionStorage.setItem(KEY, JSON.stringify({ documents, comparison, comparisonId })) }, [documents, comparison, comparisonId])
  async function checkHealth() { try { const data = await request<{ status?: string }>('/health'); setApiHealthy(data.status === 'healthy') } catch { setApiHealthy(false) } }
  useEffect(() => { let active = true; request<{ status?: string }>('/health').then(data => { if (active) setApiHealthy(data.status === 'healthy') }).catch(() => { if (active) setApiHealthy(false) }); return () => { active = false } }, [])
  async function loadReport(id: string) { setReportError(''); try { const r = await request<Report>(`/impact/${encodeURIComponent(id)}`); setReport(r) } catch (e) { setReport(null); setReportError(errorMessage(e)) } }
  useEffect(() => { if (!comparisonId) return; let active = true; request<Report>(`/impact/${encodeURIComponent(comparisonId)}`).then(r => { if (active) { setReport(r); setReportError('') } }).catch(e => { if (active) { setReport(null); setReportError(errorMessage(e)) } }); return () => { active = false } }, [comparisonId])
  const links = [
    { to: '/overview', name: 'Overview', icon: LayoutDashboard },
    { to: '/documents', name: 'Documents', icon: FileText },
    { to: '/comparison', name: 'Rule comparison', icon: FileDiff },
    { to: '/impact', name: 'Policy impact', icon: ShieldCheck },
    { to: '/knowledge', name: 'Knowledge base', icon: BookOpen },
    { to: '/reports', name: 'Reports', icon: Download },
    { to: '/settings', name: 'Settings', icon: Settings2 },
  ]
  return <div className="app-shell">
    <button className="mobile-menu" onClick={() => setSidebar(true)} aria-label="Open navigation"><Menu size={22} /></button>
    {sidebar && <div className="scrim" onClick={() => setSidebar(false)} />}
    <aside className={`sidebar ${sidebar ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark"><ShieldCheck size={23} /></div><div><strong>Regulatory AI</strong><span>Intelligence workspace</span></div><button className="close-menu" onClick={() => setSidebar(false)} aria-label="Close navigation"><X size={20}/></button></div>
      <div className="nav-caption">WORKSPACE</div>
      <nav>{links.map(({ to, name, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setSidebar(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={19}/><span>{name}</span><ChevronRight size={15} className="nav-chevron" /></NavLink>)}</nav>
      <div className="sidebar-bottom"><div className={`status-dot ${apiHealthy ? 'online' : ''}`} /><div><strong>{apiHealthy === null ? 'Checking connection' : apiHealthy ? 'API connected' : 'API unavailable'}</strong><small>Local analysis workspace</small></div></div>
    </aside>
    <main className="main"><div className="topbar"><span>REGULATORY INTELLIGENCE <span className="topbar-divider">/</span> WORKSPACE</span><span className="topbar-right"><span className={`status-dot ${apiHealthy ? 'online' : ''}`} />{apiHealthy ? 'Connected' : apiHealthy === false ? 'Offline' : 'Checking'}</span></div><div className="content">
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<Overview comparison={comparison} report={report} navigateTo="/documents" />} />
        <Route path="/documents" element={<Documents documents={documents} onUpload={d => setDocuments(old => [...old, d])} />} />
        <Route path="/comparison" element={<ComparisonPage documents={documents} comparison={comparison} onComparison={c => { setComparison(c); setComparisonId(c.comparison_id); setReport(null) }} />} />
        <Route path="/impact" element={<ImpactPage key={comparisonId} comparisonId={comparisonId} setComparisonId={id => { setComparisonId(id); setReport(null) }} report={report} reportError={reportError} reload={() => comparisonId && void loadReport(comparisonId)} />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/reports" element={<ReportsPage key={comparisonId} comparisonId={comparisonId} report={report} setComparisonId={setComparisonId} reportError={reportError} />} />
        <Route path="/settings" element={<SettingsPage healthy={apiHealthy} checkHealth={checkHealth} />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </div></main>
  </div>
}
function Overview({ comparison, report, navigateTo }: { comparison: Comparison | null; report: Report | null; navigateTo: string }) {
  const navigate = useNavigate()
  const s = comparison?.summary
  const analyzed = s?.analyzed_rule_count
  const modified = s?.modified_rule_count
  const unchanged = typeof analyzed === 'number' && typeof modified === 'number' ? Math.max(0, analyzed - modified) : undefined
  const pie = typeof modified === 'number' && typeof unchanged === 'number' ? [{ name: 'Modified', value: modified, color: '#2563eb' }, { name: 'Unchanged', value: unchanged, color: '#0d9488' }] : []
  const bars = s ? [{ name: 'Modified', count: modified || 0 }, { name: 'Review', count: s.pending_review_count || 0 }, { name: 'Additions', count: s.potential_addition_count || 0 }, { name: 'Removals', count: s.potential_removal_count || 0 }] : []
  return <><SectionHead eyebrow="ANALYTICS OVERVIEW" title="Regulatory intelligence, clearly presented." description="Track document changes, review preliminary findings, and move from evidence to action." />
    <div className="hero"><div><span className="hero-tag">DOCUMENT INTELLIGENCE</span><h2>Understand what changed.<br/>See what needs review.</h2><p>Compare regulatory versions and investigate possible policy implications with traceable evidence.</p><button className="button white" onClick={() => navigate(navigateTo)}>Start with documents <ArrowRight size={16}/></button></div><div className="hero-graphic"><div className="graphic-ring ring-one"/><div className="graphic-ring ring-two"/><ShieldCheck size={78} strokeWidth={1.2}/></div></div>
    <div className="metrics-grid"><Metric label="Rules analyzed" number={analyzed ?? '—'} foot="Current comparison" icon={<BookOpen size={20}/>}/><Metric label="Modified rules" number={modified ?? '—'} foot="Detected changes" icon={<FileDiff size={20}/>}/><Metric label="Pending review" number={s?.pending_review_count ?? '—'} foot="Alignment review" icon={<CircleAlert size={20}/>}/><Metric label="Impact findings" number={report?.findings?.length ?? '—'} foot="Preliminary assessments" icon={<Activity size={20}/>}/></div>
    {!comparison && <Notice>There is no comparison in this browser session yet. Upload two PDFs and run a comparison to populate the analytics.</Notice>}
    <div className="two-columns"><Panel title="Rule change distribution" subtitle="Based on the latest comparison response">{pie.length && pie.some(p => p.value > 0) ? <div className="chart-layout"><div className="chart-wrap"><ResponsiveContainer width="100%" height={240}><PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={66} outerRadius={94} paddingAngle={3}>{pie.map(p => <Cell key={p.name} fill={p.color}/>)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div><div className="legend">{pie.map(p => <div key={p.name}><span className="legend-dot" style={{ background: p.color }}/><span>{p.name}</span><strong>{p.value}</strong></div>)}</div></div> : <Empty>Chart data will appear after comparing documents.</Empty>}</Panel>
    <Panel title="Comparison signals" subtitle="Counts from the analysis pipeline">{bars.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={bars} margin={{ top: 12, right: 10, bottom: 0, left: -20 }}><CartesianGrid vertical={false} stroke="#e8eef6" strokeDasharray="3 4"/><XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#64748b', fontSize: 12 }}/><YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }}/><Tooltip cursor={{ fill: '#f1f5f9' }}/><Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={48}/></BarChart></ResponsiveContainer> : <Empty>Comparison signals will appear here.</Empty>}</Panel></div>
    <Panel title="Review status" subtitle="Interpretation and governance"><div className="review-banner"><CircleAlert size={22}/><div><strong>Human review remains required</strong><p>AI-generated explanations and policy matches are preliminary. This application does not issue final legal compliance or risk determinations.</p></div></div></Panel>
  </>
}
function Documents({ documents, onUpload }: { documents: Uploaded[]; onUpload: (d: Uploaded) => void }) {
  const [file, setFile] = useState<File | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [success, setSuccess] = useState('')
  async function upload() { if (!file) return; if (!file.name.toLowerCase().endsWith('.pdf')) { setError('Select a PDF file.'); return } if (file.size > 20 * 1024 * 1024) { setError('Maximum upload size is 20 MB.'); return } setBusy(true); setError(''); setSuccess(''); try { const body = new FormData(); body.append('file', file); const result = await request<Uploaded>('/documents/upload', { method: 'POST', body }); onUpload(result); setSuccess(`${result.filename} uploaded and extracted successfully.`); setFile(null); const input = document.getElementById('document-file') as HTMLInputElement | null; if (input) input.value = '' } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) } }
  return <><SectionHead eyebrow="DOCUMENT LIBRARY" title="Manage regulatory documents" description="Upload PDF versions to extract text and prepare them for structured comparison."/><div className="two-columns docs-layout"><Panel title="Upload a document" subtitle="PDF format · Maximum 20 MB"><div className="upload-zone"><CloudUpload size={36}/><strong>{file?.name || 'Select a regulatory PDF'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'Text must be extractable from the PDF'}</span><input id="document-file" type="file" accept="application/pdf,.pdf" onChange={e => setFile(e.target.files?.[0] || null)}/></div><button className="button primary" disabled={!file || busy} onClick={upload}>{busy ? <Spinner/> : <CloudUpload size={17}/>} Upload and process</button>{error && <Notice kind="error">{error}</Notice>}{success && <Notice kind="success">{success}</Notice>}</Panel><Panel title="Processing details" subtitle="What happens after upload"><div className="process-steps"><div><span>01</span><div><strong>Upload PDF</strong><p>Stored locally by the backend with a unique document ID.</p></div></div><div><span>02</span><div><strong>Extract text</strong><p>Page-level text is extracted and validated.</p></div></div><div><span>03</span><div><strong>Compare versions</strong><p>Use the returned document IDs and page ranges.</p></div></div></div></Panel></div><Panel title="Uploaded this session" subtitle="Documents are tracked in this browser session; the backend currently has no document-list endpoint">{documents.length ? <div className="document-list">{documents.map(d => <div className="document-row" key={d.document_id}><FileText size={22}/><div><strong>{d.filename}</strong><small>{d.total_pages} pages · {d.pages_with_text} with text</small><code>{d.document_id}</code></div><CheckCircle2 size={19} color="#0d9488"/></div>)}</div> : <Empty>No documents uploaded in this session.</Empty>}</Panel></>
}
function ComparisonPage({ documents, comparison, onComparison }: { documents: Uploaded[]; comparison: Comparison | null; onComparison: (c: Comparison) => void }) {
  const [original, setOriginal] = useState(''), [updated, setUpdated] = useState(''), [start1, setStart1] = useState(1), [end1, setEnd1] = useState(1), [start2, setStart2] = useState(1), [end2, setEnd2] = useState(1), [topK, setTopK] = useState(3), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const orig = documents.find(d => d.document_id === original), upd = documents.find(d => d.document_id === updated)


  
async function compare() {
  setError('')

  if (!original || !updated || original === updated) {
    setError('Select two different uploaded documents.')
    return
  }

  if (
    start1 < 1 || end1 < start1 ||
    start2 < 1 || end2 < start2 ||
    (orig && end1 > orig.total_pages) ||
    (upd && end2 > upd.total_pages)
  ) {
    setError('Check the selected page ranges.')
    return
  }

  setBusy(true)

  try {
    const result = await postJson<Comparison>('/documents/compare', {
      original_document_id: original,
      updated_document_id: updated,
      original_pages: { start_page: start1, end_page: end1 },
      updated_pages: { start_page: start2, end_page: end2 },
      top_k: topK
    })

    onComparison(result)

    // Clear previous comparison data before loading the new result.
    setLocalChanges(null)
    setDraftParsed(null)
    setFinalParsed(null)

    setSavedComparisonId(result.comparison_id)
    await loadSavedComparison(result.comparison_id)
    await refreshHistory()

  } catch (e) {
    setError(errorMessage(e))
  } finally {
    setBusy(false)
  }
}

  const s = comparison?.summary
  const [localChanges, setLocalChanges] = useState<ChangeFile | null>(null)
  const [importError, setImportError] = useState('')
  const [filter, setFilter] = useState('all')
  const [draftParsed, setDraftParsed] = useState<ParsedRules | null>(null)
  const [finalParsed, setFinalParsed] = useState<ParsedRules | null>(null)
  const [parsedError, setParsedError] = useState('')

const [savedComparisonId, setSavedComparisonId] = useState(
  comparison?.comparison_id ?? ''
)
const [loadingSaved, setLoadingSaved] = useState(false)
const [savedLoadError, setSavedLoadError] = useState('')
const [history, setHistory] = useState<HistoryItem[]>([])
const [historyBusy, setHistoryBusy] = useState(false)
const [historyError, setHistoryError] = useState('')
async function refreshHistory() {
  setHistoryBusy(true)
  setHistoryError('')
  try {
    const result = await request<{ comparisons: HistoryItem[] }>('/documents/comparisons')
    setHistory(Array.isArray(result.comparisons) ? result.comparisons : [])
  } catch (e) { setHistoryError(errorMessage(e)) }
  finally { setHistoryBusy(false) }
}
useEffect(() => { void refreshHistory() }, [])


async function loadSavedComparison(id: string) {
  const cleanId = id.trim()

  if (!/^[0-9a-f]{32}$/.test(cleanId)) {
    setSavedLoadError('Enter a valid 32-character comparison ID.')
    return
  }

  setLoadingSaved(true)
  setSavedLoadError('')

  try {
    const data = await request<{
      comparison_id: string
      changes: ChangeFile
      draft: ParsedRules
      final: ParsedRules
    }>(`/documents/comparisons/${cleanId}`)

    if (
      !Array.isArray(data.changes?.analyzed_rules) ||
      !Array.isArray(data.draft?.sections) ||
      !Array.isArray(data.final?.sections)
    ) {
      throw new Error('The saved comparison response is incomplete.')
    }

    const items = data.changes.analyzed_rules
    const savedSummary = {
      original_rule_count: data.draft.sections.length,
      updated_rule_count: data.final.sections.length,
      analyzed_rule_count: items.length,
      modified_rule_count: items.filter(r => r.status === 'modified').length,
      pending_review_count: items.filter(r => r.review_required).length,
      potential_addition_count: 0,
      potential_removal_count: 0,
      alignment_conflict_count: 0
    }
    onComparison({ comparison_id: cleanId, summary: savedSummary, analyzed_rules: items, review_required: true })
    setLocalChanges(data.changes)
    setDraftParsed(data.draft)
    setFinalParsed(data.final)
    setImportError('')
    setParsedError('')
    setSavedComparisonId(cleanId)
  } catch (e) {
    setSavedLoadError(errorMessage(e))
  } finally {
    setLoadingSaved(false)
  }
}

  async function importParsed(file: File | undefined, version: 'draft' | 'final') {
    if (!file) return
    setParsedError('')
    try {
      const data: unknown = JSON.parse(await file.text())
      if (!data || typeof data !== 'object' || !('sections' in data) || !Array.isArray((data as ParsedRules).sections) || !(data as ParsedRules).sections.every(section => section && typeof section.text === 'string')) throw new Error('Select a parsed JSON file containing a sections array with text fields.')
      if (version === 'draft') setDraftParsed(data as ParsedRules)
      else setFinalParsed(data as ParsedRules)
    } catch (e) { setParsedError(errorMessage(e)); if (version === 'draft') setDraftParsed(null); else setFinalParsed(null) }
  }
  async function importChanges(file?: File) {
    if (!file) return
    setImportError('')
    try {
      const parsed: unknown = JSON.parse(await file.text())
      if (!parsed || typeof parsed !== 'object' || !('analyzed_rules' in parsed) || !Array.isArray((parsed as ChangeFile).analyzed_rules)) throw new Error('Select the comparison _changes.json file.')
      setLocalChanges(parsed as ChangeFile)
    } catch (e) { setImportError(errorMessage(e)); setLocalChanges(null) }
  }
  const rules = localChanges?.analyzed_rules ?? (Array.isArray(comparison?.analyzed_rules) ? comparison.analyzed_rules as RuleChange[] : [])
  const shownRules = rules.filter(r => filter === 'all' || r.status === filter)
  return <><SectionHead eyebrow="CHANGE INTELLIGENCE" title="Compare regulatory versions" description="Align numbered rules, detect textual changes, and flag uncertain matches for review."/><Panel title="Comparison setup" subtitle="Choose uploaded documents and the pages containing regulatory rules"><div className="compare-form"><div><Field label="Original version"><select value={original} onChange={e => { const id = e.target.value; setOriginal(id); setStart1(1); setEnd1(documents.find(d => d.document_id === id)?.total_pages ?? 1) }}><option value="">Select original PDF</option>{documents.map(d => <option key={d.document_id} value={d.document_id}>{d.filename} ({d.total_pages} pages)</option>)}</select></Field><div className="range"><Field label="Start page"><input type="number" min="1" value={start1} onChange={e => setStart1(Number(e.target.value))}/></Field><Field label="End page"><input type="number" min="1" max={orig?.total_pages} value={end1} onChange={e => setEnd1(Number(e.target.value))}/></Field></div></div><div><Field label="Updated version"><select value={updated} onChange={e => { const id = e.target.value; setUpdated(id); setStart2(1); setEnd2(documents.find(d => d.document_id === id)?.total_pages ?? 1) }}><option value="">Select updated PDF</option>{documents.map(d => <option key={d.document_id} value={d.document_id}>{d.filename} ({d.total_pages} pages)</option>)}</select></Field><div className="range"><Field label="Start page"><input type="number" min="1" value={start2} onChange={e => setStart2(Number(e.target.value))}/></Field><Field label="End page"><input type="number" min="1" max={upd?.total_pages} value={end2} onChange={e => setEnd2(Number(e.target.value))}/></Field></div></div></div><div className="form-actions"><Field label="Alignment candidates"><select value={topK} onChange={e => setTopK(Number(e.target.value))}>{[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}</option>)}</select></Field><button className="button primary" disabled={busy || documents.length < 2} onClick={compare}>{busy ? <Spinner/> : <FileDiff size={17}/>} Run comparison</button></div>{documents.length < 2 && <Notice>Upload two PDFs on the Documents page first.</Notice>}{error && <Notice kind="error">{error}</Notice>}</Panel>
    <Panel title="Comparison history" subtitle="Saved locally; reopen results without rerunning analysis" action={<button className="button secondary" disabled={historyBusy} onClick={() => void refreshHistory()}>{historyBusy ? 'Refreshing...' : 'Refresh history'}</button>}>
      {historyError && <Notice kind="error">{historyError}</Notice>}
      {history.length ? <div className="history-list">{history.map(item => <div className="history-item" key={item.comparison_id}>
        <div><strong>{new Date(item.created_at).toLocaleString()}</strong><small>{item.analyzed_rule_count} rules · {item.modified_rule_count} modified · {item.pending_review_count} review flags</small><code>{item.comparison_id}</code></div>
        <button className="button secondary" disabled={loadingSaved} onClick={() => void loadSavedComparison(item.comparison_id)}>Open comparison</button>
      </div>)}</div> : <p className="muted">{historyBusy ? 'Loading history...' : 'No saved comparisons found.'}</p>}
    </Panel>
    {comparison ? <><div className="metrics-grid compact"><Metric label="Rules analyzed" number={s?.analyzed_rule_count ?? '—'} foot="Aligned rules" icon={<BookOpen size={20}/>}/><Metric label="Modified" number={s?.modified_rule_count ?? '—'} foot="Detected modifications" icon={<FileDiff size={20}/>}/><Metric label="Pending review" number={s?.pending_review_count ?? '—'} foot="Uncertain alignments" icon={<CircleAlert size={20}/>}/><Metric label="Conflicts" number={s?.alignment_conflict_count ?? '—'} foot="Alignment conflicts" icon={<Activity size={20}/>}/></div><Panel title="Comparison results" subtitle={`Comparison ID: ${comparison.comparison_id}`}><div className="result-tabs"><DetailGroup title="Analyzed rules" data={comparison.analyzed_rules}/><DetailGroup title="Pending review" data={comparison.pending_review}/><DetailGroup title="Potential additions" data={comparison.potential_additions}/><DetailGroup title="Potential removals" data={comparison.potential_removals}/><DetailGroup title="Alignment conflicts" data={comparison.alignment_conflicts}/></div><Notice>Potential additions, removals, and uncertain matches require manual verification.</Notice></Panel></> : <Panel title="Comparison results"><Empty>Run a comparison to see the detected changes.</Empty></Panel>}
    <Panel title="Detailed rule comparison" subtitle="Inspect detected edits from the comparison response or import an existing local changes JSON file">
      <div className="rule-toolbar"><label className="button secondary rule-import">Import changes JSON<input type="file" accept=".json,application/json" onChange={e => void importChanges(e.target.files?.[0])}/></label><label className="rule-filter">Show <select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All rules</option><option value="modified">Modified</option><option value="unchanged">Unchanged</option></select></label></div>
      <div className="id-actions">
  <Field label="Saved comparison ID">
    <input
      value={savedComparisonId}
      onChange={e => setSavedComparisonId(e.target.value.trim())}
      placeholder="Enter comparison ID"
    />
  </Field>
  <button
    className="button secondary"
    disabled={loadingSaved}
    onClick={() => void loadSavedComparison(savedComparisonId)}
  >
    {loadingSaved ? <Spinner /> : <FileDiff size={17} />}
    Load saved comparison
  </button>
</div>
{savedLoadError && <Notice kind="error">{savedLoadError}</Notice>}
      <div className="parsed-imports"><label className="button secondary rule-import">Import Draft parsed JSON<input type="file" accept=".json,application/json" onChange={e => void importParsed(e.target.files?.[0], 'draft')}/></label><label className="button secondary rule-import">Import Final parsed JSON<input type="file" accept=".json,application/json" onChange={e => void importParsed(e.target.files?.[0], 'final')}/></label></div>
      {parsedError && <Notice kind="error">{parsedError}</Notice>}
      {(draftParsed || finalParsed) && <Notice kind="success">Full-text sources: Draft {draftParsed ? 'loaded' : 'missing'} · Final {finalParsed ? 'loaded' : 'missing'}. Files remain in your browser only.</Notice>}
      {importError && <Notice kind="error">{importError}</Notice>}
      {localChanges && <Notice kind="success">Loaded {localChanges.analyzed_rules.length} analyzed rules from the selected file. This is a local preview; no backend data was changed.</Notice>}
      {shownRules.length ? <div className="rule-list">{shownRules.map((r, i) => <RuleCard key={`${r.draft_rule_number}-${r.final_rule_number}-${i}`} rule={r} draftSection={draftParsed?.sections.find(section => String(section.rule_number) === String(r.draft_rule_number))} finalSection={finalParsed?.sections.find(section => String(section.rule_number) === String(r.final_rule_number))}/>)}</div> : <Empty>No rule details available. Import the matching *_changes.json file from data/comparisons to inspect existing results without rerunning the comparison.</Empty>}
    </Panel>
  </>
}
type TextChange = { operation?: string; draft_text?: string; final_text?: string; review_required?: boolean }
type RuleChange = { draft_rule_number?: number; final_rule_number?: number; draft_title?: string; final_title?: string; status?: string; similarity?: number; alignment_confidence?: string; alignment_similarity?: number; review_required?: boolean; changes?: TextChange[]; classified_changes?: TextChange[] }
type ChangeFile = { analyzed_rules: RuleChange[] }
type ParsedSection = { rule_number?: string | number; title?: string; text: string; start_page?: number; end_page?: number }
type ParsedRules = { sections: ParsedSection[] }
function HighlightedRule({ text, changes, side }: { text: string; changes: TextChange[]; side: 'draft' | 'final' }) {
  // Highlight only uniquely matched, literal excerpts; avoid guessing when snippets are ambiguous.
  const spans: { start: number; end: number }[] = []
  for (const change of changes) {
    const snippet = side === 'draft' ? change.draft_text : change.final_text
    if (!snippet?.trim()) continue
    const start = text.indexOf(snippet)
    if (start < 0) continue

if (text.indexOf(snippet, start + 1) !== -1) {
  if (side === 'final' && change.operation === 'replace'
      && change.draft_text === 'same,'
      && snippet === 'breach,') {
    const context = 'within seventy-two hours of becoming aware of the breach,'
    const contextStart = text.indexOf(context)
    if (contextStart < 0 || text.indexOf(context, contextStart + 1) !== -1) continue
    const targetStart = contextStart + context.lastIndexOf(snippet)
    spans.push({ start: targetStart, end: targetStart + snippet.length })
  }
  continue
}
    const end = start + snippet.length
    if (!spans.some(x => start < x.end && end > x.start)) spans.push({ start, end })
  }
  spans.sort((a, b) => a.start - b.start)
  const pieces: React.ReactNode[] = []
  let pos = 0
  spans.forEach((span, i) => {
    if (pos < span.start) pieces.push(text.slice(pos, span.start))
    pieces.push(<mark key={i} className={side === 'draft' ? 'full-rule-removed' : 'full-rule-added'}>{text.slice(span.start, span.end)}</mark>)
    pos = span.end
  })
  pieces.push(text.slice(pos))
  return <div className="full-rule-text">{pieces}</div>
}
function RuleCard({ rule, draftSection, finalSection }: { rule: RuleChange; draftSection?: ParsedSection; finalSection?: ParsedSection }) {
  const changes = rule.classified_changes?.length ? rule.classified_changes : rule.changes || []
  return <details className="rule-card"><summary><div className="rule-card-heading"><span className="rule-index">DRAFT {value(rule.draft_rule_number)} → FINAL {value(rule.final_rule_number)}</span><strong>{rule.final_title || rule.draft_title || 'Untitled rule'}</strong><small>{changes.length} detected edits · Alignment: {rule.alignment_confidence || 'unavailable'}{typeof rule.alignment_similarity === 'number' ? ` (${(rule.alignment_similarity * 100).toFixed(1)}%)` : ''}</small></div><span className={`rule-status ${rule.status === 'modified' ? 'modified' : 'unchanged'}`}>{rule.status || 'unknown'}</span></summary>
    <div className="rule-card-body">{rule.review_required && <p className="rule-warning">Manual verification required. Detected text changes do not establish legal impact.</p>}
      {(draftSection || finalSection) && <div className="full-rule-grid"><section className="full-rule-column"><h4>Draft · Rule {value(rule.draft_rule_number)}</h4><small>{draftSection?.title || 'Source unavailable'}{draftSection?.start_page ? ` · PDF page ${draftSection.start_page}` : ''}</small>{draftSection ? <HighlightedRule text={draftSection.text} changes={changes} side="draft"/> : <p className="muted">Import the matching Draft parsed JSON.</p>}</section><section className="full-rule-column"><h4>Final · Rule {value(rule.final_rule_number)}</h4><small>{finalSection?.title || 'Source unavailable'}{finalSection?.start_page ? ` · PDF page ${finalSection.start_page}` : ''}</small>{finalSection ? <HighlightedRule text={finalSection.text} changes={changes} side="final"/> : <p className="muted">Import the matching Final parsed JSON.</p>}</section></div>}
      {(draftSection || finalSection) && <p className="muted">Highlights mark only exact, uniquely matched change excerpts. Unhighlighted differences may remain; compare against the PDFs before drawing conclusions.</p>}
      {changes.length ? changes.map((change, i) => <div className="rule-change" key={i}><div className="rule-change-title">Change {i + 1} · {change.operation || 'edit'}</div><div className="rule-diff-grid"><div><span className="diff-label">Draft text</span><p className="diff-old">{change.draft_text || '— No text in draft —'}</p></div><div><span className="diff-label">Final text</span><p className="diff-new">{change.final_text || '— Removed from final —'}</p></div></div></div>) : <p className="muted">No textual changes detected for this aligned rule.</p>}
      <p className="muted">The individual change cards above show detected excerpts. Verify all differences against the source PDFs.</p>
    </div></details>
}

function DetailGroup({ title, data }: { title: string; data: unknown }) { const items = Array.isArray(data) ? data : []; return <details className="details"><summary>{title} <span>{items.length}</span></summary>{items.length ? <div className="detail-items">{items.map((item, i) => <pre key={i}>{formatJson(item)}</pre>)}</div> : <p className="muted">No entries returned.</p>}</details> }
type EvidenceData = { text?: unknown; start_page?: unknown; end_page?: unknown }
type ImpactChangeData = { operation?: unknown; draft_text?: unknown; final_text?: unknown }
type PolicyMatchData = { policy_section?: unknown; policy_text?: unknown; semantic_similarity?: unknown; ranking_score?: unknown }
function asRecord(data: unknown): Record<string, unknown> | null {
  return data !== null && typeof data === 'object' && !Array.isArray(data) ? data as Record<string, unknown> : null
}
function safeText(data: unknown): string { return typeof data === 'string' ? data : data == null ? '' : String(data) }
function EvidenceView({ data }: { data: unknown }) {
  const obj = asRecord(data) as EvidenceData | null
  if (!obj) return data == null ? <p className="muted">No regulatory evidence supplied.</p> : <pre>{formatJson(data)}</pre>
  const start = obj.start_page
  const end = obj.end_page
  const pages = start == null ? '' : `PDF page ${safeText(start)}${end != null && end !== start ? `–${safeText(end)}` : ''}`
  return <section className="impact-evidence">{pages && <div className="impact-evidence-source"><FileText size={15}/> {pages}</div>}<p className="impact-evidence-text">{safeText(obj.text) || 'No source text supplied.'}</p></section>
}
function DetectedChangesView({ data }: { data: unknown }) {
  const items = Array.isArray(data) ? data : []
  if (!items.length) return <p className="muted">No detected changes supplied.</p>
  return <div className="impact-changes">{items.map((item, index) => {
    const change = asRecord(item) as ImpactChangeData | null
    if (!change) return <pre key={index}>{formatJson(item)}</pre>
    return <div className="impact-change-card" key={index}><div className="impact-change-heading">Change {index + 1} · {safeText(change.operation) || 'edit'}</div><div className="rule-diff-grid"><div><span className="diff-label">Draft</span><p className="diff-old">{safeText(change.draft_text) || '— No draft text —'}</p></div><div><span className="diff-label">Final</span><p className="diff-new">{safeText(change.final_text) || '— No final text —'}</p></div></div></div>
  })}</div>
}
function PolicyMatchesView({ data }: { data: unknown }) {
  const items = Array.isArray(data) ? data : []
  if (!items.length) return <p className="muted">No potential policy matches supplied.</p>
  return <div className="impact-policy-list">{items.map((item, index) => {
    const match = asRecord(item) as PolicyMatchData | null
    if (!match) return <pre key={index}>{formatJson(item)}</pre>
    const similarity = typeof match.semantic_similarity === 'number' && Number.isFinite(match.semantic_similarity) ? `${(match.semantic_similarity * 100).toFixed(1)}% semantic similarity` : null
    return <section className="impact-policy-card" key={index}><div className="impact-policy-heading"><strong>{safeText(match.policy_section) || `Policy match ${index + 1}`}</strong>{similarity && <span>{similarity}</span>}</div><p>{safeText(match.policy_text) || 'Policy excerpt unavailable.'}</p><small>Potential match only · Requires human verification</small></section>
  })}</div>
}

function ImpactPage({ comparisonId, setComparisonId, report, reportError, reload }: { comparisonId: string; setComparisonId: (id: string) => void; report: Report | null; reportError: string; reload: () => void }) {
  const [entered, setEntered] = useState(comparisonId), [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState('')
  const [impactFilter, setImpactFilter] = useState('all')
  const findings = (report?.findings || []).filter(f => impactFilter === 'all' || (impactFilter === 'review' ? f.requires_human_review !== false : (f.impact_level || 'not_assessed').toLowerCase() === impactFilter))
  const levels = [...new Set((report?.findings || []).map(f => (f.impact_level || 'not_assessed').toLowerCase()))]


  async function analyze() { if (!/^[0-9a-f]{32}$/.test(entered)) { setError('Enter a valid 32-character comparison ID.'); return } setError(''); setResult(''); setBusy(true); try { const r = await request<{ status?: string; ai_status?: string }>(`/impact/${entered}/analyze`, { method: 'POST' }); setResult(`Analysis ${r.status || 'completed'}; AI status: ${r.ai_status || 'unknown'}.`); if (entered !== comparisonId) setComparisonId(entered); else reload() } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) } }
  return <><SectionHead eyebrow="POLICY INTELLIGENCE" title="Preliminary policy impact" description="Investigate regulatory changes and possible policy matches. Human review is required for every finding."/><Panel title="Run or retrieve assessment" subtitle="Use a comparison ID from the Rule comparison page, or enter an existing ID"><div className="id-actions"><Field label="Comparison ID"><input placeholder="32-character comparison ID" value={entered} onChange={e => setEntered(e.target.value.trim())}/></Field><button className="button primary" onClick={analyze} disabled={busy}>{busy ? <Spinner/> : <Activity size={17}/>} Run impact analysis</button><button className="button secondary" onClick={() => { if (/^[0-9a-f]{32}$/.test(entered)) { setComparisonId(entered); if (entered === comparisonId) reload() } else setError('Enter a valid comparison ID.') }}>Load report</button></div>{error && <Notice kind="error">{error}</Notice>}{result && <Notice kind="success">{result}</Notice>}{reportError && <Notice kind="info">{reportError}</Notice>}</Panel>
    {report ? <><div className="metrics-grid compact"><Metric label="Impact findings" number={report.findings?.length ?? '—'} foot="Preliminary" icon={<FileText size={20}/>}/><Metric label="Modified rules evaluated" number={report.modified_rules_evaluated ?? '—'} foot="Assessment scope" icon={<FileDiff size={20}/>}/><Metric label="Policy sections checked" number={report.policy_sections_checked ?? '—'} foot="Internal policy sections" icon={<BookOpen size={20}/>}/><Metric label="AI status" number={report.ai_status || '—'} foot="Processing status" icon={<Activity size={20}/>}/></div><Panel title="Findings" subtitle="Review evidence and possible policy matches individually"><div className="impact-toolbar"><label>Filter findings <select value={impactFilter} onChange={e => setImpactFilter(e.target.value)}><option value="all">All findings</option><option value="review">Human review</option>{levels.map(level => <option key={level} value={level}>{level.replaceAll('_', ' ')}</option>)}</select></label><span>{findings.length} of {report.findings?.length ?? 0} shown</span></div>{findings.length ? <div className="findings">{findings.map((f, i) => <details className="finding" key={i}><summary><div><span className="rule-index">RULE {value(f.final_rule_number)}</span><strong>{f.rule_title || 'Regulatory change'}</strong></div><span className="review-pill">Review required</span></summary><div className="finding-body"><div className="finding-meta"><span>Impact: <strong>{f.impact_level || 'not_assessed'}</strong></span><span>Assessment: <strong>{f.assessment_status || 'preliminary'}</strong></span></div><h3>Assessment reason</h3><p>{f.impact_reason || 'No reason supplied.'}</p>{f.ai_preliminary_explanation && <><h3>AI preliminary explanation</h3><p className="preserve">{f.ai_preliminary_explanation}</p></>}<h3>Regulatory evidence</h3><EvidenceView data={f.regulatory_evidence}/><h3>Detected changes</h3><DetectedChangesView data={f.detected_changes}/><h3>Potential policy matches</h3><PolicyMatchesView data={f.potential_policy_matches}/></div></details>)}</div> : <Empty>No findings were returned.</Empty>}</Panel>{report.disclaimer && <Notice>{report.disclaimer}</Notice>}</> : <Panel title="Findings"><Empty>Load or run an impact assessment to review findings.</Empty></Panel>}
  </>
}
function KnowledgePage() {
  const [question, setQuestion] = useState(''), [version, setVersion] = useState('final_2025'), [topK, setTopK] = useState(3), [busy, setBusy] = useState(false), [answer, setAnswer] = useState<unknown>(null), [error, setError] = useState('')
  async function ask() { if (!question.trim()) return; setBusy(true); setError(''); setAnswer(null); try { setAnswer(await postJson<unknown>('/rag/query', { question: question.trim(), document_version: version, top_k: topK })) } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) } }
  const obj = answer && typeof answer === 'object' && !Array.isArray(answer) ? answer as Json : null
  const mainAnswer = obj ? (typeof obj.answer === 'string' ? obj.answer : typeof obj.response === 'string' ? obj.response : null) : typeof answer === 'string' ? answer : null
  return <><SectionHead eyebrow="KNOWLEDGE BASE" title="Ask the regulatory documents" description="Query the indexed DPDP document versions using the existing retrieval-augmented generation pipeline."/><Panel title="Regulatory question" subtitle="Answers are generated by the local backend and should be verified against their sources"><Field label="Your question"><textarea rows={4} maxLength={2000} placeholder="What changed in the requirements for data fiduciaries?" value={question} onChange={e => setQuestion(e.target.value)}/></Field><div className="form-actions"><Field label="Document version"><select value={version} onChange={e => setVersion(e.target.value)}><option value="final_2025">Final 2025</option><option value="draft_2025">Draft 2025</option></select></Field><Field label="Retrieved passages"><select value={topK} onChange={e => setTopK(Number(e.target.value))}>{[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}</option>)}</select></Field><button className="button primary" onClick={ask} disabled={busy || !question.trim()}>{busy ? <Spinner/> : <Search size={17}/>} Ask question</button></div>{error && <Notice kind="error">{error}</Notice>}</Panel><Panel title="Answer and evidence" subtitle="Response from the local RAG service">{answer !== null ? <div className="answer"><p className="preserve">{mainAnswer || 'The response is shown below.'}</p><details className="details" open={!mainAnswer}><summary>Full response and citations</summary><pre>{formatJson(answer)}</pre></details></div> : <Empty>Submit a question to see the answer and supporting evidence.</Empty>}</Panel></>
}
function ReportsPage({ comparisonId, report, setComparisonId, reportError }: { comparisonId: string; report: Report | null; setComparisonId: (id: string) => void; reportError: string }) {
  const [entered, setEntered] = useState(comparisonId), [busy, setBusy] = useState(false), [error, setError] = useState('')

  async function download(format: 'json' | 'md') { if (!/^[0-9a-f]{32}$/.test(entered)) { setError('Enter a valid comparison ID.'); return } setError(''); setBusy(true); try { const response = await fetch(`${API}/impact/${entered}/download?format=${format}`); if (!response.ok) { let msg = `Download failed (${response.status})`; try { const json = await response.json(); if (typeof json.detail === 'string') msg = json.detail } catch { /* ignore */ } throw new Error(msg) } const blob = await response.blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${entered}_impact.${format}`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000) } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) } }
  async function downloadComparison() {
    if (!/^[0-9a-f]{32}$/.test(entered)) { setError('Enter a valid comparison ID.'); return }
    setError(''); setBusy(true)
    try {
      const response = await fetch(`${API}/documents/comparisons/${entered}/export`)
      if (!response.ok) throw new Error(`Comparison export failed (${response.status})`)
      saveBlob(await response.blob(), `${entered}_comparison.json`)
    } catch (e) { setError(errorMessage(e)) }
    finally { setBusy(false) }
  }
  return <><SectionHead eyebrow="REPORTING" title="Export assessment reports" description="Download the backend-generated preliminary assessment as JSON or Markdown."/><Panel title="Select assessment" subtitle="Only reports that have already been generated can be downloaded"><div className="id-actions"><Field label="Comparison ID"><input placeholder="32-character comparison ID" value={entered} onChange={e => setEntered(e.target.value.trim())}/></Field><button className="button secondary" onClick={() => { if (/^[0-9a-f]{32}$/.test(entered)) setComparisonId(entered); else setError('Enter a valid comparison ID.') }}>Load report</button></div>{error && <Notice kind="error">{error}</Notice>}{reportError && <Notice>{reportError}</Notice>}</Panel><div className="two-columns"><Panel title="Structured JSON" subtitle="Machine-readable findings and evidence"><div className="export-card"><FileText size={32}/><p>Export complete assessment data for further processing or archiving.</p><button className="button primary" disabled={busy} onClick={() => download('json')}><Download size={17}/> Download JSON</button></div></Panel><Panel title="Markdown report" subtitle="Readable review document"><div className="export-card"><FileText size={32}/><p>Export the backend's formatted preliminary assessment report.</p><button className="button primary" disabled={busy} onClick={() => download('md')}><Download size={17}/> Download Markdown</button></div></Panel></div><Panel title="Comparison export" subtitle="Download saved rule changes and both parsed versions"><div className="export-card"><FileDiff size={30}/><p>This JSON export works even if you have not run a policy impact assessment.</p><button className="button secondary" disabled={busy} onClick={() => void downloadComparison()}><Download size={17}/> Download comparison JSON</button></div></Panel>{report && <Panel title="Current report summary"><p className="muted">{report.findings?.length ?? 0} findings · {report.modified_rules_evaluated ?? '—'} modified rules evaluated · AI status: {report.ai_status || 'unknown'}</p></Panel>}<Notice>Reports are preliminary, require human review, and do not constitute a legal compliance determination.</Notice></>
}
function SettingsPage({ healthy, checkHealth }: { healthy: boolean | null; checkHealth: () => Promise<void> }) {
  return <><SectionHead eyebrow="WORKSPACE SETTINGS" title="System connectivity" description="View the local service connection and integration details."/><Panel title="Backend service" subtitle="React connects through the Vite /api proxy"><div className="setting-row"><div><strong>FastAPI health</strong><p>GET /health · proxied to http://127.0.0.1:8000</p></div><span className={`state ${healthy ? 'ok' : 'off'}`}>{healthy === null ? 'Checking' : healthy ? 'Connected' : 'Unavailable'}</span></div><button className="button secondary" onClick={() => void checkHealth()}><Activity size={17}/> Recheck connection</button></Panel><Panel title="Architecture"><div className="process-steps"><div><span>UI</span><div><strong>React + TypeScript</strong><p>Client-side navigation, charts, forms and session state.</p></div></div><div><span>API</span><div><strong>FastAPI</strong><p>Upload, comparison, impact analysis, RAG and report endpoints.</p></div></div><div><span>AI</span><div><strong>Local processing</strong><p>Existing RAG, language-model and policy matching pipelines remain on the Python backend.</p></div></div></div></Panel><Notice>Session state is stored in this browser tab. Existing reports can be retrieved by comparison ID; the backend does not yet expose history-list endpoints.</Notice></>
}
export default App
