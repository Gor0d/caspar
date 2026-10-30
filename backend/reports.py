from io import BytesIO
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

LABELS = {
    'pt': ['Laudo técnico', 'Programa', 'Ativo', 'Condições de autorização', 'Hipótese', 'Evidências verificadas pelo pesquisador', 'Conclusão do pesquisador', 'Passos registrados', 'Impacto declarado', 'Recomendação', 'Manifesto de evidências', 'Não informado', 'Diário de pesquisa'],
    'en': ['Technical report', 'Program', 'Asset', 'Authorization conditions', 'Hypothesis', 'Evidence verified by the researcher', 'Researcher conclusion', 'Recorded steps', 'Declared impact', 'Remediation', 'Evidence manifest', 'Not provided', 'Research journal'],
}


def markdown_text(value):
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', escape(value))


def quote(value):
    # Keep imported content inert even in Markdown readers: HTML escaped + blockquoted.
    return '\n'.join('> ' + markdown_text(line) for line in (value or '').splitlines()) or '> —'


def render(program, investigation, findings, evidence, journals, language, plans=(), runs=()):
    labels = LABELS[language]
    lines = [f'# CASPAR — {labels[0]}', '', quote(investigation.title), '',
             f'**{labels[1]}:**', quote(program.name), f'**{labels[2]}:**', quote(investigation.target),
             f'## {labels[3]}', quote(program.authorization), quote(program.policy), '',
             '> ' + ('Documento baseado em registros locais. IA não valida fatos. Revisão humana obrigatória.' if language == 'pt' else 'Based on local records. AI does not validate facts. Human review required.')]
    for finding in findings:
        lines += ['', '## ' + markdown_text(finding.title), f'ID: {finding.id}', f'{finding.severity.upper()} · {finding.cwe or "—"} · {markdown_text(finding.owasp)}', f'Status: {finding.status}']
        for index, field in enumerate(['hypothesis', 'verified', 'conclusion', 'steps', 'impact', 'remediation'], 4):
            lines += [f'### {labels[index]}', quote(getattr(finding, field) or labels[11])]
        lines += ['Evidence IDs: ' + ', '.join(finding.evidence_ids)]
        linked_runs = [run.id for run in runs if run.finding_id == finding.id]
        if linked_runs:
            lines += [('Execuções relacionadas: ' if language == 'pt' else 'Related test runs: ') + ', '.join(linked_runs)]
    testing_labels = {
        'pt': ['Planos de testes manuais', 'Histórico de execuções manuais', 'Objetivo', 'Técnica', 'Pré-condições', 'Passos planejados', 'Resultado esperado', 'Condições de interrupção', 'Resultado observado', 'Limitações', 'Revisão humana', 'Ainda não revisado', 'Comportamento esperado', 'Possível problema observado', 'Inconclusivo'],
        'en': ['Manual test plans', 'Manual execution history', 'Objective', 'Technique', 'Preconditions', 'Planned steps', 'Expected result', 'Stop conditions', 'Observed result', 'Limitations', 'Human review', 'Not yet reviewed', 'Expected behavior', 'Potential issue observed', 'Inconclusive'],
    }[language]
    fields = ('objective', 'technique', 'preconditions', 'steps', 'expected_result', 'stop_conditions')
    if plans:
        lines += [f'## {testing_labels[0]}']
        for plan in plans:
            lines += ['### ' + markdown_text(plan.title), f'ID: {plan.id} / revision: {plan.revision} / status: {plan.status}']
            for index, field in enumerate(fields, 2):
                lines += [f'**{testing_labels[index]}**', quote(getattr(plan, field))]
    if runs:
        lines += [f'## {testing_labels[1]}', quote('Registros declarados pelo pesquisador; o CASPAR não executou estes testes.' if language == 'pt' else 'Researcher-declared records; CASPAR did not execute these tests.')]
        outcomes = dict(zip(('expected_behavior', 'observed_issue', 'inconclusive'), testing_labels[12:15]))
        for run in runs:
            snapshot = run.plan_snapshot
            lines += ['### ' + markdown_text(snapshot['title']), f'ID: {run.id} / plan: {run.test_plan_id} / revision: {snapshot["revision"]}',
                      run.performed_at, outcomes[run.outcome], quote(snapshot['scope']['target']),
                      quote(snapshot['scope']['authorization']), 'Approval: ' + snapshot['approved_at']]
            for index, field in enumerate(fields, 2):
                lines += [f'**{testing_labels[index]}**', quote(snapshot[field])]
            lines += [f'**{testing_labels[8]}**', quote(run.observed_result), f'**{testing_labels[9]}**', quote(run.limitations),
                      'Evidence IDs: ' + ', '.join(run.evidence_ids)]
            for evidence_id, digest in snapshot['evidence_manifest'].items():
                lines += [f'{evidence_id}: SHA-256 {digest}']
            lines += [f'**{testing_labels[10]}**', quote(run.review_notes if run.reviewed_at else testing_labels[11])]
            if run.finding_id:
                lines += ['Finding ID: ' + run.finding_id]
    lines += ['', f'## {labels[10]}']
    for record in evidence:
        lines += [f'- ID: {record.id}', quote(record.filename), f'  SHA-256: {record.sha256}', f'  Bytes: {record.size}', quote(record.provenance)]
    lines += ['', f'## {labels[12]}']
    for journal in journals:
        lines += [journal.created_at, quote(journal.body)]
    return '\n\n'.join(lines)


def pdf(markdown):
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 14
    styles['BodyText'].wordWrap = 'CJK'
    story = []
    for line in markdown.splitlines():
        if not line.strip():
            story.append(Spacer(1, 5))
            continue
        style = styles['Heading1' if line.startswith('# ') else 'Heading2' if line.startswith('## ') else 'Heading3' if line.startswith('### ') else 'BodyText']
        text = re.sub(r'\\([\\`*_{}\[\]()#+.!|>~-])', r'\1', line.lstrip('#> ').replace('**', ''))
        # Never interpret imported HTML, URLs, images or PDF markup.
        story.append(Paragraph(escape(text), style))
    SimpleDocTemplate(output, title='CASPAR Technical Report', author='CASPAR', pageCompression=1).build(story)
    return output.getvalue()
