"""Gera as artes animadas do README do perfil (tema: RPG + música pop).

- dist/banner.svg   cabeçalho com d20 rolando, equalizador e subtítulo digitando
- dist/mochila.svg  inventário de RPG: linguagens viram poções, números viram recursos e conquistas
- dist/jornada.svg  dois dragõezinhos atravessam o gráfico de contribuições acendendo os dias com fogo

Só usa a biblioteca padrão do Python. Roda todo dia pelo GitHub Actions
(.github/workflows/atualizar-svgs.yml). Para rodar local:
    GITHUB_TOKEN=$(gh auth token) python scripts/gerar_svgs.py
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USUARIO = os.environ.get("GITHUB_USER", "guxzi")
NOME = "Gustavo Zimmermann"
SAIDA = Path(__file__).resolve().parent.parent / "dist"

# Paleta: noite de show pop + dourado de taverna
FUNDO_1, FUNDO_2 = "#140f24", "#0d1326"
BORDA = "#2e2650"
TEXTO, TEXTO_2 = "#f4effa", "#a99fc6"
ROSA, ROXO, CIANO, OURO = "#ff4fa3", "#9b5cff", "#3ddcff", "#ffd166"
FONTE = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'SFMono-Regular', 'DejaVu Sans Mono', monospace"


# ------------------------------------------------------------------ dados
CONSULTA = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""


def buscar_dados():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Defina GITHUB_TOKEN (no Actions ele já existe; local: gh auth token).")
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "readme-svgs"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resposta = json.load(r)
    if "errors" in resposta:
        sys.exit(f"Erro da API: {resposta['errors']}")
    u = resposta["data"]["user"]
    cc = u["contributionsCollection"]

    linguagens = {}
    cores = {}
    estrelas = 0
    for repo in u["repositories"]["nodes"]:
        estrelas += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            nome = e["node"]["name"]
            linguagens[nome] = linguagens.get(nome, 0) + e["size"]
            cores[nome] = e["node"]["color"] or ROXO

    dias = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs_issues": cc["totalPullRequestContributions"] + cc["totalIssueContributions"],
        "repos": u["repositories"]["totalCount"],
        "seguidores": u["followers"]["totalCount"],
        "estrelas": estrelas,
        "linguagens": sorted(linguagens.items(), key=lambda kv: -kv[1]),
        "cores": cores,
        "semanas": [w["contributionDays"] for w in cc["contributionCalendar"]["weeks"]],
        "dias": dias,
    }


def maior_sequencia(dias):
    melhor = atual = 0
    for d in dias:
        atual = atual + 1 if d["contributionCount"] > 0 else 0
        melhor = max(melhor, atual)
    return melhor


# ------------------------------------------------------------------ util SVG
def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def moldura(w, h, conteudo, estilo=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<defs>
  <linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{FUNDO_1}"/><stop offset="1" stop-color="{FUNDO_2}"/>
  </linearGradient>
  <linearGradient id="pop" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{ROSA}"/><stop offset=".55" stop-color="{ROXO}"/><stop offset="1" stop-color="{CIANO}"/>
  </linearGradient>
  <linearGradient id="popv" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="{ROXO}"/><stop offset=".6" stop-color="{ROSA}"/><stop offset="1" stop-color="{OURO}"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: {FONTE}; }}
  .mono {{ font-family: {MONO}; }}
  @keyframes pisca {{ 0%,100% {{ opacity: .15 }} 50% {{ opacity: 1 }} }}
  {estilo}
</style>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="url(#fundo)" stroke="{BORDA}" stroke-width="2"/>
{conteudo}
</svg>
"""


def estrelinhas(w, h, n, semente):
    """Brilhinhos fixos que piscam (posições determinísticas)."""
    out = []
    x = semente
    for i in range(n):
        x = (x * 1103515245 + 12345) % 2147483648
        px = 20 + (x % (w - 40))
        x = (x * 1103515245 + 12345) % 2147483648
        py = 14 + (x % (h - 28))
        dur = 2.2 + (i % 5) * 0.6
        out.append(f'<circle cx="{px}" cy="{py}" r="{1 + (i % 3) * 0.5}" fill="{TEXTO}" '
                   f'style="animation: pisca {dur:.1f}s ease-in-out {i * 0.37:.2f}s infinite; opacity:.2"/>')
    return "\n".join(out)


