# CASPAR — Personal Research Edition

Ferramenta pessoal para organizar pesquisa responsável de bug bounty e material previamente coletado. O fluxo é **Programa → Investigação → Evidência → Achado → Relatório**. A versão 0.1.0 tem frontend React/TypeScript e API FastAPI com SQLite, migrations Alembic e armazenamento local fora do Git.

Não existem varreduras, exploração, requisições a alvos, agentes autônomos, SaaS, equipes ou cobrança. O único tráfego de pesquisa permitido pela aplicação é uma análise opcional de texto por IA, após revisão e aprovação por envio.

## Requisitos

- Python 3.12 e Node.js 22 ou 24 com npm.
- Acesso à internet para a instalação das dependências. Depois de instalado, o fluxo principal funciona sem internet.
- Uma conta pessoal do sistema operacional com permissão para criar `~/.caspar`.

## Instalação e execução no Windows

Na raiz do projeto, no PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Start.ps1
```

O primeiro script cria o ambiente Python, instala dependências, compila o frontend, aplica migrations e restringe a ACL da pasta de dados ao usuário atual e SYSTEM. `Bypass` vale somente para o processo do script; não altera a política global. O segundo inicia um único servidor em **http://127.0.0.1:8000**. Encerre com Ctrl+C.

Instalação manual equivalente, se preferir:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe -m backend.cli init
powershell -ExecutionPolicy Bypass -File .\scripts\Protect-Data.ps1
.\.venv\Scripts\python.exe -m backend.cli serve
```

Não é necessário ativar o ambiente virtual. `npm.cmd` evita o bloqueio de `npm.ps1` em instalações Windows com política restrita.

## Linux / macOS

```sh
sh scripts/setup.sh
sh scripts/start.sh
```

Diretórios de dados usam modo `0700`; banco e arquivos de evidência usam `0600`. No Windows, execute `Protect-Data.ps1` também após mudar o diretório ou restaurar um backup.

## Primeiro uso

1. Cadastre um programa. Registre política, referência, data, condições e validade da autorização; confirme expressamente a autorização.
2. Adicione hosts permitidos e proibidos. Sem regra permitida, o host fica bloqueado. Proibições sempre prevalecem.
3. Crie uma investigação para um host permitido e registre seu diário.
4. Importe uma evidência local e registre sua origem. O backend calcula SHA-256 e confere a integridade antes de download, backup ou análise por IA.
5. Registre um achado. Mantenha hipótese, fatos verificados, conclusão, impacto e recomendação separados. Fatos verificados exigem uma evidência vinculada da mesma investigação.
6. Atualize o status de submissão, referência e recompensa quando necessário. Esses dados são registros manuais; a aplicação não acessa plataformas de bounty.
7. Selecione uma investigação em Relatórios, escolha PT ou EN e gere um snapshot. Abra o registro para baixar Markdown ou PDF.

Sem dados de demonstração por padrão. Para instalar apenas fixtures sintéticas, com domínio reservado `.test`:

```powershell
.\.venv\Scripts\python.exe -m backend.cli demo
```

O comando é idempotente e não conecta a nenhum alvo. O achado de exemplo registra que nenhuma vulnerabilidade foi demonstrada.

## Configuração local e IA opcional

Copie `.env.example` para `.env` na raiz. O arquivo é ignorado pelo Git. Variáveis do ambiente têm precedência. Reinicie o backend após alterações.

```dotenv
# Opcional: diretório dedicado fora do repositório
# CASPAR_DATA_DIR=C:/Users/usuario/.caspar
OPENAI_API_KEY=
OPENAI_MODEL=
OLLAMA_MODEL=
OLLAMA_PORT=11434
AI_INPUT_COST_PER_MILLION=0
AI_OUTPUT_COST_PER_MILLION=0
```

Escolha explicitamente o identificador de um modelo disponível na sua conta OpenAI ou instalado no Ollama. Não há modelo externo selecionado por padrão. O Ollama usa exclusivamente `127.0.0.1`, não aceita URL customizada e deve executar um modelo local, sem encaminhamento para serviços de nuvem.

Na tela Evidências, selecione uma investigação e clique **Analisar com IA**. Escolha arquivos textuais e uma pergunta. Preparar a prévia não faz tráfego de rede. Revise o conteúdo integral e marque a aprovação para habilitar o envio. Uma aprovação vale por dez minutos e uma única tentativa; falhas não geram reenvio automático. A aplicação envia apenas as instruções exibidas e o payload da prévia, sem anexos binários, diário, políticas ou acesso ao restante do computador.

Há redação automática de padrões comuns de credenciais, cookies, HAR, e-mails e chaves privadas, mas **ela não encontra todos os segredos ou dados pessoais**. Prepare recortes mínimos e remova dados sensíveis antes da importação. Se encontrar um segredo na prévia, volte e importe um material saneado.

