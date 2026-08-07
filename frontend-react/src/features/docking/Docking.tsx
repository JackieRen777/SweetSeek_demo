import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, Download, FileCode2, Play, Upload, X } from 'lucide-react';
import StructureViewer from '../md-builder/StructureViewer';
import './docking.css';

type DockingKind = 'protein_ligand' | 'protein_protein';
type Uploaded = { role: 'receptor' | 'ligand'; file: File };
type Pose = { id: string; rank: number; score: number | null; structure: string; format: string };
type Job = { id: string; status: string; progress: number; error?: string | null; poses: Pose[] };
export type SelectedDockingPose = Pose & { jobId: string };
interface DockingProps { onPoseSelected?: (pose: SelectedDockingPose | null) => void }

const labels: Record<DockingKind, string> = { protein_ligand: 'Protein–small molecule', protein_protein: 'Protein–protein' };

export default function Docking({ onPoseSelected }: DockingProps) {
  const [kind, setKind] = useState<DockingKind>('protein_ligand');
  const [uploads, setUploads] = useState<Uploaded[]>([]);
  const [poses, setPoses] = useState(10);
  const [exhaustiveness, setExhaustiveness] = useState(8);
  const [job, setJob] = useState<Job | null>(null);
  const [engine, setEngine] = useState<Record<string, { available: boolean; engine: string; install: string }>>({});
  const [error, setError] = useState('');
  const [selectedPose, setSelectedPose] = useState(0);
  const receptorInput = useRef<HTMLInputElement>(null);
  const ligandInput = useRef<HTMLInputElement>(null);
  const activePose = job?.poses[selectedPose];
  useEffect(() => {
    onPoseSelected?.(activePose && job ? { ...activePose, jobId: job.id } : null);
  }, [activePose, job?.id, onPoseSelected]);

  useEffect(() => {
    fetch('/api/docking/status').then(response => response.json()).then(data => setEngine(data.engines || {})).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return;
    const timer = window.setInterval(() => {
      fetch(`/api/docking/jobs/${job.id}`).then(response => response.json()).then(data => data.job && setJob(data.job)).catch(() => undefined);
    }, 1200);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  const setFile = (role: Uploaded['role'], file: File | undefined) => {
    if (!file) return;
    setError('');
    setUploads(previous => [...previous.filter(item => item.role !== role), { role, file }]);
    setJob(null);
  };

  const canRun = uploads.length === 2 && uploads.some(item => item.role === 'receptor') && uploads.some(item => item.role === 'ligand') && !job;
  const viewerContents = useMemo(() => activePose ? [{ name: activePose.id, format: 'pdb', text: activePose.structure }] : [], [activePose]);

  const run = async () => {
    if (!canRun) return;
    setError(''); setSelectedPose(0);
    const form = new FormData();
    form.append('kind', kind);
    form.append('options', JSON.stringify({ poses, exhaustiveness }));
    uploads.forEach(item => form.append(item.role, item.file, item.file.name));
    try {
      const response = await fetch('/api/docking/jobs', { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not start docking.');
      setJob(data.job);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not start docking.'); }
  };

  const reset = () => { setUploads([]); setJob(null); setError(''); setSelectedPose(0); };

  return <div className="dock-shell">
    <header className="dock-header">
      <div><span className="dock-kicker">STRUCTURAL COMPUTATION</span><h1>Docking workspace</h1><p>Generate ranked binding poses on the application server.</p></div>
      <div className="dock-engine-status">{Object.entries(engine).map(([key, value]) => <span key={key} className={value.available ? 'ready' : 'offline'}><i />{labels[key as DockingKind]} · {value.available ? 'ready' : 'engine unavailable'}</span>)}</div>
    </header>
    {error && <div className="dock-alert"><AlertTriangle size={16} />{error}<button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
    <div className="dock-layout">
      <main className="dock-main">
        <section className="dock-section"><div className="dock-section-title"><span>01</span><div><h2>Choose docking type</h2><p>The server selects the appropriate engine and input preparation.</p></div></div><div className="dock-segmented">{(Object.keys(labels) as DockingKind[]).map(option => <button key={option} className={kind === option ? 'active' : ''} onClick={() => { setKind(option); reset(); }}>{labels[option]}</button>)}</div></section>
        <section className="dock-section"><div className="dock-section-title"><span>02</span><div><h2>Provide structures</h2><p>Files are kept in the job workspace and removed after completion.</p></div></div><div className="dock-upload-grid">
          <button className="dock-upload" onClick={() => receptorInput.current?.click()} disabled={!!job}><Upload size={20} /><strong>{uploads.find(item => item.role === 'receptor')?.file.name || 'Upload receptor PDB'}</strong><small>Protein receptor · .pdb</small></button>
          <button className="dock-upload" onClick={() => ligandInput.current?.click()} disabled={!!job}><Upload size={20} /><strong>{uploads.find(item => item.role === 'ligand')?.file.name || (kind === 'protein_ligand' ? 'Upload ligand' : 'Upload partner PDB')}</strong><small>{kind === 'protein_ligand' ? 'MOL2, SDF, or PDB' : 'Protein partner · .pdb'}</small></button>
          <input ref={receptorInput} type="file" accept=".pdb,.ent" hidden onChange={event => setFile('receptor', event.target.files?.[0])} />
          <input ref={ligandInput} type="file" accept={kind === 'protein_ligand' ? '.mol2,.sdf,.pdb' : '.pdb,.ent'} hidden onChange={event => setFile('ligand', event.target.files?.[0])} />
        </div><div className="dock-file-list">{uploads.map(item => <div key={item.role}><FileCode2 size={16} /><span><b>{item.file.name}</b><small>{item.role === 'receptor' ? 'Receptor' : kind === 'protein_ligand' ? 'Ligand' : 'Partner 2'} · {(item.file.size / 1024).toFixed(1)} KB</small></span><button onClick={() => setUploads(previous => previous.filter(file => file.role !== item.role))} aria-label={`Remove ${item.role}`}><X size={15} /></button></div>)}</div></section>
        <section className="dock-section"><div className="dock-section-title"><span>03</span><div><h2>Search settings</h2><p>Higher exhaustiveness explores more orientations and takes longer.</p></div></div><div className="dock-controls"><label>Number of poses<input type="number" min="1" max="20" value={poses} onChange={event => setPoses(Number(event.target.value))} /></label><label>Exhaustiveness<input type="number" min="1" max="64" value={exhaustiveness} onChange={event => setExhaustiveness(Number(event.target.value))} /></label></div></section>
        <div className="dock-actions"><button className="dock-run" onClick={() => void run()} disabled={!canRun}><Play size={17} />{job?.status === 'running' ? 'Docking in progress' : 'Run docking'}</button>{(uploads.length > 0 || job) && <button className="dock-reset" onClick={reset}>Clear workspace</button>}</div>
      </main>
      <aside className="dock-results"><div className="dock-results-header"><div><span>04</span><h2>Ranked poses</h2></div>{job && <span className={`dock-job-state ${job.status}`}>{job.status}</span>}</div>{job && ['queued', 'running'].includes(job.status) && <div className="dock-progress"><div><span>Calculating on server</span><b>{job.progress}%</b></div><progress value={job.progress} max="100" /></div>}{job?.status === 'failed' && <div className="dock-failure"><AlertTriangle size={18} /><p>{job.error}</p></div>}{job?.status === 'complete' && <div className="dock-complete"><CheckCircle2 size={17} />{job.poses.length} poses available</div>}{job?.poses?.length ? <><div className="dock-pose-list">{job.poses.map((pose, index) => <button key={pose.id} className={index === selectedPose ? 'selected' : ''} onClick={() => setSelectedPose(index)}><span className="pose-rank">{String(pose.rank).padStart(2, '0')}</span><span><b>{pose.id}</b><small>{pose.score === null ? 'Score pending' : `${pose.score.toFixed(2)} kcal/mol`}</small></span><ChevronDown size={14} /></button>)}</div><StructureViewer contents={viewerContents} /><a className="dock-download" href={`data:text/plain;charset=utf-8,${encodeURIComponent(activePose?.structure || '')}`} download={`${activePose?.id || 'pose'}.pdb`}><Download size={16} /> Download selected pose</a></> : !job && <div className="dock-empty"><FileCode2 size={28} /><p>Run a docking job to review ranked poses here.</p></div>}</aside>
    </div>
  </div>;
}
