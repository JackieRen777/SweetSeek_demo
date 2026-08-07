import { useEffect, useMemo, useRef, useState, type WheelEvent } from 'react';
import {
  AlertTriangle, Bot, Check, ChevronDown, Download, FileArchive, FileCode2,
  Loader2, RefreshCw, Send, Upload, WandSparkles, X,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './amber-md-builder.css';
import StructureViewer from './StructureViewer';
import Docking from '../docking/Docking';

type SystemChoice = 'single_protein' | 'protein_protein' | 'protein_ligand';
type Tab = 'setup' | 'files' | 'expert' | 'docking';
type ChainGroup = 'partner1' | 'partner2' | 'excluded';

interface ChainInfo { id: string; residues: number; name: string }
interface Inspection {
  filename: string;
  format: 'pdb' | 'mol2' | 'sdf';
  atoms: number;
  residues: number;
  chains: ChainInfo[];
  warnings: string[];
  unsupported: string[];
  valid: boolean;
  has_charges?: boolean;
  net_charge?: number | null;
}
interface StructureEntry {
  source: 'upload' | 'rcsb';
  filename: string;
  inspection: Inspection;
  file?: File;
  pdb_id?: string;
  unit?: 'asymmetric' | 'assembly';
  assembly_id?: number;
}

interface ExpertMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  confidence?: 'low' | 'medium' | 'high';
  checks?: string[];
}

interface Parameters {
  project_name: string;
  simulation_time_ns: number;
  temperature_k: number;
  pressure_bar: number;
  preset: 'standard' | 'compatibility';
  protein_force_field: 'ff19SB' | 'ff14SB';
  water_model: 'OPCBOX' | 'TIP3PBOX';
  solvent_padding_a: number;
  cutoff_a: number;
  salt_molar: number;
  timestep_fs: number;
  heating_ps: number;
  equilibration_ps: number;
  trajectory_interval_ps: number;
  charge_method: 'am1bcc' | 'resp' | 'existing';
  ligand_net_charge: number;
  ligand_multiplicity: number;
}

const DEFAULT_PARAMETERS: Parameters = {
  project_name: 'amber_md_project', simulation_time_ns: 50, temperature_k: 300,
  pressure_bar: 1, preset: 'standard', protein_force_field: 'ff19SB',
  water_model: 'OPCBOX', solvent_padding_a: 12, cutoff_a: 10,
  salt_molar: 0, timestep_fs: 2, heating_ps: 200, equilibration_ps: 1000,
  trajectory_interval_ps: 10, charge_method: 'am1bcc', ligand_net_charge: 0,
  ligand_multiplicity: 1,
};

const PARAMETER_LABELS: Partial<Record<keyof Parameters, string>> = {
  project_name: 'project name',
  simulation_time_ns: 'production time',
  temperature_k: 'temperature',
  pressure_bar: 'pressure',
  preset: 'protocol preset',
  salt_molar: 'salt concentration',
  charge_method: 'ligand charge method',
  ligand_net_charge: 'ligand net charge',
  ligand_multiplicity: 'ligand multiplicity',
};

const PARAMETER_KEYS = new Set<keyof Parameters>(Object.keys(DEFAULT_PARAMETERS) as (keyof Parameters)[]);

const GENERATED_FILES = [
  'README.md', 'parameters.json', 'inputs/', 'run_md.sh', 'leap.in',
  'md/min1.in', 'md/min2.in', 'md/heat.in', 'md/equil.in', 'md/prod.in',
  'analyse/analyse.sh',
];

function resolvedSetup(choice: SystemChoice, structures: StructureEntry[]) {
  const pdbs = structures.filter(item => item.inspection.format === 'pdb');
  const mol2s = structures.filter(item => item.inspection.format === 'mol2' || item.inspection.format === 'sdf');
  const system = choice;
  const inputMode = system === 'protein_protein'
    ? (pdbs.length === 2 ? 'two_partners' : 'single_complex')
    : 'single_structure';
  return { system, inputMode, pdbs, mol2s };
}

