import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, Download, FileCode2, Play, Upload, X } from 'lucide-react';
import StructureViewer from '../md-builder/StructureViewer';
import './docking.css';

export type DockingKind = 'protein_ligand' | 'protein_protein';
type DockingMode = 'rigid' | 'flexible';
type Uploaded = { role: 'receptor' | 'ligand'; file: File };
export type SelectedDockingPose = {
  id: string; rank: number; score: number | null; score_unit: string;
  score_method: string; kind: DockingKind; mode: DockingMode; parameters: Record<string, unknown>;
  jobId: string;
};
type Job = {
  id: string; kind: DockingKind; mode: DockingMode; status: string; stage: string;
  error?: string | null; poses: Omit<SelectedDockingPose, 'jobId'>[];
};
export interface DockingHandoff {
  pose: SelectedDockingPose;
  files: File[];
  complex: string;
}
interface DockingProps {
  onConfirm?: (handoff: DockingHandoff) => void;
  onSkip?: () => void;
  onDirty?: () => void;
}

const labels: Record<DockingKind, string> = {
  protein_ligand: 'Protein-small molecule',
  protein_protein: 'Protein-protein',
};
const terminal = new Set(['complete', 'failed', 'expired']);

export default function Docking({ onConfirm, onSkip, onDirty }: DockingProps) {
  const [kind, setKind] = useState<DockingKind>('protein_ligand');
  const [mode, setMode] = useState<DockingMode>('rigid');
  const [uploads, setUploads] = useState<Uploaded[]>([]);
  const [poses, setPoses] = useState(10);
  const [exhaustiveness, setExhaustiveness] = useState(8);
  const [centerMode, setCenterMode] = useState<'auto' | 'manual'>('auto');
  const [center, setCenter] = useState({ x: 0, y: 0, z: 0 });
  const [box, setBox] = useState({ x: 30, y: 30, z: 30 });
  const [flexResidues, setFlexResidues] = useState('');
  const [swarms, setSwarms] = useState(100);
  const [steps, setSteps] = useState(20);
  const [anmModes, setAnmModes] = useState(10);
  const [job, setJob] = useState<Job | null>(null);
  const [engine, setEngine] = useState<Record<string, { available: boolean; engine: string }>>({});
  const [error, setError] = useState('');
  const [selectedPose, setSelectedPose] = useState(0);
  const [structure, setStructure] = useState('');
  const receptorInput = useRef<HTMLInputElement>(null);
  const ligandInput = useRef<HTMLInputElement>(null);
  const activePose = job?.poses[selectedPose];

  useEffect(() => {
    fetch('/api/docking/status').then(response => response.json())
      .then(data => setEngine(data.engines || {})).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!job || terminal.has(job.status)) return;
    const timer = window.setInterval(() => {
      fetch(`/api/docking/jobs/${job.id}`).then(response => response.json())
        .then(data => data.job && setJob(data.job)).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  useEffect(() => {
    if (!activePose || !job) { setStructure(''); return; }
    let cancelled = false;
    fetch(`/api/docking/jobs/${job.id}/poses/${activePose.id}/structure`)
      .then(response => {
        if (!response.ok) throw new Error('Pose structure is unavailable.');
        return response.text();
      })
      .then(text => { if (!cancelled) setStructure(text); })
      .catch(caught => { if (!cancelled) setError(caught instanceof Error ? caught.message : 'Could not load pose.'); });
    return () => { cancelled = true; };
  }, [activePose?.id, job?.id]);

  const invalidate = () => {
    setJob(null); setSelectedPose(0); setStructure(''); setError(''); onDirty?.();
  };
  const setFile = (role: Uploaded['role'], file: File | undefined) => {
    if (!file) return;
    setUploads(previous => [...previous.filter(item => item.role !== role), { role, file }]);
    invalidate();
  };
  const selectKind = (next: DockingKind) => {
    setKind(next); setMode('rigid'); setUploads([]); invalidate();
  };
  const canRun = uploads.length === 2 && !job && engine[kind]?.available === true;
  const viewerContents = useMemo(() => structure ? [{ name: activePose?.id || 'pose', format: 'pdb', text: structure }] : [], [structure, activePose?.id]);

  const run = async () => {
    if (!canRun) return;
    setError(''); setSelectedPose(0); setStructure(''); onDirty?.();
    const options: Record<string, unknown> = { mode, poses };
    if (kind === 'protein_ligand') {
      Object.assign(options, {
        exhaustiveness, center_mode: centerMode,
        center_x: center.x, center_y: center.y, center_z: center.z,
        size_x: box.x, size_y: box.y, size_z: box.z,
        flex_residues: flexResidues.split(',').map(item => item.trim()).filter(Boolean),
      });
    } else Object.assign(options, { swarms, steps, anm_modes: anmModes });
    const form = new FormData();
    form.append('kind', kind); form.append('options', JSON.stringify(options));
    uploads.forEach(item => form.append(item.role, item.file, item.file.name));
    try {
      const response = await fetch('/api/docking/jobs', { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not start docking.');
      setJob(data.job);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not start docking.'); }
  };

  const confirmPose = () => {
    if (!activePose || !job || !structure) return;
    onConfirm?.({ pose: { ...activePose, jobId: job.id }, files: uploads.map(item => item.file), complex: structure });
  };
  const reset = () => { setUploads([]); invalidate(); };
  const numberField = (label: string, value: number, setter: (value: number) => void, min: number, max: number) => (
    <label key={label}>{label}<input type="number" min={min} max={max} value={value} onChange={event => { setter(Number(event.target.value)); invalidate(); }} /></label>
  );

  return <div className="dock-shell">
    <header className="dock-header">
      <div><span className="dock-kicker">STEP 1 · STRUCTURAL COMPUTATION</span><h1>Docking</h1><p>Generate and select a starting complex for AMBER preparation.</p></div>
      <button className="dock-skip" onClick={onSkip}>Skip docking</button>
    </header>
    {error && <div className="dock-alert"><AlertTriangle size={16} />{error}<button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
    <div className="dock-layout">
      <main className="dock-main">
        <section className="dock-section"><div className="dock-section-title"><span>01</span><div><h2>System</h2><p>Select the molecular partners.</p></div></div>
          <div className="dock-segmented">{(Object.keys(labels) as DockingKind[]).map(option => <button key={option} className={kind === option ? 'active' : ''} onClick={() => selectKind(option)}>{labels[option]}</button>)}</div>
          <div className="dock-engine-status">{engine[kind] && <span className={engine[kind].available ? 'ready' : 'offline'}><i />{engine[kind].engine} · {engine[kind].available ? 'ready' : 'worker engine unavailable'}</span>}</div>
        </section>
        <section className="dock-section"><div className="dock-section-title"><span>02</span><div><h2>Structures</h2><p>Inputs are retained for 24 hours with the job.</p></div></div>
          <div className="dock-upload-grid">
            <button className="dock-upload" onClick={() => receptorInput.current?.click()} disabled={!!job}><Upload size={20} /><strong>{uploads.find(item => item.role === 'receptor')?.file.name || 'Upload receptor PDB'}</strong><small>Protein receptor · PDB</small></button>
            <button className="dock-upload" onClick={() => ligandInput.current?.click()} disabled={!!job}><Upload size={20} /><strong>{uploads.find(item => item.role === 'ligand')?.file.name || (kind === 'protein_ligand' ? 'Upload ligand' : 'Upload partner PDB')}</strong><small>{kind === 'protein_ligand' ? 'MOL2, SDF, or PDB' : 'Protein partner · PDB'}</small></button>
            <input ref={receptorInput} type="file" accept=".pdb,.ent" hidden onChange={event => setFile('receptor', event.target.files?.[0])} />
            <input ref={ligandInput} type="file" accept={kind === 'protein_ligand' ? '.mol2,.sdf,.pdb' : '.pdb,.ent'} hidden onChange={event => setFile('ligand', event.target.files?.[0])} />
          </div>
          <div className="dock-file-list">{uploads.map(item => <div key={item.role}><FileCode2 size={16} /><span><b>{item.file.name}</b><small>{item.role === 'receptor' ? 'Receptor' : kind === 'protein_ligand' ? 'Ligand' : 'Partner 2'} · {(item.file.size / 1024).toFixed(1)} KB</small></span><button onClick={() => { setUploads(previous => previous.filter(file => file.role !== item.role)); invalidate(); }} aria-label={`Remove ${item.role}`}><X size={15} /></button></div>)}</div>
        </section>
        <section className="dock-section"><div className="dock-section-title"><span>03</span><div><h2>Search settings</h2><p>Server-safe limits protect the Q&A service.</p></div></div>
          <div className="dock-segmented"><button className={mode === 'rigid' ? 'active' : ''} onClick={() => { setMode('rigid'); invalidate(); }}>{kind === 'protein_ligand' ? 'Rigid receptor' : 'Rigid body'}</button><button className={mode === 'flexible' ? 'active' : ''} onClick={() => { setMode('flexible'); invalidate(); }}>Limited flexibility</button></div>
          <div className="dock-controls">{numberField('Number of poses', poses, setPoses, 1, 20)}
            {kind === 'protein_ligand' ? <>
              {numberField('Exhaustiveness', exhaustiveness, setExhaustiveness, 1, 64)}
              <label>Search center<select value={centerMode} onChange={event => { setCenterMode(event.target.value as 'auto' | 'manual'); invalidate(); }}><option value="auto">Receptor geometric center</option><option value="manual">Manual coordinates</option></select></label>
              {mode === 'flexible' && <label className="dock-wide">Flexible residues<input value={flexResidues} placeholder="A:42, A:45 (maximum 8)" onChange={event => { setFlexResidues(event.target.value); invalidate(); }} /></label>}
            </> : <>{numberField('Swarms', swarms, setSwarms, 1, 100)}{numberField('Optimization steps', steps, setSteps, 1, 50)}{mode === 'flexible' && numberField('ANM modes', anmModes, setAnmModes, 1, 10)}</>}
          </div>
          {kind === 'protein_ligand' && <details className="dock-advanced"><summary>Search box <ChevronDown size={15} /></summary>
            {centerMode === 'manual' && <div className="dock-coordinate-grid">{(['x', 'y', 'z'] as const).map(axis => numberField(`Center ${axis.toUpperCase()}`, center[axis], value => setCenter(previous => ({ ...previous, [axis]: value })), -10000, 10000))}</div>}
            <div className="dock-coordinate-grid">{(['x', 'y', 'z'] as const).map(axis => numberField(`Size ${axis.toUpperCase()} (A)`, box[axis], value => setBox(previous => ({ ...previous, [axis]: value })), 10, 40))}</div>
          </details>}
        </section>
        <div className="dock-actions"><button className="dock-run" onClick={() => void run()} disabled={!canRun}><Play size={17} />{job && !terminal.has(job.status) ? 'Docking in progress' : 'Run docking'}</button>{(uploads.length > 0 || job) && <button className="dock-reset" onClick={reset}>Clear workspace</button>}</div>
      </main>
      <aside className="dock-results"><div className="dock-results-header"><div><span>04</span><h2>Ranked poses</h2></div>{job && <span className={`dock-job-state ${job.status}`}>{job.stage}</span>}</div>
        {job && !terminal.has(job.status) && <div className="dock-progress"><div><span>{job.stage}</span><b>single-worker queue</b></div><progress /></div>}
        {job?.status === 'failed' && <div className="dock-failure"><AlertTriangle size={18} /><p>{job.error}</p></div>}
        {job?.status === 'complete' && <div className="dock-complete"><CheckCircle2 size={17} />{job.poses.length} poses available</div>}
        {job?.poses?.length ? <><div className="dock-pose-list">{job.poses.map((pose, index) => <button key={pose.id} className={index === selectedPose ? 'selected' : ''} onClick={() => setSelectedPose(index)}><span className="pose-rank">{String(pose.rank).padStart(2, '0')}</span><span><b>{pose.id}</b><small>{pose.score === null ? 'Score unavailable' : `${pose.score.toFixed(2)} ${pose.score_unit}`}</small></span><ChevronDown size={14} /></button>)}</div>
          <StructureViewer contents={viewerContents} />
          <div className="dock-pose-actions"><a className="dock-download" download={`${activePose?.id || 'pose'}-complex.pdb`} href={`/api/docking/jobs/${job.id}/poses/${activePose?.id}/complex.pdb`}><Download size={16} />Download complex PDB</a><button className="dock-use-pose" onClick={confirmPose} disabled={!structure}><CheckCircle2 size={16} />Use this pose for MD</button></div>
        </> : !job && <div className="dock-empty"><FileCode2 size={28} /><p>Submit a docking job to review ranked complexes.</p></div>}
      </aside>
    </div>
  </div>;
}