# ------------------------------------------------------------------ banner
def gerar_banner():
    w, h = 840, 210
    frases = [
        "Ciência da Computação · UNIFAL-MG",
        "Front-end, interfaces e game dev",
        "Mestre de RPG nas horas vagas",
        "Trilha sonora: pop no repeat",
    ]
    ciclo = 16  # segundos para as 4 frases
    fatia = ciclo / len(frases)
    estilo = [
        "@keyframes rola { 0% { transform: rotate(0deg) } 45% { transform: rotate(1080deg) } 100% { transform: rotate(1080deg) } }",
        ".d20 { transform-origin: 120px 105px; transform-box: view-box; animation: rola 6s cubic-bezier(.2,.7,.2,1) infinite; }",
        "@keyframes numero { 0%,44% { opacity: 1 } 45%,100% { opacity: 0 } }",
        "@keyframes vinte { 0%,44% { opacity: 0 } 46%,100% { opacity: 1 } }",
        "@keyframes critico { 0%,46% { opacity: 0; transform: translateY(6px) } 52%,90% { opacity: 1; transform: translateY(0) } 100% { opacity: 0 } }",
        ".rolando { animation: numero 6s steps(1) infinite; }",
        ".vinte { animation: vinte 6s steps(1) infinite; }",
        ".critico { animation: critico 6s ease-out infinite; }",
        "@keyframes eq { 0%,100% { transform: scaleY(.25) } 50% { transform: scaleY(1) } }",
        ".barra { transform-box: fill-box; transform-origin: bottom; animation: eq 1s ease-in-out infinite; }",
        "@keyframes nota { 0% { opacity: 0; transform: translate(0,0) } 15% { opacity: 1 } 100% { opacity: 0; transform: translate(-14px,-70px) } }",
        ".nota { animation: nota 3.6s ease-out infinite; }",
        "@keyframes cursor { 0%,100% { opacity: 1 } 50% { opacity: 0 } }",
        ".cursor { animation: cursor .8s steps(1) infinite; }",
    ]
    conteudo = [estrelinhas(w, h, 26, 7)]

    # d20 (contorno hexagonal + faces) girando e caindo no 20
    import math as m
    cx, cy, r = 120, 105, 58
    hexa = " ".join(f"{cx + r * m.cos(m.radians(90 + 60 * i)):.1f},{cy - r * m.sin(m.radians(90 + 60 * i)):.1f}" for i in range(6))
    tri = [(cx, cy - r * 0.62), (cx - r * 0.58, cy + r * 0.36), (cx + r * 0.58, cy + r * 0.36)]
    tri_s = " ".join(f"{x:.1f},{y:.1f}" for x, y in tri)
    vert = [(cx + r * m.cos(m.radians(90 + 60 * i)), cy - r * m.sin(m.radians(90 + 60 * i))) for i in range(6)]
    linhas = []
    for (tx, ty) in tri:
        for (vx, vy) in vert:
            if math.hypot(tx - vx, ty - vy) < r * 0.75:
                linhas.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{vx:.1f}" y2="{vy:.1f}"/>')
    conteudo.append(f"""<g class="d20">
  <polygon points="{hexa}" fill="{ROXO}" fill-opacity=".18" stroke="{OURO}" stroke-width="2.5" stroke-linejoin="round"/>
  <g stroke="{OURO}" stroke-opacity=".55" stroke-width="1.5">{''.join(linhas)}</g>
  <polygon points="{tri_s}" fill="{ROXO}" fill-opacity=".35" stroke="{OURO}" stroke-width="2" stroke-linejoin="round"/>
</g>
<g class="mono" font-weight="700" text-anchor="middle" font-size="24">
  <text class="rolando" x="{cx}" y="{cy + 13}" fill="{TEXTO}">?</text>
  <text class="vinte" x="{cx}" y="{cy + 13}" fill="{OURO}">20</text>
</g>
<text class="critico" x="{cx}" y="{cy + r + 26}" text-anchor="middle" font-size="13" font-weight="800" letter-spacing="3" fill="{OURO}">CRÍTICO!</text>""")

    # nome
    conteudo.append(f'<text x="228" y="92" font-size="36" font-weight="800" fill="{TEXTO}">{esc(NOME)}</text>')
    conteudo.append(f'<rect x="230" y="104" width="300" height="4" rx="2" fill="url(#pop)"/>')

    # subtítulo "digitando" (cada frase revelada por um clipPath que cresce em passos)
    for i, frase in enumerate(frases):
        ini = i * fatia / ciclo * 100
        fim = (i + 1) * fatia / ciclo * 100
        dig = ini + (fatia * 0.45) / ciclo * 100
        larg = len(frase) * 11.2 + 4
        estilo.append(
            f"@keyframes digita{i} {{ 0%,{ini:.2f}% {{ width: 0 }} {dig:.2f}%,{fim - 1.5:.2f}% {{ width: {larg:.0f}px }} {fim:.2f}%,100% {{ width: 0 }} }}"
        )
        estilo.append(f".clip{i} {{ animation: digita{i} {ciclo}s steps({len(frase)}) infinite; }}")
        conteudo.append(
            f'<clipPath id="c{i}"><rect class="clip{i}" x="230" y="122" height="34" width="0"/></clipPath>'
            f'<text clip-path="url(#c{i})" x="232" y="146" font-size="20" class="mono" fill="{TEXTO_2}">{esc(frase)}</text>'
        )
    conteudo.append(f'<text class="cursor mono" x="232" y="176" font-size="13" fill="{ROSA}">▍ pressione start para continuar</text>')

    # equalizador
    base_x, base_y = 662, 160
    duracoes = [0.9, 0.7, 1.1, 0.8, 1.3, 0.6, 1.0, 0.75, 1.2, 0.85, 0.65]
    for i, d in enumerate(duracoes):
        alt = 48 + (i * 37 % 50)
        conteudo.append(
            f'<rect class="barra" x="{base_x + i * 14}" y="{base_y - alt}" width="9" height="{alt}" rx="3" '
            f'fill="url(#popv)" style="animation-duration: {d}s; animation-delay: -{i * 0.13:.2f}s"/>'
        )
    conteudo.append(f'<rect x="{base_x - 6}" y="{base_y + 4}" width="{len(duracoes) * 14 + 4}" height="2" rx="1" fill="{BORDA}"/>')
    for i, (nx, sim) in enumerate([(668, "♪"), (712, "♫"), (756, "♪"), (798, "♬")]):
        conteudo.append(f'<text class="nota" x="{nx}" y="{base_y - 50}" font-size="20" fill="{[ROSA, CIANO, OURO, ROXO][i]}" '
                        f'style="animation-delay: {i * 0.9:.1f}s; opacity: 0">{sim}</text>')

    return moldura(w, h, "\n".join(conteudo), "\n  ".join(estilo))


