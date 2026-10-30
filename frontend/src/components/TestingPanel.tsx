import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Check, ClipboardList, FileCheck2, Plus, RotateCcw, ShieldCheck, X } from 'lucide-react';
import { Button } from './ui/button';
import { api } from '../api';
import type { Investigation, TestPlan, TestRun, Workspace } from '../types';

export const planStatuses: Record<string, string> = {planned: 'Planejado', approved: 'Aprovado', executed: 'Registrado', inconclusive: 'Inconclusivo', reviewed: 'Revisado'};
export const outcomes: Record<string, string> = {expected_behavior: 'Comportamento esperado', observed_issue: 'Possível problema observado', inconclusive: 'Inconclusivo'};
const fields = [['title', 'Título do plano', 200], ['objective', 'Objetivo do teste', 10000], ['technique', 'Técnica permitida', 200], ['preconditions', 'Pré-condições', 10000], ['steps', 'Passos planejados', 20000], ['expected_result', 'Resultado esperado', 10000], ['stop_conditions', 'Condições de interrupção', 10000]] as const;
const date = (value: string) => new Date(value).toLocaleString('pt-BR');
const localTime = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
function Field({label, children}: {label: string; children: ReactNode}) { return <label className="field"><span>{label}</span>{children}</label>; }

type Props = {data: Workspace; investigation?: Investigation; investigationIds: string[]; query: string; refresh: () => Promise<void>};
type Modal = 'plan' | 'approve' | 'run' | 'review' | null;
type ApprovalPreview = {context_digest: string; scope: {target: string; authorization: string; policy: string; assets: {id: string; pattern: string; allowed: boolean; note: string}[]}};

