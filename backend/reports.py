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


def render(program, investigation, findings, evidence, journals, language):
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