# ------------------------------------------------------------------ mochila
def icone_moeda(x, y):
    return (f'<g transform="translate({x},{y})"><circle r="10" fill="{OURO}"/><circle r="6.5" fill="none" stroke="#b8862b" stroke-width="1.6"/>'
            f'<rect x="-1.5" y="-4" width="3" height="8" rx="1" fill="#b8862b"/><circle cx="-4" cy="-5" r="1.6" fill="#fff6d6"/></g>')


def icone_pergaminho(x, y):
    return (f'<g transform="translate({x},{y})"><rect x="-8" y="-7" width="16" height="14" rx="2" fill="#f1e2c0"/>'
            f'<rect x="-11" y="-9" width="4" height="18" rx="2" fill="#c9a96e"/><rect x="7" y="-9" width="4" height="18" rx="2" fill="#c9a96e"/>'
            f'<path d="M-4 -3h8M-4 0.5h8M-4 4h5" stroke="#9c7b45" stroke-width="1.4" stroke-linecap="round"/></g>')


def icone_selo(x, y):
    estrela = estrela_pontos(0, 0, 5.5, 2.4)
    return (f'<g transform="translate({x},{y})"><path d="M-6 6 L-8 13 L-3 10.5 L0 14 L0 7 Z M6 6 L8 13 L3 10.5 L0 14 L0 7 Z" fill="{ROXO}"/>'
            f'<circle r="9" fill="{ROSA}"/><polygon points="{estrela}" fill="#fff"/></g>')


def icone_estrela(x, y):
    return f'<g transform="translate({x},{y})"><polygon points="{estrela_pontos(0, 0, 10.5, 4.6)}" fill="{OURO}" stroke="#b8862b" stroke-width="1.2" stroke-linejoin="round"/></g>'


