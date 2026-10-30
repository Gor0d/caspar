import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

const workspace = { programs: [], assets: [], investigations: [], evidence: [], findings: [], journals: [], reports: [], analyses: [] };
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === 'POST') return { ok: false, status: 422, json: async () => ({ detail: 'Registre a autorização.' }) };
    return { ok: true, status: 200, json: async () => url.endsWith('workspace') ? workspace : {storage: '/private/caspar'} };
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('Personal workspace', () => {
  it('loads real records via the local header and shows empty dashboard', async () => {
    render(<App/>);
    await screen.findByText('Seu próximo projeto começa por um programa.');
    expect(fetch).toHaveBeenCalledWith('/api/workspace', expect.objectContaining({ headers: {'X-Caspar-Local': '1'} }));
    expect(screen.getByText('SCOPE GUARD ATIVO')).toBeInTheDocument();
  });
  it('opens program creation and displays API validation without closing the dialog', async () => {
    render(<App/>);
    await screen.findByText('Seu próximo projeto começa por um programa.');
    fireEvent.click(screen.getByRole('button', {name: /Novo programa/}));
    fireEvent.change(screen.getByLabelText('Nome do programa'), {target: {value: 'Synthetic Lab'}});
    fireEvent.click(screen.getByRole('button', {name: 'Salvar programa'}));
    await waitFor(() => expect(screen.getAllByRole('alert')[0]).toHaveTextContent('Registre a autorização.'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/programs', expect.objectContaining({method: 'POST', body: expect.stringContaining('Synthetic Lab')}));
  });
  it('exposes privacy controls and requires typed deletion confirmation', async () => {
    render(<App/>);
    await screen.findByText('Seu próximo projeto começa por um programa.');
    fireEvent.click(screen.getByRole('button', {name: 'Dados e privacidade'}));
    expect(screen.getByText('/private/caspar')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: 'Excluir dados'}));
    expect(screen.getByLabelText('Digite EXCLUIR para confirmar')).toHaveAttribute('pattern', 'EXCLUIR');
  });
  it('keeps AI transmission disabled until the exact preview is approved', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => ({ok: true, status: 200, json: async () => {
      if (url.endsWith('workspace')) return {...workspace,
        programs: [{id: 'p1', name: 'Synthetic', authorized: true}],
        investigations: [{id: 'i1', program_id: 'p1', title: 'Offline fixture', target: 'api.example.test'}],
        evidence: [{id: 'e1', investigation_id: 'i1', filename: 'fixture.txt', size: 100, sha256: 'f'.repeat(64), provenance: 'Synthetic', created_at: '2026-10-30T12:00:00Z'}]
      };
      if (url.endsWith('/preview')) return {consent_id: 'c1', digest: 'digest', provider: 'openai', model: 'test', payload: 'UNTRUSTED fixture only', instructions: 'No tools', warning: 'Review first', approximate_input_tokens: 20, estimated_max_cost_usd: 0};
      return {storage: '/private/caspar', openai_configured: true, openai_model: 'test'};
    }})));
    render(<App/>);
    await screen.findByText('Offline fixture');
    fireEvent.click(screen.getByRole('button', {name: 'Evidências'}));
    fireEvent.change(screen.getByLabelText('Investigação'), {target: {value: 'i1'}});
    fireEvent.click(screen.getByRole('button', {name: 'Analisar com IA'}));
    fireEvent.change(screen.getByLabelText('Provedor e modelo'), {target: {value: 'openai'}});
    fireEvent.change(screen.getByLabelText('Pergunta sobre o material'), {target: {value: 'Summarize fixture'}});
    fireEvent.click(screen.getByLabelText('fixture.txt'));
    fireEvent.click(screen.getByRole('button', {name: 'Preparar prévia local'}));
    const send = await screen.findByRole('button', {name: 'Aprovar e analisar'});
    expect(send).toBeDisabled();
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining('/analyze'), expect.anything());
    fireEvent.click(screen.getByLabelText(/Revisei o conteúdo/));
    expect(send).toBeEnabled();
    expect(screen.getByText('UNTRUSTED fixture only')).toBeInTheDocument();
  });
});