export default function TestingPanel({data, investigation, investigationIds, query, refresh}: Props) {
  const [modal, setModal] = useState<Modal>(null);
  const [plan, setPlan] = useState<TestPlan>();
  const [run, setRun] = useState<TestRun>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [approved, setApproved] = useState(false);
  const [outcome, setOutcome] = useState('inconclusive');
  const [approvalPreview, setApprovalPreview] = useState<ApprovalPreview>();
  useEffect(() => {
    if (modal !== 'approve' || !plan) return;
    let cancelled = false;
    setApprovalPreview(undefined);
    api<ApprovalPreview>('/test-plans/' + plan.id + '/approval-preview?expected_revision=' + plan.revision)
      .then(value => {if (!cancelled) setApprovalPreview(value);})
      .catch(e => {if (!cancelled) setError(e.message);});
    return () => {cancelled = true;};
  }, [modal, plan?.id, plan?.revision]);
  useEffect(() => {setModal(null); setPlan(undefined); setRun(undefined); setError(''); setNotice('');}, [investigation?.id]);
  const visible = data.test_plans.filter(p => (investigation ? p.investigation_id === investigation.id : investigationIds.includes(p.investigation_id)) && (p.title + p.technique).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const currentInvestigation = data.investigations.find(i => i.id === plan?.investigation_id) || investigation;
  const evidence = data.evidence.filter(e => e.investigation_id === currentInvestigation?.id);
  const findings = data.findings.filter(f => f.investigation_id === run?.investigation_id);

  function open(next: Modal, selected?: TestPlan, selectedRun?: TestRun) {
    setPlan(selected); setRun(selectedRun); setModal(next); setApproved(false); setApprovalPreview(undefined); setOutcome('inconclusive'); setError('');
  }
  async function perform(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setNotice('');
    try {await action(); await refresh(); setNotice(message); setModal(null);}
    catch (e) {setError(e instanceof Error ? e.message : 'Não foi possível salvar.');}
    finally {setBusy(false);}
  }
  function form(event: FormEvent<HTMLFormElement>) {event.preventDefault(); return new FormData(event.currentTarget);}
  const str = (values: FormData, key: string) => String(values.get(key) || '');
  function submitPlan(event: FormEvent<HTMLFormElement>) {
    const values = form(event);
    const body = Object.fromEntries(fields.map(([key]) => [key, str(values, key)]));
    void perform(() => api(plan ? '/test-plans/' + plan.id : '/investigations/' + investigation!.id + '/test-plans', plan ? 'PUT' : 'POST', {...body, ...(plan ? {expected_revision: plan.revision} : {})}), plan ? 'Nova versão salva. Revise e aprove o plano novamente.' : 'Plano criado. Revise antes de aprovar.');
  }
  function submitRun(event: FormEvent<HTMLFormElement>) {
    const values = form(event);
    void perform(() => api('/test-plans/' + plan!.id + '/runs', 'POST', {
      expected_revision: plan!.revision, performed_at: new Date(str(values, 'performed_at')).toISOString(), outcome,
      observed_result: str(values, 'observed_result'), limitations: str(values, 'limitations'), evidence_ids: values.getAll('evidence_ids'),
    }), 'Execução manual registrada. Revise o resultado antes de relacioná-lo a um achado.');
  }
  return <section className="panel testing-panel">
    <div className="panel-heading"><div><h2><ClipboardList size={18}/> Planos e execuções manuais</h2><p>Planeje, registre o que você executou e preserve cada reteste.</p></div><Button disabled={!investigation || busy} onClick={() => open('plan')}><Plus size={14}/> Novo plano</Button></div>
    {error && !modal && <div role="alert" className="message error testing-message">{error}</div>}
    {notice && <div role="status" className="message success testing-message"><Check size={15}/>{notice}</div>}
    <div className="testing-intro"><ShieldCheck size={18}/><p>O CASPAR registra testes realizados por você em ambiente autorizado. Aprovar um plano não envia requisições nem executa comandos.</p></div>
    {!visible.length && <div className="empty"><ClipboardList size={25}/><p>{investigation ? 'Crie um plano com objetivo, resultado esperado e condições de interrupção.' : 'Selecione uma investigação para planejar e registrar seus testes.'}</p></div>}
    {visible.map(item => {
      const runs = data.test_runs.filter(r => r.test_plan_id === item.id);
      return <article className="test-plan" key={item.id}>
        <div className="test-plan-heading"><div><h3>{item.title}</h3><small>{item.technique} · v{item.revision} · {data.investigations.find(i => i.id === item.investigation_id)?.target}</small></div><span className={'badge ' + (item.status === 'approved' || item.status === 'reviewed' ? 'green' : '')}>{planStatuses[item.status]}</span></div>
        <p className="preserve">{item.objective}</p>
        <details className="test-spec"><summary>Ver plano completo e condições</summary><div>{fields.slice(2).map(([key, label]) => <div key={key}><h4>{label}</h4><p className="preserve">{item[key] || 'Não informado'}</p></div>)}</div></details>
        <div className="toolbar"><Button variant="outline" disabled={busy} onClick={() => open('plan', item)}>Editar plano</Button><Button variant="outline" disabled={busy} onClick={() => open('approve', item)}>{runs.length ? <RotateCcw size={14}/> : <ShieldCheck size={14}/>}{runs.length ? 'Aprovar reteste' : 'Revisar e aprovar'}</Button><Button disabled={busy || item.status !== 'approved'} onClick={() => open('run', item)}><Plus size={14}/> Registrar execução manual</Button></div>
        {!!runs.length && <div className="test-history"><h4>Histórico · {runs.length} registro(s)</h4>{[...runs].reverse().map(record => <details className="test-run" key={record.id}><summary><FileCheck2 size={16}/><strong>{outcomes[record.outcome]}</strong><span>v{record.plan_snapshot.revision} · {date(record.performed_at)}</span><span className="badge">{record.reviewed_at ? 'Revisado' : 'A revisar'}</span></summary><div className="test-run-body"><h4>Resultado observado</h4><p className="preserve">{record.observed_result}</p><h4>Limitações</h4><p className="preserve">{record.limitations || 'Não informadas'}</p><h4>Evidências preservadas</h4>{record.evidence_ids.map(id => <p className="mono preserve" key={id}>{data.evidence.find(e => e.id === id)?.filename || id}<small>SHA-256: {record.plan_snapshot.evidence_manifest[id]}</small></p>)}<details className="test-spec"><summary>Plano e autorização usados neste registro</summary><div><p className="preserve">{record.plan_snapshot.scope.target}</p><p className="preserve">{record.plan_snapshot.scope.authorization}</p><small>Aprovação registrada: {date(record.plan_snapshot.approved_at)}</small>{fields.map(([key, label]) => <div key={key}><h4>{label}</h4><p className="preserve">{record.plan_snapshot[key] || 'Não informado'}</p></div>)}</div></details>{record.reviewed_at ? <><h4>Revisão humana · {date(record.reviewed_at)}</h4><p className="preserve">{record.review_notes}</p><small>Achado: {data.findings.find(f => f.id === record.finding_id)?.title || 'Sem vínculo — resultado também pode ser negativo ou inconclusivo.'}</small></> : <Button variant="outline" onClick={() => open('review', item, record)}>Revisar e vincular achado</Button>}</div></details>)}</div>}
      </article>;
    })}
    <Dialog.Root open={!!modal} onOpenChange={value => {if (!value && !busy) setModal(null);}}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="dialog-content dialog-wide" aria-describedby="testing-dialog-description"><div className="dialog-heading"><Dialog.Title>{modal === 'plan' ? plan ? 'Editar plano de teste' : 'Novo plano de teste' : modal === 'approve' ? 'Revisar e aprovar plano' : modal === 'run' ? 'Registrar execução manual' : 'Revisão humana do resultado'}</Dialog.Title><Dialog.Close asChild><Button variant="ghost" disabled={busy} aria-label="Fechar janela de testes"><X size={18}/></Button></Dialog.Close></div><Dialog.Description id="testing-dialog-description">Somente registros locais. Nenhum teste será executado pelo CASPAR.</Dialog.Description>
    {error && <div role="alert" className="message error">{error}</div>}
    {modal === 'plan' && <form onSubmit={submitPlan}>{fields.map(([key, label, maxLength]) => <Field key={key} label={label}>{key === 'title' || key === 'technique' ? <input name={key} maxLength={maxLength} required defaultValue={plan?.[key]}/> : <textarea name={key} maxLength={maxLength} required={key !== 'preconditions'} rows={3} defaultValue={plan?.[key]}/>}</Field>)}<p className="muted">Salvar alterações cria uma nova versão e invalida a aprovação atual. Registros anteriores preservam o plano usado na época.</p><Button disabled={busy} type="submit">Salvar plano</Button></form>}
    {modal === 'approve' && plan && <div>
      <h3>{plan.title} · v{plan.revision}</h3>
      <div className="approval-context"><h4>Ativo e autorização atuais</h4>
        <p>{approvalPreview?.scope.target || 'Carregando contexto atual…'}</p>
        <p className="preserve">{approvalPreview?.scope.authorization}</p>
        <p className="preserve muted">{approvalPreview?.scope.policy}</p>
        {approvalPreview?.scope.assets.map(asset => <p className="mono preserve" key={asset.id}>{asset.allowed ? 'Permitido' : 'Proibido'}: {asset.pattern} {asset.note && '· ' + asset.note}</p>)}
      </div>
      {fields.slice(1).map(([key, label]) => <div className="approval-field" key={key}><h4>{label}</h4><p className="preserve">{plan[key] || 'Não informado'}</p></div>)}
      <label className="checkbox approval"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)}/> Revisei esta versão, a autorização e as condições de interrupção. Aprovo o plano para um registro de execução manual.</label>
      <p className="muted">Aprovação válida por 24 horas e para um único registro. Alterar política, escopo ou plano exige nova aprovação. O CASPAR não verifica a legitimidade da autorização.</p>
      <Button disabled={!approved || !approvalPreview || busy} onClick={() => void perform(() => api('/test-plans/' + plan.id + '/approve', 'POST', {approved: true, expected_revision: plan.revision, context_digest: approvalPreview!.context_digest}), 'Plano aprovado para um registro manual. Nenhuma conexão foi iniciada.')}>Aprovar versão {plan.revision}</Button>
    </div>}
    {modal === 'run' && <form onSubmit={submitRun}><h3>{plan?.title} · v{plan?.revision}</h3><Field label="Quando você realizou o teste (horário local)"><input name="performed_at" type="datetime-local" required defaultValue={localTime()}/></Field><Field label="Resultado observado"><select value={outcome} onChange={e => setOutcome(e.target.value)}>{Object.entries(outcomes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="Descreva o que aconteceu"><textarea name="observed_result" required rows={4} maxLength={20000}/></Field><Field label="Limitações e motivo se inconclusivo"><textarea name="limitations" required={outcome === 'inconclusive'} rows={3} maxLength={10000}/></Field><fieldset><legend>Evidências locais da execução (selecione ao menos uma)</legend>{evidence.map(item => <label className="checkbox" key={item.id}><input type="checkbox" name="evidence_ids" value={item.id}/>{item.filename}</label>)}{!evidence.length && <p>Importe primeiro as evidências desta investigação na tela Evidências.</p>}</fieldset><p className="muted">O registro preserva o plano e os hashes das evidências. Um possível problema observado ainda precisa de revisão humana; não equivale a vulnerabilidade confirmada.</p><Button disabled={busy || !evidence.length} type="submit">Salvar execução manual</Button></form>}
    {modal === 'review' && run && <form onSubmit={e => {const values = form(e); void perform(() => api('/test-runs/' + run.id + '/review', 'POST', {reviewed: true, review_notes: str(values, 'review_notes'), finding_id: str(values, 'finding_id') || null}), 'Revisão registrada. O histórico original foi preservado.');}}><h3>{outcomes[run.outcome]}</h3><p className="preserve">{run.observed_result}</p><Field label="Revisão e conclusão humana"><textarea name="review_notes" required rows={4} maxLength={10000}/></Field><Field label="Achado relacionado (opcional)"><select name="finding_id"><option value="">Sem vínculo</option>{findings.map(f => <option key={f.id} value={f.id}>{f.title}</option>)}</select></Field><p className="muted">Após salvar, esta revisão será preservada. Novas observações devem entrar em outro registro de teste ou reteste.</p><Button type="submit" disabled={busy}>Salvar revisão</Button></form>}
    {busy && <p role="status" className="busy-indicator">Salvando registro local…</p>}
    </Dialog.Content></Dialog.Portal></Dialog.Root>
  </section>;
}