def estrela_pontos(cx, cy, r_ext, r_int, pontas=5):
    pts = []
    for k in range(pontas * 2):
        r = r_ext if k % 2 == 0 else r_int
        a = math.radians(-90 + k * 180 / pontas)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def pocao(i, cx, topo, cor, nivel):
    """Frasco redondo com líquido ondulando e bolhas subindo."""
    r = 24
    cy = topo + 24 + r
    ly = cy + r - 2 * r * nivel  # altura do líquido
    onda = f"M{cx - r - 24} {ly:.1f} q6 -3 12 0" + " t12 0" * 9 + f" V{cy + r + 2} H{cx - r - 24} Z"
    bolhas = "".join(
        f'<circle class="bolha" cx="{cx - 12 + k * 11}" cy="{cy + r - 5}" r="{1.6 + (k % 2) * 0.6}" fill="#fff" '
        f'style="animation-delay: {(i * 0.5 + k * 0.7):.1f}s"/>'
        for k in range(3)
    )
    return f"""<defs><clipPath id="frasco{i}"><circle cx="{cx}" cy="{cy}" r="{r - 2}"/></clipPath>
  <radialGradient id="aura{i}"><stop offset="0" stop-color="{cor}" stop-opacity=".45"/><stop offset="1" stop-color="{cor}" stop-opacity="0"/></radialGradient></defs>
<circle class="aura" cx="{cx}" cy="{cy}" r="{r + 16}" fill="url(#aura{i})" style="animation-delay: {i * 0.6:.1f}s"/>
<g clip-path="url(#frasco{i})">
  <rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="#ffffff" fill-opacity=".04"/>
  <path class="onda" d="{onda}" fill="{cor}" style="animation-delay: -{i * 0.4:.1f}s"/>
  <rect x="{cx - r}" y="{ly + 3:.1f}" width="{2 * r}" height="{2 * r}" fill="#000" fill-opacity=".18"/>
  {bolhas}
</g>
<rect x="{cx - 7}" y="{topo + 9}" width="14" height="17" fill="#ffffff" fill-opacity=".05" stroke="#cfc6ea" stroke-opacity=".6" stroke-width="2.2"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#cfc6ea" stroke-opacity=".6" stroke-width="2.5"/>
<rect x="{cx - 10}" y="{topo}" width="20" height="11" rx="3" fill="#8a5a3c" stroke="#5e3b24" stroke-width="1.2"/>
<path d="M{cx - 15} {cy - 9} a17 17 0 0 1 9 -11" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="3" stroke-linecap="round"/>"""


