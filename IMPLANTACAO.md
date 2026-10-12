# Implantação — novo site MS Gestão & Tecnologia

> Documento de passagem. Repositório: `C:\Gestao_Empresa\msgestaotecnologia` → `https://github.com/silviomilare/msgestaotecnologia` (branch `main`)
> **Publicação: nginx no servidor da empresa** (`/var/www/msgestaotecnologia`, que é um clone deste repositório), atrás do Cloudflare.
> **Não usa GitHub Pages** (o `CNAME` é herança da primeira publicação) e não usa GitHub Actions.
> Data: 12/10/2026

---

## 1. Situação

| Arquivo | Status | O que é |
|---|---|---|
| `index.html` | alterado | Site reescrito (novo layout, animações, seção de notícias) |
| `README.md` | alterado | Estrutura e fluxo de publicação |
| `scripts/atualizar_noticias.py` | novo | Coletor RSS (somente biblioteca padrão do Python 3) |
| `.gitignore` | novo | Mantém o `noticias.json` fora do git |
| `IMPLANTACAO.md` | novo | Este arquivo |
| `noticias.json` | local, **não versionado** | Gerado pelo coletor (no servidor, via cron) |

O nginx do servidor já bloqueia (404) `/.git`, arquivos `.md/.py/.yml` e `/scripts/` (feito em 12/10/2026,
backup do config em `~ubuntu/backups_nginx/`). A pasta do site é o próprio repositório, então essas regras
não podem ser removidas.

---

## 2. O que mudou no site

