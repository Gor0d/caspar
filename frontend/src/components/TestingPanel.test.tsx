import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import TestingPanel from './TestingPanel';
import type { TestPlan, Workspace } from '../types';

const investigation = {id: 'i1', program_id: 'p1', title: 'Synthetic lab', target: 'api.example.test', created_at: '2026-10-30T12:00:00Z'};
const plan: TestPlan = {id: 'plan1', investigation_id: 'i1', created_at: '2026-10-30T12:00:00Z', revision: 1, status: 'planned', approved_revision: 0, approved_at: '', approval_context: '', title: 'Check fixture', objective: 'Compare access behavior', technique: 'Offline fixture comparison', preconditions: 'Owned synthetic lab', steps: 'Review supplied response', expected_result: '403', stop_conditions: 'Stop if real user data appears'};
const data: Workspace = {programs: [{id: 'p1', name: 'Synthetic program', authorized: true, authorization: 'Owned offline lab', policy: 'Synthetic data only', created_at: '2026-10-30T12:00:00Z'}], assets: [], investigations: [investigation], test_plans: [plan], test_runs: [], evidence: [], findings: [], journals: [], reports: [], analyses: []};
const refresh = vi.fn(async () => {});

beforeEach(() => {refresh.mockClear(); vi.stubGlobal('fetch', vi.fn(async (url: string) => ({ok: true, status: 200, json: async () => url.includes('approval-preview') ? {context_digest: 'f'.repeat(64), scope: {target: 'api.example.test', authorization: 'Owned offline lab', policy: 'Synthetic data only', assets: []}} : {}})));});
afterEach(() => {cleanup(); vi.unstubAllGlobals();});

describe('Manual testing workspace', () => {
  it('requires investigation context for creating a plan', () => {
    render(<TestingPanel data={{...data, test_plans: []}} investigationIds={['i1']} query="" refresh={refresh}/>);
    expect(screen.getByRole('button', {name: 'Novo plano'})).toBeDisabled();
    expect(screen.getByText('Selecione uma investigação para planejar e registrar seus testes.')).toBeInTheDocument();
  });
  it('saves a real plan through the API without approving or executing it', async () => {
    render(<TestingPanel data={{...data, test_plans: []}} investigation={investigation} investigationIds={['i1']} query="" refresh={refresh}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Novo plano'}));
    for (const [label, value] of [['Título do plano', 'Fixture review'], ['Objetivo do teste', 'Compare fixture'], ['Técnica permitida', 'Offline review'], ['Passos planejados', 'Read fixture'], ['Resultado esperado', '403'], ['Condições de interrupção', 'Unexpected private data']]) {
      fireEvent.change(screen.getByLabelText(label), {target: {value}});
    }
    fireEvent.click(screen.getByRole('button', {name: 'Salvar plano'}));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetch).toHaveBeenCalledWith('/api/investigations/i1/test-plans', expect.objectContaining({method: 'POST', body: expect.stringContaining('Fixture review')}));
    expect(fetch).toHaveBeenCalledOnce();
  });
  it('requires explicit approval of the exact plan revision', async () => {
    render(<TestingPanel data={data} investigation={investigation} investigationIds={['i1']} query="" refresh={refresh}/>);
    expect(screen.getByRole('button', {name: 'Registrar execução manual'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button', {name: 'Revisar e aprovar'}));
    const button = screen.getByRole('button', {name: 'Aprovar versão 1'});
    expect(button).toBeDisabled();
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining('/approve'), expect.objectContaining({method: 'POST'}));
    expect(await screen.findByText('Owned offline lab')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Revisei esta versão/));
    fireEvent.click(button);
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetch).toHaveBeenCalledWith('/api/test-plans/plan1/approve', expect.objectContaining({body: JSON.stringify({approved: true, expected_revision: 1, context_digest: 'f'.repeat(64)})}));
  });
  it('preserves form inputs and displays stale revision errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ok: false, status: 409, json: async () => ({detail: 'Plano alterado. Recarregue.'})})));
    render(<TestingPanel data={data} investigation={investigation} investigationIds={['i1']} query="" refresh={refresh}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Editar plano'}));
    fireEvent.change(screen.getByLabelText('Objetivo do teste'), {target: {value: 'Updated objective'}});
    fireEvent.click(screen.getByRole('button', {name: 'Salvar plano'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Plano alterado. Recarregue.');
    expect(screen.getByLabelText('Objetivo do teste')).toHaveValue('Updated objective');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });
  it('records a manual result with selected evidence rather than starting a network test', async () => {
    const evidence = {id: 'e1', investigation_id: 'i1', filename: 'fixture.txt', storage_name: 'f'.repeat(32) + '.bin', size: 10, sha256: 'f'.repeat(64), provenance: 'Synthetic', created_at: '2026-10-30T12:00:00Z'};
    render(<TestingPanel data={{...data, evidence: [evidence], test_plans: [{...plan, status: 'approved'}]}} investigation={investigation} investigationIds={['i1']} query="" refresh={refresh}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Registrar execução manual'}));
    fireEvent.change(screen.getByLabelText('Resultado observado'), {target: {value: 'expected_behavior'}});
    fireEvent.change(screen.getByLabelText('Descreva o que aconteceu'), {target: {value: '403 in synthetic fixture'}});
    fireEvent.click(screen.getByLabelText('fixture.txt'));
    fireEvent.click(screen.getByRole('button', {name: 'Salvar execução manual'}));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[0]).toBe('/api/test-plans/plan1/runs');
    expect(JSON.parse(String(call[1]?.body))).toMatchObject({evidence_ids: ['e1'], outcome: 'expected_behavior', expected_revision: 1});
    expect(fetch).toHaveBeenCalledOnce();
  });
});