def gerar_mochila(d):
    w, h = 840, 356
    total = d["total"]
    seq = maior_sequencia(d["dias"])
    n_ling = len(d["linguagens"])
    fama = d["seguidores"] + d["estrelas"]

    estilo = [
        "@keyframes onda { from { transform: translateX(0) } to { transform: translateX(24px) } }",
        ".onda { animation: onda 2.4s linear infinite; }",
        "@keyframes bolha { 0% { transform: translateY(0); opacity: 0 } 15% { opacity: .75 } 100% { transform: translateY(-34px); opacity: 0 } }",
        ".bolha { opacity: 0; animation: bolha 2.6s ease-in infinite; }",
        "@keyframes aura { 0%,100% { opacity: .5 } 50% { opacity: 1 } }",
        ".aura { animation: aura 3s ease-in-out infinite; }",
        "@keyframes surge { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }",
        ".surge { opacity: 0; animation: surge .6s ease-out forwards; }",
        "@keyframes reflexo { 0%,55% { transform: translateX(-80px) } 100% { transform: translateX(200px) } }",
        ".reflexo { animation: reflexo 4.5s ease-in-out infinite; }",
        "@keyframes brilho { 0%,100% { opacity: .55 } 50% { opacity: 1 } }",
        ".brilho { animation: brilho 2.4s ease-in-out infinite; }",
        "@keyframes enche { from { transform: scaleX(0) } to { transform: scaleX(1) } }",
        ".progresso { transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: enche 1.4s cubic-bezier(.2,.8,.2,1) .8s forwards; }",
    ]
    c = [estrelinhas(w, h, 14, 41)]
    c.append(f'<text x="28" y="40" font-size="12" font-weight="700" letter-spacing="4" fill="{OURO}" class="brilho">MOCHILA DO AVENTUREIRO</text>')
    c.append(f'<text x="28" y="64" font-size="14" fill="{TEXTO_2}">Tudo o que juntei em '
             f'<tspan fill="{TEXTO}" font-weight="700">{plural(total, "contribuição", "contribuições")}</tspan> no último ano</text>')

    # poções = linguagens mais usadas
    soma = sum(v for _, v in d["linguagens"]) or 1
    top = d["linguagens"][:4]
    maior = (top[0][1] / soma) if top else 1
    for i, (nome, bytes_) in enumerate(top):
        x = 28 + i * 112
        pct = bytes_ / soma
        nivel = 0.25 + 0.6 * (pct / maior)  # o mais usado fica quase cheio
        cor = d["cores"].get(nome, ROXO)
        c.append(f'<g class="surge" style="animation-delay: {0.1 + i * 0.12:.2f}s">'
                 f'<rect x="{x}" y="82" width="100" height="134" rx="12" fill="{FUNDO_1}" stroke="{BORDA}" stroke-width="2"/>'
                 f'<text x="{x + 90}" y="100" text-anchor="end" font-size="11" font-weight="700" fill="{TEXTO_2}">{pct * 100:.0f}%</text>'
                 f'{pocao(i, x + 50, 92, cor, nivel)}'
                 f'<text x="{x + 50}" y="202" text-anchor="middle" font-size="13" font-weight="700" fill="{TEXTO}">{esc(nome)}</text></g>')
    if not top:
        c.append(f'<text x="28" y="150" font-size="13" fill="{TEXTO_2}">A mochila ainda está vazia.</text>')

    # recursos
    recursos = [
        (icone_moeda, "Moedas de commit", d["commits"]),
        (icone_pergaminho, "Pergaminhos (repositórios)", d["repos"]),
        (icone_selo, "Selos de guilda (PRs e issues)", d["prs_issues"]),
        (icone_estrela, "Fama (estrelas e seguidores)", fama),
    ]
    c.append(f'<g class="surge" style="animation-delay: .55s"><rect x="480" y="82" width="332" height="134" rx="12" fill="{FUNDO_1}" stroke="{BORDA}" stroke-width="2"/>')
    for k, (icone, rotulo, valor) in enumerate(recursos):
        y = 100 + k * 32
        c.append(icone(504, y + 2))
        c.append(f'<text x="526" y="{y + 7}" font-size="13" fill="{TEXTO_2}">{esc(rotulo)}</text>'
                 f'<text x="796" y="{y + 8}" text-anchor="end" font-size="17" font-weight="800" fill="{TEXTO}">{valor}</text>')
        if k < len(recursos) - 1:
            c.append(f'<rect x="496" y="{y + 17}" width="300" height="1" fill="{BORDA}"/>')
    c.append("</g>")

    # conquistas (desbloqueiam com os números reais)
    conquistas = [
        ("Aventureiro", "1 repositório", d["repos"], 1),
        ("Poliglota", "5 linguagens", n_ling, 5),
        ("Arquivista", "10 repositórios", d["repos"], 10),
        ("Constante", "7 dias seguidos", seq, 7),
        ("Em guilda", "10 PRs ou issues", d["prs_issues"], 10),
        ("Centenário", "100 contribuições", total, 100),
    ]
    feitas = sum(1 for *_, v, meta in conquistas if v >= meta)
    c.append(f'<text x="28" y="246" font-size="12" font-weight="800" letter-spacing="3" fill="{OURO}">CONQUISTAS</text>'
             f'<text x="150" y="246" font-size="12" fill="{TEXTO_2}">{feitas} de {len(conquistas)} desbloqueadas</text>')
    c.append(f'<defs><linearGradient id="ouro" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1b8"/>'
             f'<stop offset=".5" stop-color="{OURO}"/><stop offset="1" stop-color="#c98a1c"/></linearGradient></defs>')
    for i, (titulo, requisito, valor, meta) in enumerate(conquistas):
        x, y = 28 + i * 131, 258
        ok = valor >= meta
        atraso = 0.9 + i * 0.1
        if ok:
            medalha = (f'<circle cx="{x + 22}" cy="{y + 32}" r="14" fill="url(#ouro)" stroke="#c98a1c" stroke-width="1.5"/>'
                       f'<polygon points="{estrela_pontos(x + 22, y + 32, 7, 3)}" fill="#7a4d0b"/>')
            rodape = f'<text x="{x + 44}" y="{y + 54}" font-size="10" font-weight="700" fill="{OURO}">✓ desbloqueada</text>'
            reflexo = (f'<defs><clipPath id="cq{i}"><rect x="{x}" y="{y}" width="123" height="66" rx="10"/></clipPath></defs>'
                       f'<g clip-path="url(#cq{i})"><g class="reflexo" style="animation-delay: {i * 0.7:.1f}s">'
                       f'<rect x="{x}" y="{y - 10}" width="26" height="90" fill="#fff" fill-opacity=".09" transform="skewX(-20)"/></g></g>')
            borda = OURO
        else:
            medalha = (f'<circle cx="{x + 22}" cy="{y + 32}" r="14" fill="{BORDA}"/>'
                       f'<rect x="{x + 16}" y="{y + 31}" width="12" height="9" rx="2" fill="{TEXTO_2}"/>'
                       f'<path d="M{x + 18.5} {y + 31} v-3 a3.5 3.5 0 0 1 7 0 v3" fill="none" stroke="{TEXTO_2}" stroke-width="2"/>')
            frac = min(1, valor / meta)
            rodape = (f'<rect x="{x + 44}" y="{y + 48}" width="40" height="5" rx="2.5" fill="{BORDA}"/>'
                      f'<rect class="progresso" x="{x + 44}" y="{y + 48}" width="{max(3, 40 * frac):.0f}" height="5" rx="2.5" fill="url(#pop)"/>'
                      f'<text x="{x + 116}" y="{y + 54}" text-anchor="end" font-size="9.5" fill="{TEXTO_2}">{valor}/{meta}</text>')
            reflexo = ""
            borda = BORDA
        c.append(f'<g class="surge" style="animation-delay: {atraso:.2f}s">'
                 f'<rect x="{x}" y="{y}" width="123" height="66" rx="10" fill="{FUNDO_1}" stroke="{borda}" stroke-opacity="{1 if ok else .9}" stroke-width="{1.6 if ok else 2}"/>'
                 f'{reflexo}{medalha}'
                 f'<text x="{x + 44}" y="{y + 25}" font-size="12" font-weight="800" fill="{TEXTO if ok else TEXTO_2}">{esc(titulo)}</text>'
                 f'<text x="{x + 44}" y="{y + 39}" font-size="9.5" fill="{TEXTO_2}">{esc(requisito)}</text>'
                 f'{rodape}</g>')

    hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    c.append(f'<text x="{w - 28}" y="{h - 12}" text-anchor="end" font-size="10.5" fill="{TEXTO_2}">'
             f'itens e conquistas calculados dos dados públicos do GitHub · atualizada em {hoje}</text>')
    return moldura(w, h, "\n".join(c), "\n  ".join(estilo))


