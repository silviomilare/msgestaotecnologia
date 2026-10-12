# msgestaotecnologia
Site institucional — MS Gestão & Tecnologia. Publicado no servidor da empresa (nginx, atrás do Cloudflare)
em `/var/www/msgestaotecnologia`, que é um clone deste repositório. Não usa GitHub Pages.

## Estrutura
- `index.html` — página única (HTML/CSS/JS inline, sem build).
- `noticias.json` — manchetes da seção "Radar MS". **Gerado no servidor** pelo cron; não é versionado (`.gitignore`).
- `scripts/atualizar_noticias.py` — coletor RSS (só biblioteca padrão do Python).
- `IMPLANTACAO.md` — o que mudou no novo site e como publicar.

## Publicar uma alteração
1. Edite o `index.html` e faça commit + push (GitHub Desktop).
2. No servidor (como `ubuntu`): `sudo -u www-data git -C /var/www/msgestaotecnologia pull`
O nginx serve direto da pasta; não precisa reiniciar nada.

## Notícias
Fontes: Convergência Digital, IT Forum, Baguete, Contábeis e MundoGEO (edite a lista `FONTES` no script).
Itens promocionais são filtrados pela expressão `BLOQUEIO`. Exibimos só título, trecho e link para a matéria original.
Um cron do usuário `www-data` roda o coletor a cada 3 horas. Teste manual local:
```
python scripts/atualizar_noticias.py noticias.json
```

## Rastreamento / leads
Visitas e cliques (`data-track`) vão para `sistema.msgestaotecnologia.com.br/track/evento`;
o formulário envia para `/track/lead` (cria lead no funil do sistema).

## Segurança do nginx
O config do site bloqueia (404) `/.git`, arquivos `.md/.py/.yml` e `/scripts/`. Não remova essas regras:
a pasta do site é o próprio repositório.
