# Operação local e recuperação

## Diretórios

O diretório mostrado em Dados e privacidade é a fonte de verdade. Padrão: `~/.caspar`. Cada evidência tem nome interno aleatório; o banco armazena o nome original, origem, hash e vínculo. Não renomeie arquivos internos. Não exclua o banco isoladamente: isso destrói os vínculos das evidências.

Migrations são aplicadas no início do backend e no comando `init`. Antes de atualizar o código ou dependências, encerre o servidor e faça uma cópia protegida do diretório completo ou um backup pela interface. Não use CLI de escrita simultaneamente ao servidor.

Na versão 0.2, `test_plans` e `test_runs` guardam planos versionados e histórico de registros manuais. Atualizar um plano preserva os snapshots de registros anteriores. Aprovação tem uso único e validade de 24 horas; mudanças de política ou escopo exigem nova aprovação. Após restaurar um backup, planos que aguardavam registro voltam a Planejado para revisão. O restante do histórico permanece.

## Restaurar backup da aplicação

Somente restaure um ZIP gerado por uma instalação CASPAR de confiança. Não abra nem extraia backups recebidos de terceiros. O fluxo abaixo foi coberto por teste de restauração com snapshot gerado pela própria aplicação.

1. Encerre o servidor com Ctrl+C. Preserve a pasta atual e os backups existentes.
2. Escolha uma pasta nova e vazia fora do repositório, por exemplo `C:/Users/usuario/.caspar-restored`.
3. Inspecione o ZIP. Ele deve conter `caspar.sqlite3`, `manifest.json` e somente arquivos `evidence/<32 caracteres hexadecimais>.bin`. Rejeite caminhos absolutos, `..`, links, arquivos extras ou um volume desproporcional ao seu acervo.
4. Extraia o ZIP de confiança na nova pasta. Compare SHA-256 de cada evidência com o manifesto (`Get-FileHash -Algorithm SHA256` no Windows). O teste de integridade SQLite pode ser executado com Python conforme abaixo.
5. Configure `CASPAR_DATA_DIR` no `.env` para a pasta nova. Execute `python -m backend.cli init` com o Python do ambiente virtual. Isso aplica migrations pendentes e cria pastas reservadas ausentes.
6. No Windows, execute `scripts/Protect-Data.ps1` usando a política de processo documentada no README. Confira as permissões; no Unix, proteja a pasta e arquivos para uso exclusivo da conta.
7. Inicie a aplicação e confira programas, contagens e um download de evidência. Um arquivo com hash divergente será bloqueado. Gere e confira um relatório antes de retomar o uso.

Exemplo de verificação, substituindo o caminho pelo snapshot restaurado:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; from contextlib import closing; p='C:/Users/usuario/.caspar-restored/caspar.sqlite3'; c=sqlite3.connect(p); print(c.execute('PRAGMA integrity_check').fetchall()); print(c.execute('PRAGMA foreign_key_check').fetchall()); c.close()"
```

O esperado é `ok` na integridade e uma lista vazia nas chaves estrangeiras. O JSON exportado é útil para leitura e portabilidade; esta versão não o importa de volta automaticamente. O ZIP restaura o acervo completo. Autorizações de envio para IA não são restauradas; é necessário aprovar novas prévias.

## Exclusão

Exclusão individual de programa/investigação não apaga backups antigos. A exclusão total apaga backups internos, mas não downloads, cópias externas, sincronização do SO ou histórico de snapshots. Após excluir dados sensíveis, gerencie essas cópias separadamente. A pasta vazia e o schema SQLite permanecem para permitir continuar usando a aplicação.

## Solução de problemas

- **API indisponível:** confira `http://127.0.0.1:8000/api/health`; não inicie um segundo servidor sobre o mesmo banco.
- **Tela não aparece:** rode `npm.cmd run build` em `frontend` e reinicie o backend. O diretório estático é registrado na inicialização.
- **Escopo bloqueado:** confira autorização, regra permitida, proibições prioritárias e formato do host. Wildcards não incluem a raiz do domínio. Políticas limitadas a caminho/porta não são representáveis nesta versão.
- **Arquivo bloqueado por integridade:** não altere o hash no banco. Preserve o arquivo, restaure uma cópia íntegra e confira a origem.
- **Provedor indisponível ou saída inválida:** a tentativa consumiu a aprovação. Confira modelo e serviço local/credenciais, prepare nova prévia e aprove novamente. Não há retry automático.
- **Estimativa zero:** configure tarifas no `.env`; não significa gratuidade. A estimativa não é limite financeiro do provedor.
- **Mudança de diretório:** com o servidor parado, copie todo o diretório para uma pasta dedicada fora do Git, configure o novo caminho e confira integridade antes de remover a cópia antiga.

## Evolução recomendada

1. Adicionar expiração estruturada de autorização e versionamento de políticas/escopo.
2. Oferecer restauração validada na interface e criptografia de backups com chave do proprietário.
3. Paginar o acervo, transmitir backups sem carregar tudo em memória e implementar reconciliação de arquivos órfãos.
4. Adicionar revisão de redação por campo, orçamentos de IA e resultados estruturados com referências validadas.
5. Evoluir PDF para fontes Unicode incorporadas e tradução explícita de trechos selecionados, sempre com revisão.
6. Adicionar testes E2E em navegador e revisão de acessibilidade em dispositivos reais, mantendo ausência de varredura e execução automática.