# ------------------------------------------------------------------ jornada
# Dragõezinhos em pixel art (de perfil, olhando para a direita).
# Cada letra é um pixel; "." é transparente. O contorno é desenhado sozinho.
DRAGAO_ASAS_CIMA = [
    ".f....................",
    ".ff......f.h..h.......",
    ".fwf....ff..h..h......",
    ".fwwf..fwf...h..h.....",
    "..fwwwfwwf..bbbbbbb...",
    "..fwwwwwwf.bbbbbbbbb..",
    "...fwwwwf..bbbbbbexbb.",
    "....fwwwf..bbbbbbeebbb",
    "k....ffff..bbbbbbcbbnb",
    "kk.....bbbbbbbbbbbbb..",
    ".bb..bbbbbbbbbll......",
    "..bbbbbbbbbbblll......",
    "...bbbbbbbbbblll......",
    ".....bbbbbbbbll.......",
    "......bb...bb.........",
]
DRAGAO_ASAS_BAIXO = [
    "......................",
    "...........h..h.......",
    "............h..h......",
    ".............h..h.....",
    "............bbbbbbb...",
    "...........bbbbbbbbb..",
    "...........bbbbbbexbb.",
    "...........bbbbbbeebbb",
    "k..........bbbbbbcbbnb",
    "kk....fffffbbbbbbbbb..",
    ".bb..bwwwwfbbbll......",
    "..bbbwwwwfbbblll......",
    "...bwwwwfbbbblll......",
    "....wwwfbbbbbll.......",
    "...wf.bb...bb.........",
]
PALETAS_DRAGAO = {
    "preto": {"b": "#221c30", "l": "#3a3150", "h": "#efe3c4", "f": "#40365a", "w": "#7b3fd1",
              "e": OURO, "x": "#fff6d6", "c": "#5c2b55", "n": "#0c0a12", "k": ROSA, "contorno": "#8a76cc"},
    "branco": {"b": "#f6f1ff", "l": "#ddd3f2", "h": OURO, "f": "#cbbfe6", "w": "#8fe3ff",
               "e": "#2a1f4a", "x": "#ffffff", "c": "#ff9ecb", "n": "#a99fc6", "k": CIANO, "contorno": "#3b2f63"},
}


