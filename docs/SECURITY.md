# Segurança e privacidade

## Limite de confiança

O CASPAR é local e pessoal, para um único usuário de SO e uma instância. O serviço nativo escuta somente `127.0.0.1:8000`. Não exponha o backend em rede, túnel, ambiente compartilhado ou proxy. Aplicativos executados na mesma conta do usuário têm capacidade de ler o acervo e chamar a API; esta edição não oferece isolamento entre processos locais.

O Scope Guard é um controle de organização de autorização registrada pelo proprietário. Ele não verifica a legitimidade da autorização nem executa testes em alvos. O usuário deve conferir validade, restrições e políticas antes de qualquer coleta feita fora da aplicação.

## Controles implementados

| Risco | Controle e limite |
| --- | --- |
| Alvo fora do escopo | Negação por padrão, autorização obrigatória, proibição prioritária, validação offline na criação de investigação, importação, novo achado e IA. Revogar autorização preserva registros antigos para consulta, atualização de acompanhamento e exportação. |
| SSRF | Não há importação por URL. Nenhum alvo é resolvido. IA usa apenas OpenAI HTTPS fixo ou loopback numérico Ollama, sem redirects nem proxies do ambiente. |
| Path traversal | API aceita upload, não caminho local. Nomes originais nunca controlam caminho; arquivos internos usam UUID validado. Extensões permitidas, tamanho e SHA-256 são conferidos. |
| Upload malicioso | Conteúdo tratado como bytes inertes; sem unzip, shell, OCR, parsing de PDF ou renderização HTML. Downloads são anexos octet-stream com `nosniff`. O sistema não faz antivírus; evite abrir arquivos desconhecidos fora dele. |
| Exaustão por corpo HTTP | Middleware limita o corpo completo antes do parser multipart, inclusive sem Content-Length, e a escrita conta bytes em blocos. Limite de upload 10 MiB, demais mutações 1 MiB. |
| XSS e Markdown remoto | React escapa strings, sem `dangerouslySetInnerHTML`. Relatórios escapam HTML e sintaxe Markdown importada. PDF escapa markup e não busca imagens ou fontes externas. CSP restringe conteúdo e conexões à própria origem. |
| CSRF e DNS rebinding | Host restrito a loopback/localhost, Origin em lista fechada, cabeçalho customizado em todas as rotas de dados, sem CORS amplo. Isso não autentica processos locais. |
| Prompt injection | Conteúdo selecionado é serializado como dados não confiáveis; instruções fixas separam hipóteses, observações e conclusões. Modelos não recebem ferramentas nem acesso ao disco. Respostas nunca viram fatos automaticamente. Não há garantia de que texto gerado esteja livre de influência maliciosa. |
| Segredos em IA | Redação de padrões comuns, prévia integral obrigatória, aprovação de uso único, validade curta e modelos sem credenciais no frontend. Detecção é heurística; revisão humana é indispensável. |
| Vazamento via Git | Dados fora do repositório por padrão e configuração rejeitada se apontar para dentro. `.gitignore` e `.dockerignore` excluem ambientes, banco, evidências, logs, backups e chaves comuns. |
| Dados em logs | Sem access log HTTP nos scripts de execução. Erros de provedor retornam mensagens genéricas, sem corpo externo ou chave. Não habilite debug/telemetria com conteúdos privados. Erros inesperados ainda podem produzir traceback local; proteja também a saída do terminal. |
| Exclusão e backups | Exclusão em cascata, limpeza de arquivos e snapshots relacionados, `secure_delete` e VACUUM na exclusão total. Backups e downloads anteriores precisam de gestão separada. Sem promessa de sanitização física. |

## Proteção do diretório

Planos e execuções manuais (0.2) não concedem capacidade de rede. A aprovação é vinculada à revisão do plano e ao digest do contexto de escopo, com expiração em 24 horas e consumo atômico ao registrar o resultado. Revisão de histórico não exige autorização ainda vigente para permitir documentação de trabalhos encerrados, mas novos planos, edições, aprovações e registros exigem escopo permitido. Históricos preservam a autorização declarada na época; o sistema não comprova sua legitimidade.

No Windows, o setup aplica ACL sem herança, permitindo usuário atual e SYSTEM na pasta dedicada. Execute novamente após restauração ou mudança de caminho. Unix utiliza permissões privadas. Não use pastas sincronizadas automaticamente ou compartilhadas. Use BitLocker/FileVault/LUKS ou equivalente para proteger dados em repouso; o SQLite não é criptografado pela aplicação.

O prefixo do diretório escolhido é validado antes de limpeza. A API de exclusão nunca recebe caminho de filesystem e só trabalha nas pastas fixas do acervo. Não altere links, junctions ou arquivos internos enquanto o servidor está em execução.

## Reportar problemas

Reproduza com fixtures sintéticas, sem chaves ou evidências reais. Descreva versão, passos e limite de confiança afetado. Não anexe banco privado, .env, ZIP de backup ou HAR real a uma issue pública.
