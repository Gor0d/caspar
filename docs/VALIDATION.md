# Registro de validação — 30/10/2026

## Versão 0.2 — planejamento e execuções manuais

- **63 testes Python passaram**, incluindo os 45 anteriores e 18 casos novos: migração de banco `0001` com preservação de dados, planos versionados, aprovação explícita de uso único, invalidação por edição/política/escopo (inclusive mudanças entre a prévia e a aprovação), expiração, integridade e vínculo das evidências, revisão imutável, retestes, snapshots, persistência após reabertura e relatórios PT/EN. O aviso de depreciação do cliente Starlette/httpx permanece.
- **9 testes de interface passaram**: os 4 anteriores e 5 novos para contexto de investigação, cadastro de plano, aprovação explícita, erro de versão sem perda imediata do formulário e registro manual com evidência selecionada.
- **Build TypeScript/Vite passou**, incluindo a compilação dos novos testes e do módulo de interface.
- **Smoke HTTP real passou** em servidor temporário no loopback: HTML/JavaScript, workspace sintético, criação/aprovação de plano, registro manual, revisão vinculada a achado, relatório em inglês, PDF e backup. Nenhum alvo ou modelo externo foi acessado.
- O servidor temporário foi encerrado e os arquivos sintéticos removidos. Nenhum acervo pessoal foi migrado durante a validação.
- **Docker build passou** e os mesmos **63 testes Python passaram no Linux**, em container descartável sem rede, como usuário sem privilégios e com apenas os testes do host montados como leitura. O container foi removido ao terminar.

Os resultados abaixo documentam a validação inicial da versão 0.1. A inspeção visual em navegador real e a validação prática pelo proprietário continuam pendentes.

## Versão 0.1 — base pessoal

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