def sprite(grade, cores, px):
    """Converte a grade em retângulos (juntando pixels vizinhos da mesma cor) com contorno de 1 pixel."""
    cheio = {(x, y) for y, linha in enumerate(grade) for x, ch in enumerate(linha) if ch in cores}
    mapa = {}
    for (x, y) in cheio:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in cheio:
                mapa[(x + dx + 1, y + dy + 1)] = cores["contorno"]
    for y, linha in enumerate(grade):
        for x, ch in enumerate(linha):
            if ch in cores:
                mapa[(x + 1, y + 1)] = cores[ch]
    larg, alt = len(grade[0]) + 2, len(grade) + 2
    rects = []
    for y in range(alt):
        x = 0
        while x < larg:
            cor = mapa.get((x, y))
            if not cor:
                x += 1
                continue
            ini = x
            while mapa.get((x, y)) == cor:
                x += 1
            rects.append(f'<rect x="{ini * px:.1f}" y="{y * px:.1f}" width="{(x - ini) * px + 0.25:.2f}" height="{px + 0.25:.2f}" fill="{cor}"/>')
    return "".join(rects), larg * px, alt * px


def dragao(cor, px, atraso=0.0):
    """Os dois quadros das asas se alternam; o corpo sobe e desce no ritmo."""
    cima, sw, sh = sprite(DRAGAO_ASAS_CIMA, PALETAS_DRAGAO[cor], px)
    baixo, _, _ = sprite(DRAGAO_ASAS_BAIXO, PALETAS_DRAGAO[cor], px)
    st = f' style="animation-delay: -{atraso:.2f}s"' if atraso else ""
    return (f'<g class="voa"{st}><g class="asa1"{st}>{cima}</g><g class="asa2"{st}>{baixo}</g></g>'), sw, sh