**Preservado do site anterior**
- Logo de três círculos (#1B5E96, #4AAEE8, #1DAF6E), agora com animação de órbita
- Fontes da marca: DM Sans e DM Serif Display
- Todos os textos institucionais: Quem somos, Serviços, Por que a MS, Segmentos e Contato
- E-mail `contato@msgestaotecnologia.com.br` e WhatsApp `(44) 99906-9725`
- **Rastreamento** (`/track/evento`): visita e cliques com `data-track="clique_whatsapp"` / `"clique_email"`. O `SITE_TOKEN` original foi mantido.
- **Formulário de lead** (`/track/lead`): mesmo payload (`nome`, `email`/`telefone`, `mensagem`, `utm_source`, `sessao_id`)
- Link para o sistema (`sistema.msgestaotecnologia.com.br`) no rodapé

**Novidades**
- Hero com rede animada em canvas que reage ao mouse e pausa quando sai da tela ou quando a aba fica oculta
- Título que entra linha a linha e palavras que se alternam em "Especialistas em…"
- Painel de exemplo no hero, marcado como "ilustrativo", com efeito de inclinação 3D
- Faixa de números com contagem animada (10+ anos · 6 frentes · 3 estados · 24h úteis)
- Elementos que aparecem conforme a rolagem, brilho que segue o cursor nos cards de serviço e órbita animada em "Quem somos"
- Abas animadas Setor privado / Setor público, com navegação por setas do teclado
- Menu que muda ao rolar, barra de progresso de leitura, link ativo da seção atual e menu lateral no celular
- Botão flutuante do WhatsApp
- **Seção "Radar MS"** (`#noticias`) com cards e filtro por tema, alimentada por `noticias.json`
- Formulário com campo "Interesse principal" (vai como prefixo na `mensagem`: `[Interesse: X] ...`) e caixa de consentimento LGPD obrigatória
- SEO: meta description, canonical, Open Graph e JSON-LD `ProfessionalService`
- Acessibilidade: link "pular para o conteúdo", foco visível, `aria-*` e respeito a `prefers-reduced-motion`

**Testado localmente (Playwright, Chromium)**
- Desktop 1366px e celular 390px, sem rolagem horizontal
- Formulário: validações (campos vazios e sem consentimento) e envio com sucesso, usando servidor simulado
- Rastreamento: evento `visita` disparado com o payload correto
- Abas e filtro de notícias funcionando

---

## 3. Notícias — como funciona

- **Fontes** (RSS validados em 12/10/2026): Convergência Digital (Governo & TI), IT Forum (Tecnologia), Baguete (Tecnologia), Contábeis (Gestão & Fiscal) e MundoGEO (Geotecnologia)
- Para editar as fontes, mude a lista `FONTES` em `scripts/atualizar_noticias.py`
- Promoções e ofertas são filtradas pela regex `BLOQUEIO`
- Cada notícia mostra título, trecho de até 220 caracteres e link para a matéria original. Imagens dos veículos não são baixadas nem hospedadas.
- O coletor tolera feeds malformados (usa regex quando o XML falha), remove duplicados e ordena por data. Se todas as fontes falharem, mantém o arquivo anterior.
- O front-end lê `noticias.json?v=<bloco de 10 min>`. Se o arquivo não estiver disponível, mostra uma mensagem amigável.
- Fontes que **não** devem ser usadas: Tecnoblog e Olhar Digital (muitas ofertas), Canaltech (robots bloqueia) e Gov.br Governo Digital (o RSS exige login)
- **Quem atualiza:** o cron do usuário `www-data` no servidor, a cada 3 horas, gravando direto em
  `/var/www/msgestaotecnologia/noticias.json` (escrita atômica, permissão 644). Log em `/var/log/noticias_msgestao.log`.

Para testar localmente:
```
python scripts/atualizar_noticias.py noticias.json
```

---

## 4. Publicar (passo a passo)

### 4.1 No GitHub Desktop (máquina local)
1. Abrir o repositório `msgestaotecnologia` (File → Add local repository → `C:\Gestao_Empresa\msgestaotecnologia`).
2. Conferir as alterações: `index.html`, `README.md`, `IMPLANTACAO.md`, `.gitignore`, `scripts/atualizar_noticias.py`.
   O `noticias.json` **não** deve aparecer (está no `.gitignore`).
3. Mensagem do commit sugerida: `Novo layout, animacoes e secao de noticias (Radar MS)`
4. **Commit to main** → **Push origin**.

### 4.2 No servidor (como `ubuntu`)
```
sudo -u www-data git -C /var/www/msgestaotecnologia pull
sudo -u www-data python3 /var/www/msgestaotecnologia/scripts/atualizar_noticias.py /var/www/msgestaotecnologia/noticias.json
```
O segundo comando gera o primeiro `noticias.json` (sem ele a seção Notícias mostra a mensagem de indisponível).
O nginx serve direto da pasta; não precisa reiniciar nada.

### 4.3 Cron do coletor (uma única vez)
```
sudo -u www-data crontab -e
```
Linha a adicionar:
```
17 */3 * * * /usr/bin/python3 /var/www/msgestaotecnologia/scripts/atualizar_noticias.py /var/www/msgestaotecnologia/noticias.json >> /var/log/noticias_msgestao.log 2>&1
```
(o arquivo de log precisa existir e ser gravável pelo `www-data`: `sudo touch /var/log/noticias_msgestao.log && sudo chown www-data /var/log/noticias_msgestao.log`)

### 4.4 Validar em produção (https://msgestaotecnologia.com.br, com Ctrl+F5)
- [ ] O Cloudflare entregou a versão nova (aparece a seção "Radar MS")
- [ ] As animações do hero, os contadores e os elementos que aparecem ao rolar funcionam
- [ ] A seção Notícias carrega os cards e o filtro por tema funciona
- [ ] Os links das notícias abrem a matéria original em nova aba
- [ ] O formulário envia e aparece "Recebemos seu contato!", com o lead criado no funil do sistema
- [ ] No sistema, aparecem visitas e cliques de WhatsApp/e-mail (`/track/evento`)
- [ ] No celular, o menu lateral, o layout e o botão do WhatsApp funcionam
- [ ] O CORS de `sistema.msgestaotecnologia.com.br` continua aceitando a origem `https://msgestaotecnologia.com.br`
- [ ] `/.git/config`, `/README.md` e `/scripts/...` retornam 404

### 4.5 Se der problema
- **Voltar ao site anterior:** `sudo -u www-data git -C /var/www/msgestaotecnologia checkout 02641b3 -- index.html` (o commit anterior é `02641b3`), ou `git revert` + push + pull.
- **Cloudflare mostrando versão antiga:** Cloudflare → Caching → Purge Everything.
- **Uma fonte de notícias quebrou:** o log `/var/log/noticias_msgestao.log` mostra `ERRO <fonte>`. Remova ou ajuste essa fonte em `FONTES`.
- **Notícias não aparecem:** confira se `noticias.json` existe na pasta do site e é um JSON válido.
- **Voltar o nginx:** o backup do config está em `~ubuntu/backups_nginx/` (copiar para `/etc/nginx/sites-available/msgestaotecnologia`, `sudo nginx -t`, `sudo systemctl reload nginx`).

---

## 5. Ideias para depois (opcional)
- Imagem Open Graph (`og:image`, 1200×630) com a logo, para melhorar a prévia no WhatsApp e no LinkedIn
- Trocar o painel ilustrativo do hero por um print real e anonimizado do sistema MS Gestão
- Página de Política de Privacidade (LGPD), com link no consentimento do formulário
- Adicionar o domínio ao Google Search Console e enviar um sitemap
