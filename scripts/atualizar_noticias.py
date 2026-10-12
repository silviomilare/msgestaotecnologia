#!/usr/bin/env python3
"""
Coletor de notícias – MS Gestão & Tecnologia
--------------------------------------------
Lê feeds RSS de veículos especializados, filtra conteúdo promocional e
grava `noticias.json` na raiz do site. Só usa a biblioteca padrão do Python 3.

Uso (local ou no GitHub Actions):
    python3 scripts/atualizar_noticias.py noticias.json

No repositório, o workflow .github/workflows/noticias.yml roda este script
a cada 3 horas e faz commit do noticias.json atualizado (o GitHub Pages publica).

Boas práticas adotadas:
  * Exibe só título, trecho curto (até 220 caracteres) e link para a matéria original.
  * Não baixa nem hospeda imagens dos veículos.
  * Se todas as fontes falharem, mantém o arquivo anterior (o site nunca fica vazio).
"""
import html
import json
import os
import re
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ---------------------------------------------------------------------------
# Fontes (edite à vontade). "cor" é a bolinha exibida no card.
# ---------------------------------------------------------------------------
FONTES = [
    {"nome": "Convergência Digital", "url": "https://www.convergenciadigital.com.br/feed/",
     "categoria": "Governo & TI", "cor": "#2563eb", "max": 6},
    {"nome": "IT Forum", "url": "https://itforum.com.br/feed/",
     "categoria": "Tecnologia", "cor": "#1DAF6E", "max": 6},
    {"nome": "Baguete", "url": "https://www.baguete.com.br/rss/noticias/feed",
     "categoria": "Tecnologia", "cor": "#f97316", "max": 5},
    {"nome": "Contábeis", "url": "https://www.contabeis.com.br/rss/noticias/",
     "categoria": "Gestão & Fiscal", "cor": "#a855f7", "max": 6},
    {"nome": "MundoGEO", "url": "https://mundogeo.com/feed/",
     "categoria": "Geotecnologia", "cor": "#0ea5e9", "max": 4},
]

TOTAL_MAX = 30          # itens gravados no JSON
RESUMO_MAX = 220        # caracteres do trecho
TIMEOUT = 20            # segundos por feed
USER_AGENT = "MSGestaoNewsBot/1.0 (+https://msgestaotecnologia.com.br)"

# Palavras que indicam conteúdo comercial/promocional ou fora do tom institucional
BLOQUEIO = re.compile(
    r"\b(oferta|promo[cç][aã]o|desconto|cupom|black ?friday|achados?|"
    r"menor pre[cç]o|frete gr[aá]tis|patrocinad[oa]|publieditorial|"
    r"aposta|bet|loteria|mega-?sena|hor[oó]scopo)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def limpar_texto(s: str) -> str:
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    # remove rodapés típicos do WordPress: "O post X apareceu primeiro em Y."
    s = re.sub(r"(O post|The post) .{0,200}? (apareceu primeiro em|appeared first on) .*$", "", s).strip()
    return s


def resumir(s: str, n: int = RESUMO_MAX) -> str:
    s = limpar_texto(s)
    if len(s) <= n:
        return s
    corte = s[:n].rsplit(" ", 1)[0].rstrip(",.;:–- ")
    return corte + "…"


def parse_data(s: str):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))  # ISO 8601 (Atom)
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _txt(el, *tags):
    for t in tags:
        x = el.find(t)
        if x is not None:
            if t.endswith("link") and x.get("href"):
                return x.get("href")
            if x.text:
                return x.text
    return ""


def extrair_itens(raw: bytes):
    """Tenta XML estrito; se o feed vier malformado, cai para extração por regex."""
    itens = []
    try:
        root = ET.fromstring(raw)
        ns_atom = "{http://www.w3.org/2005/Atom}"
        nodes = root.findall(".//item") or root.findall(f".//{ns_atom}entry")
        for it in nodes:
            itens.append({
                "titulo": _txt(it, "title", f"{ns_atom}title"),
                "link": _txt(it, "link", f"{ns_atom}link"),
                "resumo": _txt(it, "description", f"{ns_atom}summary", f"{ns_atom}content"),
                "data": _txt(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date",
                             f"{ns_atom}published", f"{ns_atom}updated"),
                "categorias": [c.text or "" for c in it.findall("category")],
            })
        return itens
    except ET.ParseError:
        pass

    txt = raw.decode("utf-8", errors="replace")
    for bloco in re.findall(r"<item\b.*?</item>", txt, flags=re.S | re.I):
        def tag(n):
            m = re.search(rf"<{n}\b[^>]*>(.*?)</{n}>", bloco, flags=re.S | re.I)
            return m.group(1) if m else ""
        itens.append({"titulo": tag("title"), "link": tag("link"), "resumo": tag("description"),
                      "data": tag("pubDate") or tag("dc:date"),
                      "categorias": re.findall(r"<category[^>]*>(.*?)</category>", bloco, flags=re.S)})
    return itens


def coletar(fonte):
    raw = baixar(fonte["url"])
    saida = []
    for it in extrair_itens(raw):
        titulo = limpar_texto(it["titulo"])
        link = limpar_texto(it["link"])
        if not titulo or not link.startswith("https://"):
            continue
        cats = " ".join(limpar_texto(c) for c in it.get("categorias", []))
        if BLOQUEIO.search(titulo) or BLOQUEIO.search(cats) or "/achados/" in link:
            continue
        d = parse_data(limpar_texto(it["data"]))
        saida.append({
            "titulo": titulo,
            "link": link,
            "resumo": resumir(it["resumo"]),
            "data": d.isoformat() if d else None,
            "fonte": fonte["nome"],
            "categoria": fonte["categoria"],
            "cor": fonte["cor"],
        })
        if len(saida) >= fonte.get("max", 5):
            break
    return saida


def gravar_atomico(caminho, dados):
    pasta = os.path.dirname(os.path.abspath(caminho)) or "."
    fd, tmp = tempfile.mkstemp(dir=pasta, prefix=".noticias-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, caminho)


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else "noticias.json"
    todos, ok, erros = [], [], []
    for f in FONTES:
        try:
            itens = coletar(f)
            todos.extend(itens)
            ok.append(f"{f['nome']}={len(itens)}")
        except Exception as e:  # noqa: BLE001 – uma fonte fora do ar não derruba as demais
            erros.append(f"{f['nome']}: {type(e).__name__}: {e}")

    agora = datetime.now(timezone.utc)
    print(f"[{agora:%Y-%m-%d %H:%M:%S}Z] ok: {', '.join(ok) or '-'}")
    for e in erros:
        print("  ERRO", e)

    if not todos:
        print("  Nenhum item coletado – arquivo anterior mantido.")
        return 1

    # remove duplicados por título e ordena do mais recente para o mais antigo
    vistos, unicos = set(), []
    for n in todos:
        chave = re.sub(r"\W+", "", n["titulo"].lower())
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(n)
    unicos.sort(key=lambda n: n["data"] or "", reverse=True)

    gravar_atomico(destino, {
        "atualizado_em": agora.isoformat(),
        "fontes": [f["nome"] for f in FONTES],
        "itens": unicos[:TOTAL_MAX],
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
