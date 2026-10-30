# Registro de validação — 30/10/2026

Verificação local com Python 3.12.10, Node 24.20.0 e dependências fixadas em `requirements.lock` e `frontend/package-lock.json`. Dados usados são exclusivamente sintéticos, em diretórios temporários fora do repositório.

| Verificação | Resultado |
| --- | --- |
| `python -m pytest -q` | **45 passaram**. Inclui migrations reais e comparação do schema com os modelos, persistência após reabertura, fluxo completo, relatórios PT/EN, backup/restauração, exclusão, escopo e controles de IA. |
| `npm.cmd test` | **4 passaram**. Carregamento via API local, erro de validação de programa, confirmação de exclusão e bloqueio do envio de IA até aprovação da prévia. |
| `npm.cmd run build` | **Passou**: TypeScript e Vite geraram assets de produção. |
| `python -m pip check` | **Passou**, sem requisitos incompatíveis. |
| `python scripts/smoke.py` | **Passou** com HTTP real em loopback: HTML e JavaScript compilados, workspace sintético, laudo em inglês, PDF e backup. Servidor encerrado e dados temporários removidos ao fim. |
| Scripts PowerShell | **Sintaxe validada** nos três scripts. Instalação de dependências e build foram executados por seus comandos equivalentes. A ACL do diretório pessoal real não foi alterada durante a validação. |
| `git check-ignore` | Confirmou exclusão de `.env`, `.env.local`, banco, evidências, relatórios, backups, node_modules e ambiente virtual. |
| `docker compose config --quiet` | **Passou**. Porta publicada somente em `127.0.0.1`. |
| `docker compose build` | **Passou** para o código final, incluindo compilação frontend dentro da imagem. |
| Container Linux descartável | **Passou**, com `--network none`, usuário não root e sem volume pessoal: migrations, saúde, interface estática, criação de programa e backup. Container removido ao encerrar. |

Há um aviso de depreciação da versão instalada do Starlette para seu cliente de testes com `httpx`. Não afeta os resultados nem as chamadas em produção; migrar o cliente de testes quando atualizar esse conjunto de dependências.

Não foram usados serviços reais OpenAI/Ollama, chaves reais ou alvos de bounty. Os adaptadores foram verificados com transportes simulados, inclusive falhas, expiração, uso único e descarte de respostas sem as seções obrigatórias. HTTP externo real é bloqueado automaticamente na suíte Python.

Sem revisão visual em navegador real, teste com leitor de tela ou execução do pipeline GitHub Actions remoto nesta sessão. Os testes de interface usam jsdom. A configuração de CI inclui Windows e Linux, sem credenciais de provedores.
