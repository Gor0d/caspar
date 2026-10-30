# CASPAR — primeira versão pessoal

1. Persistir programas, escopo, investigações, diário, evidências, achados e submissões em SQLite com Alembic.
2. Proteger armazenamento fora do Git, validar referências e bloquear escopo desconhecido ou proibido. Nenhum mecanismo de varredura.
3. Entregar interface local React com navegação pelo fluxo completo e estados de erro/carregamento.
4. Gerar relatórios determinísticos PT/EN em Markdown e PDF; backup consistente e exclusão com confirmação.
5. Oferecer adaptadores opcionais de IA, prévia redigida, consentimento descartável e resultados separados dos fatos.
6. Testar fluxo persistido, migrations e limites de segurança; documentar instalação, recuperação e limitações.

Fora desta etapa: SaaS, autenticação remota, equipes, cobrança, exploração, crawlers e execução de comandos importados.

## Direção após o MVP

O objetivo do produto também inclui testes de segurança e pentest para bug bounty, em ambientes próprios ou expressamente autorizados. A restrição de análise de material importado descreve o MVP entregue, não o limite definitivo do produto. A evolução mantém ausência de ações automáticas sobre alvos e exige execução deliberada pelo proprietário.

Próxima etapa: [workspace de testes web/API e validação de achados](PENTEST_ROADMAP.md). Este planejamento não habilita tráfego ou execução ativa na versão atual.