A integração OpenAI usa a Responses API com `store: false`, sem ferramentas. Isso desativa o armazenamento da resposta para recuperação pela API; não constitui garantia de retenção zero pelo provedor. Consulte a [documentação oficial da Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) e os [controles de dados](https://developers.openai.com/api/docs/guides/your-data) antes de aprovar conteúdo externo.

Respostas de IA são apresentadas como **não verificadas**, exigem seções distintas de hipóteses, observações e conclusões e nunca criam achados automaticamente. As tarifas são configuradas por milhão de tokens; valores zero significam estimativa não configurada. A prévia usa aproximação de caracteres por token, não um orçamento garantido. Após a resposta, o custo usa o consumo informado pelo provedor.

## Backup, exportação e exclusão

Em **Dados e privacidade**:

- **Exportar:** JSON com registros e metadados. Não inclui os arquivos originais.
- **Criar backup:** ZIP com snapshot SQLite, todas as evidências e manifesto SHA-256. O download também deixa uma cópia em `~/.caspar/backups`. Tokens e payloads de aprovação de IA não são incluídos no snapshot.
- **Excluir dados:** exige digitar `EXCLUIR`; remove registros, evidências, relatórios/análises e backups internos. Cópias baixadas ou externas ficam sob seu controle.

Programas e investigações também podem ser excluídos com seus dependentes. Evidências vinculadas a achados não podem ser excluídas até remover o vínculo. Ao excluir uma evidência isolada, os snapshots de relatório e análises da investigação são removidos para evitar retenção indireta. Backups antigos podem continuar contendo registros excluídos até serem apagados.

Veja [restauração e operação](docs/OPERATIONS.md). ZIPs e JSONs exportados não são criptografados. Guarde-os em armazenamento protegido. A exclusão é lógica e de arquivos; não promete sanitização forense de SSDs ou remoção de cópias do sistema operacional.

## Desenvolvimento e testes

Backend, um terminal:

```powershell
.\.venv\Scripts\python.exe -m backend.cli serve
```

Frontend com Vite, outro terminal:

```powershell
cd frontend
npm.cmd run dev
```

Acesse **http://127.0.0.1:5173**. O Vite encaminha `/api` ao backend local. O build de produção é servido diretamente pelo FastAPI; não há dependência de CDN ou fontes externas.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd test
npm.cmd run build
```

No Linux/macOS use `.venv/bin/python` e `npm`. O lock Python registra as versões verificadas, incluindo dependências de teste; `frontend/package-lock.json` fixa a árvore npm. Para atualizar, revise as novas versões, regenere os locks e repita a suíte.

Os testes usam bancos temporários, migrations reais, fixtures sintéticas e transportes simulados para IA. HTTP externo real é bloqueado nos testes. Eles cobrem persistência, backup/restauração, exclusão, escopo, upload, integridade, referências, exportação PT/EN, consentimento e interface. Veja [registro de validação](docs/VALIDATION.md).

## Docker Compose opcional

```sh
docker compose up --build
```

Interface e API em `http://127.0.0.1:8000`, com volume local `caspar_data`, usuário sem privilégios e publicação de porta apenas no loopback do host. O exemplo suporta OpenAI opcional via ambiente. Ollama no host não é alcançável pelo loopback do container; use execução nativa para Ollama nesta versão. Não altere a publicação para `0.0.0.0` nem exponha este serviço por túnel ou proxy público.

## Limites desta versão

- Produto para um usuário e uma instância/processo do backend. Sem autenticação: a conta e os processos locais confiáveis são o limite de acesso. Cabeçalho local, validação de Host/Origin e CSP protegem o uso no navegador, mas não substituem autenticação remota.
- Scope Guard offline somente para hostname/IP e wildcard de subdomínio. Sem CIDR, caminhos, portas específicas, expiração automática, validação de propriedade ou interpretação automática de políticas. Não converta autorização parcial de URL em permissão para o host inteiro.
- IA somente para UTF-8 textual, até 30 mil caracteres por evidência e 60 mil por análise; não há OCR, leitura de PDF, terminal, busca ou acesso a alvos. Prompt injection pode influenciar o texto do modelo; ele não possui ferramentas ou capacidade de executar ações.
- Relatórios têm estrutura PT/EN determinística. Textos do pesquisador permanecem no idioma original; não há tradução automática sem consentimento. PDF usa fontes padrão, adequadas para português/inglês; outros alfabetos e emojis podem não renderizar.
- Workspace e backup são processados em memória, adequados a um acervo pessoal pequeno. Sem paginação, deduplicação, criptografia própria, restauração pela interface ou busca de texto nos arquivos.
- Não há garantia de correção de análise de IA, atualização automática de CWE/OWASP, CVSS automático ou prova de vulnerabilidade. A verificação humana continua obrigatória.
- Docker e revisão visual em navegador real dependem do ambiente; consulte o registro de validação para o que foi efetivamente executado.

Arquitetura e decisões: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Modelo de ameaça: [SECURITY.md](docs/SECURITY.md). Planejamento inicial: [PLAN.md](docs/PLAN.md).