def gerar_jornada(d):
    semanas = d["semanas"]
    n = len(semanas)
    cel, gap = 11, 3
    passo = cel + gap
    x0, y0 = 49, 152  # espaço acima da grade para os dragões voarem sem cobrir o texto
    w = 840
    h = y0 + 7 * passo + 34
    T = 18  # segundos de uma travessia
    viagem = 0.9  # fração do ciclo em que os dragões voam
    px = 3

    # brasas: do roxo apagado ao dourado das chamas
    claro = {"NONE": "#2c2347", "FIRST_QUARTILE": "#7a2e9c", "SECOND_QUARTILE": "#d6397f",
             "THIRD_QUARTILE": "#ff7a3d", "FOURTH_QUARTILE": OURO}
    apagado = "#1d1733"
    estilo = []
    for nivel, cor in claro.items():
        estilo.append(
            f"@keyframes acende_{nivel} {{ 0% {{ fill: {apagado}; transform: scale(1) }} "
            f"1% {{ fill: {cor}; transform: scale(1.45) }} 4% {{ fill: {cor}; transform: scale(1) }} "
            f"88% {{ fill: {cor} }} 94%,100% {{ fill: {apagado} }} }}"
        )
        estilo.append(f".n_{nivel} {{ animation: acende_{nivel} {T}s linear infinite backwards; "
                      f"transform-box: fill-box; transform-origin: center; fill: {apagado}; }}")

    preto, sw, sh = dragao("preto", px)
    branco, _, _ = dragao("branco", px, atraso=0.23)
    # a chama sai da boca do dragão preto e cai em cima da coluna que vai acender
    boca_x, boca_y = 22 * px, 10.5 * px
    queda_x, queda_y = 9, 23
    bx = x0 + cel / 2 - boca_x - queda_x
    by = y0 - sh - 2
    distancia = (n - 1) * passo

    estilo += [
        f"@keyframes anda {{ 0% {{ transform: translateX(0) }} {viagem * 100:.0f}% {{ transform: translateX({distancia}px) }} 100% {{ transform: translateX({distancia}px) }} }}",
        f"@keyframes aparece {{ 0% {{ opacity: 0 }} 2% {{ opacity: 1 }} {viagem * 100 - 1:.0f}% {{ opacity: 1 }} {viagem * 100 + 3:.0f}%,100% {{ opacity: 0 }} }}",
        f".bando {{ animation: anda {T}s linear infinite, aparece {T}s linear infinite; }}",
        "@keyframes voa { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-3px) } }",
        ".voa { animation: voa .5s ease-in-out infinite; }",
        "@keyframes asa1 { 0% { opacity: 1 } 50% { opacity: 0 } }",
        "@keyframes asa2 { 0% { opacity: 0 } 50% { opacity: 1 } }",
        ".asa1 { animation: asa1 .5s step-end infinite; }",
        ".asa2 { animation: asa2 .5s step-end infinite; opacity: 0; }",
        "@keyframes paira { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-6px) } }",
        ".paira { animation: paira 2.2s ease-in-out infinite; }",
        f"@keyframes sopro {{ 0% {{ transform: translate(0,0) scale(1); opacity: 0 }} 10% {{ opacity: 1 }} "
        f"100% {{ transform: translate({queda_x}px,{queda_y}px) scale(.35); opacity: 0 }} }}",
        ".chama { transform-box: fill-box; transform-origin: center; opacity: 0; animation: sopro .7s ease-in infinite; }",
        "@keyframes rastro { 0% { transform: translate(0,0) scale(1); opacity: 0 } 15% { opacity: 1 } 100% { transform: translate(-22px,10px) scale(.2); opacity: 0 } }",
        ".brilhinho { transform-box: fill-box; transform-origin: center; opacity: 0; animation: rastro 1.4s ease-out infinite; }",
    ]

    c = [estrelinhas(w, h, 12, 17)]
    total = d["total"]
    c.append(f'<text x="28" y="36" font-size="12" font-weight="800" letter-spacing="3" fill="{OURO}">A JORNADA DOS DRAGÕES</text>')
    c.append(f'<text x="28" y="58" font-size="14" fill="{TEXTO_2}"><tspan fill="{TEXTO}" font-weight="700">{plural(total, "contribuição", "contribuições")}</tspan> '
             f'no último ano · cada dia de código acende com uma baforada de fogo</text>')

    for i, semana in enumerate(semanas):
        atraso = viagem * T * i / max(1, n - 1)
        for dia in semana:
            wd = datetime.strptime(dia["date"], "%Y-%m-%d").weekday()  # seg=0
            linha = (wd + 1) % 7  # domingo no topo, como no GitHub
            c.append(f'<rect class="n_{dia["contributionLevel"]}" style="animation-delay: {atraso:.2f}s" '
                     f'x="{x0 + i * passo}" y="{y0 + linha * passo}" width="{cel}" height="{cel}" rx="2.5"/>')

    chamas = "".join(
        f'<rect class="chama" x="{boca_x:.1f}" y="{boca_y:.1f}" width="{5 - k % 2}" height="{5 - k % 2}" rx="1" fill="{cor}" '
        f'style="animation-delay: {k * 0.14:.2f}s"/>'
        for k, cor in enumerate([OURO, "#ff7a3d", "#fff1b8", ROSA, OURO])
    )
    brilhos = "".join(
        f'<rect class="brilhinho" x="{3 * px:.1f}" y="{(9 + k % 3) * px:.1f}" width="3" height="3" fill="{cor}" '
        f'style="animation-delay: {k * 0.35:.2f}s"/>'
        for k, cor in enumerate([CIANO, "#ffffff", ROSA, CIANO])
    )
    c.append(
        f'<g class="bando">'
        f'<g transform="translate({bx - 44:.1f},{by - 30:.1f})"><g class="paira">{branco}{brilhos}</g></g>'
        f'<g transform="translate({bx:.1f},{by:.1f})">{preto}{chamas}</g>'
        f'</g>'
    )

    legenda_y = y0 + 7 * passo + 20
    c.append(f'<text x="{x0}" y="{legenda_y}" font-size="11" fill="{TEXTO_2}">menos</text>')
    for k, nivel in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]):
        c.append(f'<rect x="{x0 + 40 + k * 15}" y="{legenda_y - 10}" width="11" height="11" rx="2.5" fill="{claro[nivel]}"/>')
    c.append(f'<text x="{x0 + 40 + 5 * 15 + 4}" y="{legenda_y}" font-size="11" fill="{TEXTO_2}">mais</text>')
    c.append(f'<text x="{w - 28}" y="{legenda_y}" text-anchor="end" font-size="11" fill="{TEXTO_2}">'
             f'maior sequência: <tspan fill="{TEXTO}" font-weight="700">{plural(maior_sequencia(d["dias"]), "dia", "dias")}</tspan></text>')
    return moldura(w, h, "\n".join(c), "\n  ".join(estilo))


# ------------------------------------------------------------------ main
def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "banner.svg").write_text(gerar_banner(), encoding="utf-8")
    dados = buscar_dados()
    (SAIDA / "mochila.svg").write_text(gerar_mochila(dados), encoding="utf-8")
    (SAIDA / "jornada.svg").write_text(gerar_jornada(dados), encoding="utf-8")
    (SAIDA / "ficha.svg").unlink(missing_ok=True)  # arte antiga, substituída pela mochila
    print(f"ok: {dados['total']} contribuições, {dados['repos']} repos, linguagens: "
          f"{[n for n, _ in dados['linguagens'][:5]]}")


if __name__ == "__main__":
    main()