export default function AmberMDBuilder() {
  const [tab, setTab] = useState<Tab>('setup');
  const [systemChoice, setSystemChoice] = useState<SystemChoice>('single_protein');
  const [structures, setStructures] = useState<StructureEntry[]>([]);
  const [chainGroups, setChainGroups] = useState<Record<string, ChainGroup>>({});
  const [parameters, setParameters] = useState<Parameters>(DEFAULT_PARAMETERS);
  const [lockedFields, setLockedFields] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<'inspect' | 'generate' | null>(null);
  const [chatBusy, setChatBusy] = useState(false);
  const [expertInput, setExpertInput] = useState('');
  const [expertMessages, setExpertMessages] = useState<ExpertMessage[]>([]);
  const [suggestedUpdates, setSuggestedUpdates] = useState<Partial<Parameters> | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [viewerContents, setViewerContents] = useState<Array<{ name: string; format: string; text: string }>>([]);
  const [download, setDownload] = useState<{ url: string; name: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const partner1InputRef = useRef<HTMLInputElement>(null);
  const partner2InputRef = useRef<HTMLInputElement>(null);
  const ligandInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const setup = useMemo(() => resolvedSetup(systemChoice, structures), [systemChoice, structures]);
  const complexChains = setup.inputMode === 'single_complex' ? setup.pdbs[0]?.inspection.chains ?? [] : [];
  const canUseExistingCharges = setup.mol2s[0]?.inspection.has_charges === true;

  useEffect(() => () => {
    if (download) URL.revokeObjectURL(download.url);
  }, [download]);

  useEffect(() => {
    if (typeof chatEndRef.current?.scrollIntoView === 'function') chatEndRef.current.scrollIntoView({ block: 'end' });
  }, [expertMessages, chatBusy]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all(structures.filter(item => item.file).map(async item => ({ name: item.filename, format: item.inspection.format, text: await item.file!.text() }))).then(items => { if (!cancelled) setViewerContents(items); });
    return () => { cancelled = true; };
  }, [structures]);

  const scrollPanel = (event: WheelEvent<HTMLElement>) => {
    const panel = event.currentTarget;
    if (event.deltaY && panel.scrollHeight > panel.clientHeight) {
      event.preventDefault();
      panel.scrollTop += event.deltaY;
    }
  };

  const updateParameter = <K extends keyof Parameters>(key: K, value: Parameters[K]) => {
    setParameters(previous => ({ ...previous, [key]: value }));
    setLockedFields(previous => new Set(previous).add(key));
    if (key === 'preset') {
      const standard = value === 'standard';
      setParameters(previous => ({
        ...previous, preset: value as Parameters['preset'],
        protein_force_field: standard ? 'ff19SB' : 'ff14SB',
        water_model: standard ? 'OPCBOX' : 'TIP3PBOX',
      }));
    }
  };

  const addEntries = (entries: StructureEntry[]) => {
    setStructures(previous => {
      const combined = [...previous, ...entries].slice(0, 3);
      const pdbs = combined.filter(item => item.inspection.format === 'pdb');
      const mol2s = combined.filter(item => item.inspection.format === 'mol2' || item.inspection.format === 'sdf');
      if (pdbs.length > 2 || mol2s.length > 1) {
        setError('Use at most two PDB files and one MOL2 or SDF file.');
        return previous;
      }
      if (pdbs.length === 1 && pdbs[0].inspection.chains.length === 2) {
        setChainGroups({
          [pdbs[0].inspection.chains[0].id]: 'partner1',
          [pdbs[0].inspection.chains[1].id]: 'partner2',
        });
      }
      return combined;
    });
  };

  const inspectFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy('inspect'); setError(''); setNotice('');
    const form = new FormData();
    Array.from(files).forEach(file => form.append('files', file));
    try {
      const response = await fetch('/api/md-builder/inspect', { method: 'POST', body: form });
      const responseText = await response.text();
      let data: { structures?: Inspection[]; error?: string };
      try {
        data = JSON.parse(responseText) as { structures?: Inspection[]; error?: string };
      } catch {
        throw new Error(responseText.trim().startsWith('<!doctype') || responseText.trim().startsWith('<html')
          ? 'MD backend is not serving this route. Restart the Flask backend on port 5001 and try again.'
          : `MD backend returned an invalid response (${response.status}).`);
      }
      if (!response.ok) throw new Error(data.error || 'Could not inspect the files.');
      const selectedFiles = Array.from(files);
      addEntries((data.structures || []).map((inspection: Inspection, index: number) => ({
        source: 'upload', filename: inspection.filename, inspection,
        file: selectedFiles[index],
      })));
      setNotice('Structures inspected. Review the detected system and chains.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Inspection failed.'); }
    finally { setBusy(null); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const normalizeUpdates = (value: unknown) => {
    if (!value || typeof value !== 'object') return {} as Partial<Parameters>;
    const updates = Object.fromEntries(Object.entries(value).filter(([key, item]) =>
      PARAMETER_KEYS.has(key as keyof Parameters) && !lockedFields.has(key) && item !== null,
    )) as Partial<Parameters>;
    if (updates.preset && !updates.protein_force_field && !updates.water_model) {
      updates.protein_force_field = updates.preset === 'standard' ? 'ff19SB' : 'ff14SB';
      updates.water_model = updates.preset === 'standard' ? 'OPCBOX' : 'TIP3PBOX';
    }
    return updates;
  };

  const applyExpertUpdates = (updates: Partial<Parameters>, lockApplied: boolean) => {
    const changed = (Object.keys(updates) as (keyof Parameters)[]).filter(key => parameters[key] !== updates[key]);
    if (!changed.length) return;
    setParameters(previous => ({ ...previous, ...updates }));
    if (lockApplied) {
      setLockedFields(previous => new Set([...previous, ...changed]));
    }
    setSuggestedUpdates(null);
    setNotice(`${changed.length} ${changed.length === 1 ? 'parameter' : 'parameters'} updated: ${changed.map(key => PARAMETER_LABELS[key] || key.replaceAll('_', ' ')).join(', ')}.`);
  };

  const sendExpertMessage = async (message = expertInput) => {
    const question = message.trim();
    if (!question || chatBusy) return;
    const userMessage: ExpertMessage = { id: `user-${Date.now()}`, role: 'user', content: question };
    const conversation = [...expertMessages, userMessage];
    setExpertMessages(conversation);
    setExpertInput(''); setSuggestedUpdates(null); setChatBusy(true); setError('');
    let streamingAssistantId: string | null = null;
    try {
      const response = await fetch('/api/md-builder/chat-stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: question,
          history: expertMessages.slice(-10).map(item => ({ role: item.role, content: item.content })),
          parameters,
          locked_fields: [...lockedFields],
          structures: structures.map(item => item.inspection),
        }),
      });
      const contentType = response.headers?.get?.('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'MD Expert could not answer this question.');
        const updates = normalizeUpdates(data.parameter_updates);
        setExpertMessages(previous => [...previous, {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          confidence: data.confidence,
          checks: Array.isArray(data.diagnostic_checks) ? data.diagnostic_checks : [],
        }]);
        if (data.auto_apply) applyExpertUpdates(updates, false);
        else if (Object.keys(updates).length) setSuggestedUpdates(updates);
        return;
      }
      if (!response.ok || !response.body) throw new Error('MD Expert could not start streaming.');

      const assistantId = `assistant-${Date.now()}`;
      streamingAssistantId = assistantId;
      setExpertMessages(previous => [...previous, { id: assistantId, role: 'assistant', content: '' }]);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const event of events) {
          const raw = event.split('\n').find(line => line.startsWith('data: '))?.slice(6);
          if (!raw) continue;
          const data = JSON.parse(raw);
          if (data.type === 'error') throw new Error(data.error || 'MD Expert stream failed.');
          if (data.type === 'delta' && data.content) {
            setExpertMessages(previous => previous.map(item => item.id === assistantId
              ? { ...item, content: item.content + data.content }
              : item));
          }
          if (data.type === 'done') {
            setExpertMessages(previous => previous.map(item => item.id === assistantId
              ? { ...item, confidence: data.confidence || 'medium' }
              : item));
          }
        }
        if (done) break;
      }
    } catch (caught) {
      const errorContent = caught instanceof Error ? caught.message : 'MD Expert is unavailable.';
      setExpertMessages(previous => streamingAssistantId
        ? previous.map(item => item.id === streamingAssistantId ? { ...item, content: errorContent } : item)
        : [...previous, { id: `assistant-error-${Date.now()}`, role: 'assistant', content: errorContent }]);
    } finally { setChatBusy(false); }
  };

  const validationMessage = () => {
    if (!structures.length) return 'Add at least one structure.';
    if (structures.some(item => !item.inspection.valid)) return 'Remove unsupported structures before generation.';
    if (setup.system === 'single_protein' && (setup.pdbs.length !== 1 || setup.mol2s.length)) return 'Single protein requires one PDB file.';
    if (setup.system === 'protein_protein' && setup.pdbs.length < 1) return 'Protein-protein requires one complex or two PDB files.';
    if (setup.system === 'protein_ligand' && (setup.pdbs.length !== 1 || setup.mol2s.length !== 1)) return 'Protein-ligand requires one PDB and one MOL2 or SDF file.';
    if (setup.system === 'protein_ligand' && parameters.charge_method === 'existing' && !canUseExistingCharges) return 'No usable atomic charges were detected in the MOL2 file.';
    if (setup.inputMode === 'single_complex') {
      const p1 = Object.values(chainGroups).some(value => value === 'partner1');
      const p2 = Object.values(chainGroups).some(value => value === 'partner2');
      if (!p1 || !p2) return 'Assign at least one chain to each partner.';
    }
    return '';
  };

  const generate = async () => {
    const invalid = validationMessage();
    if (invalid) { setError(invalid); return; }
    setBusy('generate'); setError(''); setNotice('');
    const partner1 = Object.entries(chainGroups).filter(([, group]) => group === 'partner1').map(([chain]) => chain);
    const partner2 = Object.entries(chainGroups).filter(([, group]) => group === 'partner2').map(([chain]) => chain);
    const config = {
      ...parameters,
      system_type: setup.system,
      input_mode: setup.inputMode,
      structures: structures.map(({ source, filename, pdb_id, unit: sourceUnit, assembly_id }) => ({
        source, filename, pdb_id, unit: sourceUnit, assembly_id,
      })),
      partner1_chains: partner1,
      partner2_chains: partner2,
    };
    const form = new FormData();
    form.append('config', JSON.stringify(config));
    structures.forEach(item => { if (item.file) form.append('files', item.file, item.filename); });
    try {
      const response = await fetch('/api/md-builder/generate', { method: 'POST', body: form });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Project generation failed.');
      }
      const blob = await response.blob();
      setDownload({ url: URL.createObjectURL(blob), name: `${parameters.project_name}.zip` });
      setNotice('Your AMBER project is ready to download.');
      setTab('files');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Project generation failed.'); }
    finally { setBusy(null); }
  };

  const parameterPanel = (
    <div className="mdp-parameters">
      <div className="mdp-section-heading"><div><span>03</span><h2>Review parameters</h2></div><span className="mdp-lock-count">{lockedFields.size} edited</span></div>
      <label>Project name<input value={parameters.project_name} onChange={event => updateParameter('project_name', event.target.value)} /></label>
      <div className="mdp-field-grid">
        <label>Production (ns)<input type="number" min="0.1" value={parameters.simulation_time_ns} onChange={event => updateParameter('simulation_time_ns', Number(event.target.value))} /></label>
        <label>Temperature (K)<input type="number" value={parameters.temperature_k} onChange={event => updateParameter('temperature_k', Number(event.target.value))} /></label>
      </div>
      <label>Protocol preset<select value={parameters.preset} onChange={event => updateParameter('preset', event.target.value as Parameters['preset'])}><option value="standard">Standard · ff19SB + OPC</option><option value="compatibility">Compatibility · ff14SB + TIP3P</option></select></label>
      <label>Salt<select value={parameters.salt_molar} onChange={event => updateParameter('salt_molar', Number(event.target.value))}><option value={0}>Neutralize only</option><option value={0.15}>Approx. 0.15 M NaCl</option></select></label>
      {setup.system === 'protein_ligand' && <div className="mdp-ligand-fields">
        <label>Ligand charges<select value={parameters.charge_method} onChange={event => updateParameter('charge_method', event.target.value as Parameters['charge_method'])}><option value="am1bcc">AM1-BCC (recommended)</option><option value="resp">RESP · requires Gaussian</option><option value="existing" disabled={!canUseExistingCharges}>Use existing MOL2 charges{canUseExistingCharges ? '' : ' · not detected'}</option></select></label>
        <div className="mdp-field-grid"><label>Net charge<input type="number" value={parameters.ligand_net_charge} onChange={event => updateParameter('ligand_net_charge', Number(event.target.value))} /></label><label>Multiplicity<input type="number" min="1" value={parameters.ligand_multiplicity} onChange={event => updateParameter('ligand_multiplicity', Number(event.target.value))} /></label></div>
      </div>}
      <details className="mdp-advanced"><summary>Advanced settings <ChevronDown size={15} /></summary>
        <div className="mdp-field-grid">
          <label>Force field<select value={parameters.protein_force_field} onChange={event => updateParameter('protein_force_field', event.target.value as Parameters['protein_force_field'])}><option>ff19SB</option><option>ff14SB</option></select></label>
          <label>Water model<select value={parameters.water_model} onChange={event => updateParameter('water_model', event.target.value as Parameters['water_model'])}><option value="OPCBOX">OPC</option><option value="TIP3PBOX">TIP3P</option></select></label>
          <label>Padding (Å)<input type="number" value={parameters.solvent_padding_a} onChange={event => updateParameter('solvent_padding_a', Number(event.target.value))} /></label>
          <label>Cutoff (Å)<input type="number" value={parameters.cutoff_a} onChange={event => updateParameter('cutoff_a', Number(event.target.value))} /></label>
          <label>Timestep (fs)<input type="number" min="1" max="2" step="0.5" value={parameters.timestep_fs} onChange={event => updateParameter('timestep_fs', Number(event.target.value))} /></label>
          <label>Pressure (bar)<input type="number" value={parameters.pressure_bar} onChange={event => updateParameter('pressure_bar', Number(event.target.value))} /></label>
          <label>Heating (ps)<input type="number" value={parameters.heating_ps} onChange={event => updateParameter('heating_ps', Number(event.target.value))} /></label>
          <label>Equilibration (ps)<input type="number" value={parameters.equilibration_ps} onChange={event => updateParameter('equilibration_ps', Number(event.target.value))} /></label>
        </div>
        <label>Trajectory interval (ps)<input type="number" value={parameters.trajectory_interval_ps} onChange={event => updateParameter('trajectory_interval_ps', Number(event.target.value))} /></label>
      </details>
    </div>
  );

  return <div className="mdp-shell" aria-label="AMBER MD Builder">
    <nav className="mdp-mobile-tabs" aria-label="Builder views">{(['setup', 'files', 'expert', 'docking'] as Tab[]).map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</nav>
    {(error || notice) && <div className={`mdp-banner ${error ? 'error' : 'success'}`}>{error ? <AlertTriangle size={16} /> : <Check size={16} />}<span>{error || notice}</span><button onClick={() => { setError(''); setNotice(''); }}><X size={15} /></button></div>}
    {tab === 'docking' ? <div className="mdp-docking-inline"><Docking /></div> : <div className="mdp-workspace">
      <main className={`mdp-main overflow-y-auto ${tab !== 'setup' ? 'mdp-mobile-hidden' : ''}`} onWheel={scrollPanel}>
        <section className="mdp-section">
          <div className="mdp-section-heading"><div><span>01</span><h2>Select system</h2></div><span className="mdp-detected">Detected: {String(setup.system).replaceAll('_', ' ')}</span></div>
          <div className="mdp-segments">{([['single_protein', 'Single protein'], ['protein_protein', 'Protein-protein'], ['protein_ligand', 'Protein-ligand']] as [SystemChoice, string][]).map(([value, label]) => <button key={value} className={systemChoice === value ? 'active' : ''} onClick={() => setSystemChoice(value)}>{label}</button>)}</div>
        </section>

        <section className="mdp-section">
          <div className="mdp-section-heading"><div><span>02</span><h2>Provide structures</h2></div><span>{structures.length}/3 inputs</span></div>
          <div className="mdp-input-actions">
            {systemChoice === 'single_protein' && <>
              <button className="mdp-upload" onClick={() => fileInputRef.current?.click()} disabled={busy !== null}><Upload size={18} /><span><strong>Upload PDB</strong><small>Files stay in memory for this request only</small></span></button>
              <input ref={fileInputRef} type="file" multiple accept=".pdb,.ent" hidden onChange={event => inspectFiles(event.target.files)} />
            </>}
            {systemChoice === 'protein_protein' && <div className="mdp-upload-pair">
              <button className="mdp-upload" onClick={() => partner1InputRef.current?.click()} disabled={busy !== null}><Upload size={18} /><span><strong>Upload receptor protein</strong><small>PDB file</small></span></button>
              <input ref={partner1InputRef} type="file" accept=".pdb,.ent" hidden onChange={event => inspectFiles(event.target.files)} />
              <button className="mdp-upload" onClick={() => partner2InputRef.current?.click()} disabled={busy !== null}><Upload size={18} /><span><strong>Upload ligand protein</strong><small>PDB file</small></span></button>
              <input ref={partner2InputRef} type="file" accept=".pdb,.ent" hidden onChange={event => inspectFiles(event.target.files)} />
            </div>}
            {systemChoice === 'protein_ligand' && <div className="mdp-upload-pair">
              <button className="mdp-upload" onClick={() => partner1InputRef.current?.click()} disabled={busy !== null}><Upload size={18} /><span><strong>Upload receptor protein</strong><small>PDB file</small></span></button>
              <input ref={partner1InputRef} type="file" accept=".pdb,.ent" hidden onChange={event => inspectFiles(event.target.files)} />
              <button className="mdp-upload" onClick={() => ligandInputRef.current?.click()} disabled={busy !== null}><Upload size={18} /><span><strong>Upload ligand molecule</strong><small>MOL2 or SDF file</small></span></button>
              <input ref={ligandInputRef} type="file" accept=".mol2,.sdf" hidden onChange={event => inspectFiles(event.target.files)} />
            </div>}
          </div>
          <div className="mdp-structure-list">{structures.map((item, index) => <div className="mdp-structure-row" key={`${item.filename}-${index}`}><FileCode2 size={18} /><div><strong>{item.filename}</strong><span>{item.inspection.format.toUpperCase()} · {item.inspection.atoms.toLocaleString()} atoms · {item.inspection.chains.length || 1} {item.inspection.format === 'pdb' ? 'chains' : 'molecule'}</span>{item.inspection.warnings.map(warning => <small key={warning}>{warning}</small>)}</div><button title="Remove structure" onClick={() => setStructures(previous => previous.filter((_, row) => row !== index))}><X size={16} /></button></div>)}</div>
          <StructureViewer contents={viewerContents} />
          {complexChains.length > 1 && <div className="mdp-chain-table"><div className="mdp-chain-header"><span>Chain</span><span>Residues</span><span>Assignment</span></div>{complexChains.map(chain => <div className="mdp-chain-row" key={chain.id}><strong>{chain.id === '_' ? 'Blank' : chain.id}</strong><span>{chain.residues}</span><select aria-label={`Assign chain ${chain.id}`} value={chainGroups[chain.id] || 'excluded'} onChange={event => setChainGroups(previous => ({ ...previous, [chain.id]: event.target.value as ChainGroup }))}><option value="partner1">Partner 1</option><option value="partner2">Partner 2</option><option value="excluded">Excluded</option></select></div>)}</div>}
        </section>

        <section className="mdp-section mdp-parameter-section">{parameterPanel}</section>
      </main>

      <section className={`mdp-files-panel overflow-y-auto ${tab !== 'files' ? 'mdp-mobile-hidden' : ''}`} onWheel={scrollPanel}>
        <div className="mdp-section-heading"><div><span>04</span><h2>Generate & download</h2></div></div>
        <div className="mdp-protocol-summary"><strong>{parameters.preset === 'standard' ? 'Standard soluble-protein protocol' : 'Compatibility protocol'}</strong><span>{parameters.protein_force_field} · {parameters.water_model.replace('BOX', '')} · {parameters.simulation_time_ns} ns NPT</span></div>
        <div className="mdp-file-tree">{[...GENERATED_FILES, ...(setup.system === 'protein_ligand' && parameters.charge_method !== 'existing' ? ['prepare_lig.sh'] : [])].map(file => <div key={file}><FileCode2 size={14} />{file}</div>)}</div>
        {download ? <div className="mdp-file-actions">
          <a className="mdp-download" href={download.url} download={download.name}><Download size={17} /> Download {download.name}</a>
          <button className="mdp-regenerate" onClick={generate} disabled={busy !== null}>{busy === 'generate' ? <Loader2 className="mdp-spin" size={16} /> : <RefreshCw size={16} />} {busy === 'generate' ? 'Regenerating project' : 'Regenerate project'}</button>
        </div> : <div className="mdp-generate-ready"><div className="mdp-empty-files"><FileArchive size={28} /><p>Review the setup, then generate a downloadable AMBER project.</p></div><button className="mdp-generate" onClick={generate} disabled={busy !== null}>{busy === 'generate' ? <Loader2 className="mdp-spin" size={17} /> : <FileArchive size={17} />} Generate project</button></div>}
      </section>

      <aside className={`mdp-expert-panel ${tab !== 'expert' ? 'mdp-mobile-hidden' : ''}`}>
        <div className="mdp-expert-heading"><div><Bot size={18} /><div><h2>MD Expert</h2><span>DeepSeek</span></div></div><span className="mdp-expert-context">{structures.length} structures</span></div>
        <div className="mdp-expert-messages overflow-y-auto">
          {!expertMessages.length && <div className="mdp-expert-empty"><WandSparkles size={24} /><div className="mdp-quick-prompts">
            {['Set up 100 ns at 310 K with 0.15 M NaCl', 'My ligand left the binding site', 'How do I diagnose a SHAKE failure?', 'Why did the energy become NaN?'].map(item => <button key={item} onClick={() => setExpertInput(item)}>{item}</button>)}
          </div></div>}
          {expertMessages.map(message => <article key={message.id} className={`mdp-chat-message ${message.role}`}>
            <div className="mdp-chat-meta"><span>{message.role === 'user' ? 'You' : 'MD Expert'}</span>{message.confidence && <small>{message.confidence} confidence</small>}</div>
            <div className="mdp-chat-content"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>
            {!!message.checks?.length && <div className="mdp-diagnostic-checks"><strong>Check next</strong>{message.checks.map(item => <div key={item}><Check size={13} />{item}</div>)}</div>}
          </article>)}
          {chatBusy && <div className="mdp-expert-thinking"><Loader2 className="mdp-spin" size={16} /> Reviewing the setup and likely failure modes...</div>}
          <div ref={chatEndRef} />
        </div>
        {suggestedUpdates && <div className="mdp-suggested-updates"><div><strong>Suggested parameter changes</strong><span>{Object.entries(suggestedUpdates).map(([key, value]) => `${PARAMETER_LABELS[key as keyof Parameters] || key}: ${value}`).join(' · ')}</span></div><button onClick={() => applyExpertUpdates(suggestedUpdates, true)}>Apply changes</button></div>}
        <div className="mdp-expert-composer"><textarea aria-label="Ask MD Expert" value={expertInput} maxLength={12000} placeholder="Ask about setup, logs, instability, unbinding, or AMBER input files..." onChange={event => setExpertInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendExpertMessage(); } }} /><button aria-label="Send to MD Expert" title="Send message" onClick={() => void sendExpertMessage()} disabled={chatBusy || !expertInput.trim()}>{chatBusy ? <Loader2 className="mdp-spin" size={17} /> : <Send size={17} />}</button></div>
      </aside>
    </div>}
  </div>;
}
