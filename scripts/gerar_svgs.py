"""Gera as artes animadas do README do perfil (tema: Critical Role · Mighty Nein).

- dist/banner.svg   noite em Exandria: as duas luas, Rosohna ao fundo, mini Essek e mini Caleb flutuando
- dist/mochila.svg  bolsa de componentes: linguagens viram poções, números viram recursos e conquistas (com a Jester)
- dist/jornada.svg  mini Caleb e mini Essek atravessam o gráfico de contribuições rumo ao Beacon

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

# Paleta: noite em Rosohna, luz de dunamancia e fogo do Caleb
FUNDO_1, FUNDO_2 = "#140f2a", "#0a1726"
BORDA = "#2c2752"
TEXTO, TEXTO_2 = "#f1eefb", "#a8a2c9"
LAVANDA, ROXO, TEAL = "#b794ff", "#7c4dff", "#7fe3d2"
FOGO, OURO, ROSA, AZUL = "#ff8a3d", "#ffd27a", "#ff7ac8", "#5aa9ff"
FONTE = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
SERIFA = "Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif"
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


# Animações compartilhadas pelos mini personagens
ESTILO_CHIBI = [
    "@keyframes flutua { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-7px) } }",
    ".flutua { animation: flutua 3.2s ease-in-out infinite; }",
    "@keyframes sombra { 0%,100% { transform: scale(1); opacity: .45 } 50% { transform: scale(.78); opacity: .22 } }",
    ".sombra { transform-box: fill-box; transform-origin: center; animation: sombra 3.2s ease-in-out infinite; }",
    "@keyframes capa { 0%,100% { transform: skewX(-4deg) } 50% { transform: skewX(4deg) } }",
    ".capa { transform-box: fill-box; transform-origin: 50% 0; animation: capa 3.6s ease-in-out infinite; }",
    "@keyframes labareda { 0%,100% { transform: scale(1,1) } 30% { transform: scale(.88,1.12) } 60% { transform: scale(1.08,.9) } }",
    ".labareda { transform-box: fill-box; transform-origin: 50% 100%; animation: labareda .7s ease-in-out infinite; }",
    "@keyframes pulsa { 0%,100% { opacity: .45 } 50% { opacity: 1 } }",
    ".pulsa { animation: pulsa 2.6s ease-in-out infinite; }",
    "@keyframes pisca_olho { 0%,94%,100% { transform: scaleY(1) } 97% { transform: scaleY(.1) } }",
    ".olho { transform-box: fill-box; transform-origin: center; animation: pisca_olho 5s infinite; }",
]


def moldura(w, h, conteudo, estilo=""):
    chibi = "\n  ".join(ESTILO_CHIBI)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<defs>
  <linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{FUNDO_1}"/><stop offset="1" stop-color="{FUNDO_2}"/>
  </linearGradient>
  <linearGradient id="arcano" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{FOGO}"/><stop offset=".45" stop-color="{LAVANDA}"/><stop offset="1" stop-color="{TEAL}"/>
  </linearGradient>
  <radialGradient id="brilhoLavanda"><stop offset="0" stop-color="{LAVANDA}" stop-opacity=".55"/><stop offset="1" stop-color="{LAVANDA}" stop-opacity="0"/></radialGradient>
  <radialGradient id="brilhoFogo"><stop offset="0" stop-color="{FOGO}" stop-opacity=".6"/><stop offset="1" stop-color="{FOGO}" stop-opacity="0"/></radialGradient>
  <radialGradient id="brilhoRosa"><stop offset="0" stop-color="{ROSA}" stop-opacity=".5"/><stop offset="1" stop-color="{ROSA}" stop-opacity="0"/></radialGradient>
  <radialGradient id="brilhoTeal"><stop offset="0" stop-color="{TEAL}" stop-opacity=".5"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>
</defs>
<style>
  text {{ font-family: {FONTE}; }}
  .mono {{ font-family: {MONO}; }}
  .serifa {{ font-family: {SERIFA}; }}
  @keyframes pisca {{ 0%,100% {{ opacity: .15 }} 50% {{ opacity: 1 }} }}
  {chibi}
  {estilo}
</style>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="url(#fundo)" stroke="{BORDA}" stroke-width="2"/>
{conteudo}
</svg>
"""


def estrelinhas(w, h, n, semente, topo=14, base=None):
    """Brilhinhos fixos que piscam (posições determinísticas)."""
    base = h - 14 if base is None else base
    out = []
    x = semente
    for i in range(n):
        x = (x * 1103515245 + 12345) % 2147483648
        px = 20 + (x % (w - 40))
        x = (x * 1103515245 + 12345) % 2147483648
        py = topo + (x % max(1, base - topo))
        dur = 2.2 + (i % 5) * 0.6
        cor = TEXTO if i % 4 else TEAL
        out.append(f'<circle cx="{px}" cy="{py}" r="{1 + (i % 3) * 0.5}" fill="{cor}" '
                   f'style="animation: pisca {dur:.1f}s ease-in-out {i * 0.37:.2f}s infinite; opacity:.2"/>')
    return "\n".join(out)


def faisca(x, y, r, cor, atraso=0.0, classe="pulsa"):
    """Estrelinha de quatro pontas."""
    k = r * 0.28
    return (f'<path class="{classe}" style="animation-delay: {atraso:.2f}s" fill="{cor}" '
            f'd="M{x} {y - r} Q{x + k} {y - k} {x + r} {y} Q{x + k} {y + k} {x} {y + r} '
            f'Q{x - k} {y + k} {x - r} {y} Q{x - k} {y - k} {x} {y - r} Z"/>')


def gira(cx, cy, dur, sentido=1):
    fim = 360 * sentido
    return (f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
            f'to="{fim} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>')


def balanca(cx, cy, ang, dur, atraso=0.0):
    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'values="{-ang} {cx} {cy};{ang} {cx} {cy};{-ang} {cx} {cy}" keyTimes="0;.5;1" '
            f'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" dur="{dur}s" begin="-{atraso}s" repeatCount="indefinite"/>')


# ------------------------------------------------------------------ mini personagens
# Desenhados em coordenadas locais: centro da cabeça em (0, 0), uns 150px de altura.

def olhos_e_rosto(cor_olho, brilho="#ffffff", rubor="#ff9ecb", rubor_op=.45):
    return (f'<ellipse cx="-15" cy="11" rx="4.2" ry="2.2" fill="{rubor}" opacity="{rubor_op}"/>'
            f'<ellipse cx="15" cy="11" rx="4.2" ry="2.2" fill="{rubor}" opacity="{rubor_op}"/>'
            f'<g class="olho"><ellipse cx="-9" cy="5.5" rx="3.2" ry="3.9" fill="{cor_olho}"/>'
            f'<circle cx="-8" cy="4" r="1.2" fill="{brilho}"/></g>'
            f'<g class="olho"><ellipse cx="9" cy="5.5" rx="3.2" ry="3.9" fill="{cor_olho}"/>'
            f'<circle cx="10" cy="4" r="1.2" fill="{brilho}"/></g>')


def mini_essek():
    """Essek Thelyss: pele azul-acinzentada, cabelo branco, gola de pelo, capa roxa e o relógio da dunamancia."""
    pele, pele_s = "#8790c2", "#6c74a8"
    cabelo, cabelo_s = "#f0f1fb", "#c3c7e2"
    capa, capa_s = "#3a2d72", "#231a48"
    marcas = "".join(
        f'<line x1="0" y1="-37" x2="0" y2="{-41 if i % 3 else -44}" stroke="{LAVANDA}" stroke-width="{1.4 if i % 3 else 2.2}" '
        f'transform="rotate({i * 30} 0 0)"/>'
        for i in range(12)
    )
    relogio = f"""<g transform="translate(0,10)">
  <circle r="58" fill="url(#brilhoLavanda)" class="pulsa"/>
  <circle r="46" fill="none" stroke="{LAVANDA}" stroke-opacity=".45" stroke-width="1.6" stroke-dasharray="2 5">{gira(0, 0, 40, -1)}</circle>
  <circle r="41" fill="{ROXO}" fill-opacity=".10" stroke="{LAVANDA}" stroke-opacity=".75" stroke-width="1.6"/>
  <circle r="33" fill="none" stroke="{LAVANDA}" stroke-opacity=".35" stroke-width="1"/>
  <g stroke-linecap="round">{marcas}</g>
  <g><line x1="0" y1="0" x2="0" y2="-30" stroke="{LAVANDA}" stroke-width="2" stroke-linecap="round"/><circle cy="-24" r="2.6" fill="none" stroke="{LAVANDA}" stroke-width="1.4"/>{gira(0, 0, 9)}</g>
  <g><line x1="0" y1="0" x2="0" y2="-20" stroke="#e7dcff" stroke-width="2.6" stroke-linecap="round"/>{gira(0, 0, 60)}</g>
  <circle r="3.2" fill="#e7dcff"/>
</g>"""
    gola = "".join(f'<circle cx="{x}" cy="{y + 1.6}" r="{r}" fill="#d6d2ea"/>' for x, y, r in
                   [(-25, 19, 7), (-18, 25, 8.5), (-8, 28.5, 8.5), (0, 29.5, 8.5), (8, 28.5, 8.5), (18, 25, 8.5), (25, 19, 7)])
    gola += "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f7f5fe"/>' for x, y, r in
                    [(-25, 19, 7), (-18, 25, 8.5), (-8, 28.5, 8.5), (0, 29.5, 8.5), (8, 28.5, 8.5), (18, 25, 8.5), (25, 19, 7)])
    return f"""{relogio}
<g class="capa"><path d="M-22 20 C-48 44 -44 88 -16 106 Q0 99 16 106 C44 88 48 44 22 20 Z" fill="{capa_s}"/></g>
<path d="M-15 26 C-18 50 -20 72 -16 88 Q0 94 16 88 C20 72 18 50 15 26 Z" fill="{capa}"/>
<path d="M0 32 V90" stroke="{LAVANDA}" stroke-opacity=".5" stroke-width="1.4"/>
<path d="M-15 30 Q-18 42 -8 48 L-4 44 Q-11 38 -9 28 Z" fill="{capa}" stroke="{capa_s}" stroke-width="1"/>
<path d="M15 30 Q18 42 8 48 L4 44 Q11 38 9 28 Z" fill="{capa}" stroke="{capa_s}" stroke-width="1"/>
<g>
  <line x1="0" y1="46" x2="0" y2="68" stroke="{LAVANDA}" stroke-width="1.6"/>
  <circle cx="0" cy="58" r="2.2" fill="none" stroke="{LAVANDA}" stroke-width="1.3"/>
  <circle cx="0" cy="74" r="6" fill="url(#brilhoLavanda)"/>
  <circle cx="0" cy="74" r="5.2" fill="none" stroke="#e7dcff" stroke-width="1.8"/>
  {balanca(0, 46, 14, 2.6)}
</g>
<circle cx="-5" cy="46" r="3.4" fill="{pele}"/><circle cx="5" cy="46" r="3.4" fill="{pele}"/>
<path d="M-22 22 L-44 10 L-31 29 Z" fill="#cfd2e6" stroke="#9aa0c4" stroke-width="1"/>
<path d="M22 22 L44 10 L31 29 Z" fill="#cfd2e6" stroke="#9aa0c4" stroke-width="1"/>
{gola}
<path d="M-21 0 C-32 -4 -41 -10 -48 -15 C-42 -4 -32 6 -21 9 Z" fill="{pele}"/>
<path d="M-24 2 C-32 -1 -38 -5 -42 -9 C-37 -3 -31 3 -24 6 Z" fill="{pele_s}"/>
<path d="M21 0 C32 -4 41 -10 48 -15 C42 -4 32 6 21 9 Z" fill="{pele}"/>
<path d="M24 2 C32 -1 38 -5 42 -9 C37 -3 31 3 24 6 Z" fill="{pele_s}"/>
<circle cx="-34" cy="5" r="2.6" fill="none" stroke="#dfe2f5" stroke-width="1.2"/>
<circle cx="34" cy="5" r="2.6" fill="none" stroke="#dfe2f5" stroke-width="1.2"/>
<ellipse cx="0" cy="-6" rx="26" ry="22" fill="{cabelo_s}"/>
<ellipse cx="0" cy="0" rx="24" ry="22.5" fill="{pele}"/>
<path d="M-25 2 C-28 -20 -12 -31 3 -30 C20 -29 29 -17 26 2 C24 -6 20 -11 14 -13 C8 -6 -2 -2 -14 -2 C-18 -1 -22 0 -25 2 Z" fill="{cabelo}"/>
<path d="M14 -13 C24 -7 27 6 22 17 C20 6 16 -2 10 -8 Z" fill="{cabelo}"/>
<path d="M-24 0 C-27 8 -25 14 -21 18 C-22 10 -21 4 -18 -1 Z" fill="{cabelo}"/>
<path d="M-6 -26 C-2 -16 2 -10 8 -8 M6 -27 C10 -20 14 -16 18 -12 M-16 -21 C-14 -12 -10 -6 -4 -4" fill="none" stroke="{cabelo_s}" stroke-width="1.1" stroke-linecap="round"/>
<ellipse cx="-15" cy="11" rx="4.2" ry="2.2" fill="#c99be6" opacity=".5"/>
<ellipse cx="15" cy="11" rx="4.2" ry="2.2" fill="#c99be6" opacity=".5"/>
<g class="olho"><ellipse cx="-9" cy="6" rx="3.4" ry="3.2" fill="#f1e9ff"/><circle cx="-8.6" cy="6.3" r="1.5" fill="{ROXO}"/></g>
<g class="olho"><ellipse cx="9" cy="6" rx="3.4" ry="3.2" fill="#f1e9ff"/><circle cx="9.4" cy="6.3" r="1.5" fill="{ROXO}"/></g>
<path d="M-13.2 4 Q-9 1.6 -5 3.6 M5 3.6 Q9 1.6 13.2 4" fill="none" stroke="#2c2356" stroke-width="1.8" stroke-linecap="round"/>
<path d="M-3 14 Q1 15.6 5 12.6" fill="none" stroke="#2c2356" stroke-width="1.4" stroke-linecap="round"/>"""


def mini_caleb():
    """Caleb Widogast: cabelo ruivo bagunçado, barba por fazer, casaco comprido, Frumpkin no ombro e fogo na mão."""
    pele = "#f3d3bb"
    cabelo, cabelo_s, cabelo_l = "#b4502f", "#8f3d27", "#d97a52"
    casaco, casaco_s = "#5d4535", "#4a3529"
    return f"""<path d="M-27 -2 C-31 16 -29 30 -20 36 Q0 40 20 36 C29 30 31 16 27 -2 Z" fill="{cabelo_s}"/>
<path d="M-22 22 L-30 90 Q0 96 30 90 L22 22 Z" fill="{casaco_s}"/>
<path d="M-8 24 L-12 88 L12 88 L8 24 Z" fill="#8b78b8"/>
<path d="M-6 26 L-7 72 L7 72 L6 26 Z" fill="#3b3340"/>
<rect x="-7" y="72" width="5.5" height="16" fill="#2c2733"/><rect x="1.5" y="72" width="5.5" height="16" fill="#2c2733"/>
<rect x="-8.5" y="86" width="8" height="6" rx="2" fill="#3a2a22"/><rect x="0.5" y="86" width="8" height="6" rx="2" fill="#3a2a22"/>
<path d="M-20 24 L-28 88 L-10 88 L-6 26 Z" fill="{casaco}"/>
<path d="M20 24 L28 88 L10 88 L6 26 Z" fill="{casaco}"/>
<rect x="-9" y="56" width="18" height="4" rx="1" fill="#2a2026"/><rect x="-2" y="55.5" width="4" height="5" rx="1" fill="{OURO}" opacity=".8"/>
<path d="M-20 28 Q-28 40 -26 52 L-20 52 Q-20 40 -15 32 Z" fill="{casaco}"/>
<rect x="-31" y="49" width="10" height="12" rx="1.5" fill="#7a2e3a" transform="rotate(-8 -26 55)"/>
<rect x="-29.5" y="50" width="2" height="10" fill="#e9d9b8" transform="rotate(-8 -26 55)"/>
<circle cx="-23" cy="54" r="3.6" fill="{pele}"/>
<path d="M18 28 Q30 30 37 40 L32 45 Q26 38 16 35 Z" fill="{casaco}"/>
<circle cx="35" cy="43" r="3.7" fill="{pele}"/>
<circle cx="36" cy="31" r="15" fill="url(#brilhoFogo)" class="pulsa"/>
<g class="labareda"><path d="M36 18 C43 26 44 33 40.5 37.5 Q36 41.5 31.5 37.5 C28 33 30 26 36 18 Z" fill="{FOGO}"/>
<path d="M36 26 C39.5 30 40 34 38 36.5 Q36 38.5 34 36.5 C32 34 33 30 36 26 Z" fill="{OURO}"/></g>
<path d="M-17 18 Q0 28 17 18 L17 26 Q0 34 -17 26 Z" fill="#6e6488"/>
<path d="M6 26 L12 46 L4 47 L1 28 Z" fill="#5f5679"/>
<ellipse cx="0" cy="0" rx="24" ry="22.5" fill="{pele}"/>
<path d="M-19 8 C-14 22 14 22 19 8 C16 18 8 23 0 23 C-8 23 -16 18 -19 8 Z" fill="#b5634a" opacity=".3"/>
<path d="M-26 4 C-30 -18 -14 -31 2 -31 C20 -31 31 -18 26 4 L22 -5 L19 3 L15 -9 L9 -1 L4 -12 L-2 -2 L-8 -11 L-12 1 L-17 -7 L-21 5 Z" fill="{cabelo}"/>
<path d="M-26 2 C-29 12 -27 22 -21 28 C-22 18 -21 10 -19 2 Z" fill="{cabelo}"/>
<path d="M26 2 C29 12 27 22 21 28 C22 18 21 10 19 2 Z" fill="{cabelo}"/>
<path d="M-10 -26 C-14 -20 -16 -14 -17 -9 M4 -28 C2 -22 1 -18 0 -13 M14 -25 C16 -20 17 -14 17 -10" fill="none" stroke="{cabelo_l}" stroke-width="1.2" stroke-linecap="round"/>
<path d="M-13 0 Q-9 -2.2 -5 -0.6 M5 -0.6 Q9 -2.2 13 0" fill="none" stroke="{cabelo_s}" stroke-width="1.5" stroke-linecap="round"/>
{olhos_e_rosto("#2e3a5c")}
<path d="M-3 13.5 Q0 15.8 3 13.5" fill="none" stroke="#6b3a2c" stroke-width="1.4" stroke-linecap="round"/>
<g>
  <path d="M-15 19 C-8 14 -8 7 -12 4" fill="none" stroke="#e8913f" stroke-width="3.2" stroke-linecap="round">{balanca(-15, 19, 10, 2.2)}</path>
  <ellipse cx="-24" cy="19" rx="9.5" ry="6.2" fill="#e8913f"/>
  <path d="M-26 14 v9 M-22 13.5 v9 M-18 15 v7" stroke="#b8612a" stroke-width="1.3" stroke-linecap="round"/>
  <path d="M-36.5 7 L-37 -1 L-31.5 4 Z" fill="#ef9a48"/><path d="M-28.5 4 L-25.5 -2.5 L-24.5 5 Z" fill="#ef9a48"/>
  <circle cx="-30.5" cy="10" r="6.8" fill="#ef9a48"/>
  <path d="M-33 5 l1 3 M-30.5 4.2 v3 M-28 5 l-1 3" stroke="#b8612a" stroke-width="1.1" stroke-linecap="round"/>
  <path d="M-34 10.5 q1.4 1.2 2.8 0 M-29.2 10.5 q1.4 1.2 2.8 0" fill="none" stroke="#5a2e12" stroke-width="1" stroke-linecap="round"/>
  <path d="M-31.4 13 l.9 .8 l.9 -.8 Z" fill="#ff9ecb"/>
</g>"""


def mini_jester():
    """Jester Lavorre: tiefling azul, chifrinhos, sardas, pirulito gigante e muito brilho."""
    pele, pele_s = "#78aef0", "#5f97dc"
    cabelo, cabelo_s = "#2f66cf", "#234fa6"
    return f"""<path d="M10 70 C30 78 38 62 31 53" fill="none" stroke="{pele_s}" stroke-width="3" stroke-linecap="round">{balanca(10, 70, 8, 1.8)}</path>
<path d="M-26 0 C-30 18 -28 28 -22 32 Q0 30 22 32 C28 28 30 18 26 0 Z" fill="{cabelo_s}"/>
<rect x="-9" y="70" width="5" height="14" fill="{pele}"/><rect x="4" y="70" width="5" height="14" fill="{pele}"/>
<rect x="-10.5" y="81" width="8" height="8" rx="2" fill="#6b3d2e"/><rect x="2.5" y="81" width="8" height="8" rx="2" fill="#6b3d2e"/>
<path d="M-14 24 L-15 50 L15 50 L14 24 Z" fill="#2f6a55"/>
<path d="M-15 48 L-25 72 Q0 79 25 72 L15 48 Z" fill="#3a7d63"/>
<path d="M-25 72 Q0 79 25 72" fill="none" stroke="{ROSA}" stroke-width="2.2"/>
<rect x="-15" y="46" width="30" height="5" rx="1.5" fill="#f2b84b"/>
<path d="M-18 22 Q0 34 18 22 L22 34 Q0 44 -22 34 Z" fill="#24553f"/>
<g>
  <path d="M-14 28 Q-28 24 -35 11 L-31 9 Q-25 20 -12 24 Z" fill="{pele}"/>
  <circle cx="-34" cy="8" r="3.8" fill="{pele}"/>
  {balanca(-13, 27, 12, 1.1)}
</g>
<path d="M14 28 Q24 34 26 42 L22 44 Q20 38 12 34 Z" fill="{pele}"/>
<line x1="25" y1="44" x2="34" y2="20" stroke="#f6f2ff" stroke-width="2" stroke-linecap="round"/>
<circle cx="25" cy="44" r="3.8" fill="{pele}"/>
<circle cx="35" cy="13" r="13" fill="url(#brilhoRosa)" class="pulsa"/>
<circle cx="35" cy="13" r="8.5" fill="{ROSA}"/>
<path d="M35 13 m0 -6 a6 6 0 1 1 -5.5 3.5 a4 4 0 1 1 3.6 -1.4 a2 2 0 1 1 1.9 .6" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round">{gira(35, 13, 6)}</path>
<ellipse cx="0" cy="0" rx="24" ry="22.5" fill="{pele}"/>
<path d="M-13 -18 C-20 -30 -14 -39 -5 -37 C-11 -32 -12 -26 -8 -20 Z" fill="#7b6aa8"/>
<path d="M13 -18 C20 -30 14 -39 5 -37 C11 -32 12 -26 8 -20 Z" fill="#7b6aa8"/>
<path d="M-26 6 C-30 -18 -12 -30 2 -30 C20 -30 31 -18 26 6 C22 0 20 -6 18 -10 C12 -4 4 -6 0 -12 C-4 -6 -12 -4 -18 -10 C-20 -4 -22 0 -26 6 Z" fill="{cabelo}"/>
<circle cx="-29" cy="21" r="6.5" fill="{cabelo}"/><circle cx="29" cy="21" r="6.5" fill="{cabelo}"/>
<rect x="-31" y="12.5" width="5" height="3" rx="1.2" fill="{ROSA}"/><rect x="26" y="12.5" width="5" height="3" rx="1.2" fill="{ROSA}"/>
<g fill="#4f86d4"><circle cx="-16" cy="9.5" r=".9"/><circle cx="-13" cy="11.5" r=".9"/><circle cx="-18" cy="12" r=".9"/>
<circle cx="16" cy="9.5" r=".9"/><circle cx="13" cy="11.5" r=".9"/><circle cx="18" cy="12" r=".9"/></g>
<ellipse cx="-14" cy="13" rx="4" ry="2" fill="{ROSA}" opacity=".45"/><ellipse cx="14" cy="13" rx="4" ry="2" fill="{ROSA}" opacity=".45"/>
<g class="olho"><ellipse cx="-9" cy="4.5" rx="3.7" ry="4.6" fill="#4a2a7a"/><circle cx="-7.8" cy="2.8" r="1.4" fill="#fff"/><circle cx="-10" cy="6.6" r=".7" fill="#fff"/></g>
<g class="olho"><ellipse cx="9" cy="4.5" rx="3.7" ry="4.6" fill="#4a2a7a"/><circle cx="10.2" cy="2.8" r="1.4" fill="#fff"/><circle cx="8" cy="6.6" r=".7" fill="#fff"/></g>
<path d="M-5 12 Q0 19.5 5 12 Z" fill="#3a1f4a"/><path d="M-2.4 15.6 Q0 14 2.4 15.6 Q0 17.6 -2.4 15.6 Z" fill="{ROSA}"/>"""


def personagem(desenho, x, y, escala=1.0, atraso=0.0, sombra_cor=LAVANDA, sombra_y=112):
    """Posiciona um mini personagem flutuando, com a sombrinha brilhante embaixo."""
    st = f' style="animation-delay: -{atraso:.2f}s"'
    sombra = ""
    if sombra_cor:
        sombra = f'<ellipse class="sombra"{st} cx="0" cy="{sombra_y}" rx="22" ry="4.5" fill="{sombra_cor}"/>'
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({escala})">{sombra}'
            f'<g class="flutua"{st}>{desenho}</g></g>')


def beacon(x, y, r, classe="pulsa"):
    """O Beacon da Luxon: um dodecaedro brilhante visto de frente."""
    def pt(raio, ang):
        a = math.radians(ang - 90)
        return x + raio * math.cos(a), y + raio * math.sin(a)
    externo = [pt(r, 36 * k) for k in range(10)]
    interno = [pt(r * 0.5, 72 * k) for k in range(5)]
    faces = []
    for k in range(5):
        a, b = interno[k], interno[(k + 1) % 5]
        o1, o2, o3 = externo[2 * k], externo[2 * k + 1], externo[(2 * k + 2) % 10]
        pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in (a, o1, o2, o3, b))
        faces.append(f'<polygon points="{pts}" fill="{LAVANDA}" fill-opacity="{.28 + .12 * (k % 3):.2f}" stroke="#efe6ff" stroke-width="1.1" stroke-linejoin="round"/>')
    centro = " ".join(f"{px:.1f},{py:.1f}" for px, py in interno)
    return (f'<circle cx="{x}" cy="{y}" r="{r * 2.6:.1f}" fill="url(#brilhoLavanda)" class="{classe}"/>'
            f'<g>{"".join(faces)}<polygon points="{centro}" fill="#efe6ff" fill-opacity=".85" stroke="#efe6ff" stroke-width="1.1" stroke-linejoin="round"/></g>')


# ------------------------------------------------------------------ banner
def cidade(w, base, semente=3):
    """Silhueta de Rosohna: torres pontudas, mais baixas no centro para não brigar com o texto."""
    partes, janelas = [], []
    x = 0
    s = semente
    i = 0
    while x < w:
        s = (s * 1103515245 + 12345) % 2147483648
        larg = 14 + s % 22
        dist_centro = abs((x + larg / 2) - w / 2) / (w / 2)
        alt = 10 + dist_centro * 46 + (s >> 8) % 18
        topo = base - alt
        ponta = 10 + (s >> 4) % 22
        partes.append(f"M{x} {base} V{topo:.0f} L{x + larg / 2:.1f} {topo - ponta:.0f} L{x + larg} {topo:.0f} V{base} Z")
        if alt > 24 and i % 2 == 0:
            for j in range(int(alt // 16)):
                jy = topo + 7 + j * 13
                janelas.append(f'<rect x="{x + larg / 2 - 1.5:.1f}" y="{jy:.0f}" width="3" height="5" rx="1" fill="{TEAL}" '
                               f'style="animation: pisca {2.5 + (i + j) % 4:.1f}s ease-in-out {(i * .41 + j * .9) % 4:.2f}s infinite; opacity:.3"/>')
        x += larg + (s >> 12) % 6
        i += 1
    return (f'<path d="{" ".join(partes)}" fill="#1d1640"/>' + "".join(janelas))


def gerar_banner():
    w, h = 840, 260
    frases = [
        "Ciência da Computação · UNIFAL-MG",
        "Front-end, interfaces e game dev",
        "Mestre de RPG nas horas vagas",
        "Fã de Critical Role · Mighty Nein",
    ]
    ciclo = 16
    fatia = ciclo / len(frases)
    estilo = [
        "@keyframes cursor { 0%,100% { opacity: 1 } 50% { opacity: .25 } }",
        ".cursor { animation: cursor 2.4s ease-in-out infinite; }",
        "@keyframes ruidus { 0%,100% { opacity: .55 } 50% { opacity: 1 } }",
        ".ruidus { animation: ruidus 4s ease-in-out infinite; }",
        "@keyframes nevoa { from { transform: translateX(0) } to { transform: translateX(-120px) } }",
        ".nevoa { animation: nevoa 14s linear infinite alternate; }",
    ]
    c = [estrelinhas(w, h, 34, 7, base=200)]

    # as duas luas de Exandria: Catha (crescente) e a pequena e vermelha Ruidus
    c.append(f'<defs><mask id="crescente"><rect width="{w}" height="{h}" fill="#fff"/><circle cx="630" cy="40" r="19" fill="#000"/></mask></defs>'
             f'<circle cx="622" cy="46" r="40" fill="url(#brilhoTeal)"/>'
             f'<circle cx="622" cy="46" r="20" fill="#dff7f1" mask="url(#crescente)"/>'
             f'<circle class="ruidus" cx="248" cy="38" r="9" fill="#ff5a5a" opacity=".25"/>'
             f'<circle class="ruidus" cx="248" cy="38" r="4.5" fill="#c9424b"/>')

    c.append(cidade(w, h - 2))
    c.append(f'<defs><linearGradient id="bruma" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/>'
             f'<stop offset="1" stop-color="{TEAL}" stop-opacity=".22"/></linearGradient>'
             f'<clipPath id="moldura"><rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="13"/></clipPath></defs>'
             f'<g clip-path="url(#moldura)"><rect class="nevoa" x="0" y="{h - 70}" width="{w + 120}" height="70" fill="url(#bruma)"/></g>')

    # nome e subtítulo digitando, centralizados
    c.append(f'<text class="serifa" x="{w / 2}" y="104" text-anchor="middle" font-size="40" font-weight="700" fill="{TEXTO}" letter-spacing=".5">{esc(NOME)}</text>')
    c.append(f'<rect x="{w / 2 - 150}" y="118" width="300" height="3" rx="1.5" fill="url(#arcano)"/>')
    c.append(faisca(w / 2 - 162, 119.5, 6, LAVANDA) + faisca(w / 2 + 162, 119.5, 6, TEAL, 1.3))
    for i, frase in enumerate(frases):
        ini = i * fatia / ciclo * 100
        fim = (i + 1) * fatia / ciclo * 100
        dig = ini + (fatia * 0.45) / ciclo * 100
        larg = len(frase) * 11 + 4
        x_ini = w / 2 - larg / 2
        estilo.append(
            f"@keyframes digita{i} {{ 0%,{ini:.2f}% {{ width: 0 }} {dig:.2f}%,{fim - 1.5:.2f}% {{ width: {larg:.0f}px }} {fim:.2f}%,100% {{ width: 0 }} }}"
        )
        estilo.append(f".clip{i} {{ animation: digita{i} {ciclo}s steps({len(frase)}) infinite; }}")
        c.append(
            f'<clipPath id="c{i}"><rect class="clip{i}" x="{x_ini:.0f}" y="136" height="34" width="0"/></clipPath>'
            f'<text clip-path="url(#c{i})" x="{x_ini + 2:.0f}" y="160" font-size="20" class="mono" fill="{TEXTO_2}">{esc(frase)}</text>'
        )
    c.append(f'<text class="cursor serifa" x="{w / 2}" y="196" text-anchor="middle" font-size="14" font-style="italic" fill="{LAVANDA}">'
             f'✦ já é quinta-feira? ✦</text>')

    # mini Essek flutuando à esquerda, mini Caleb à direita
    c.append(personagem(mini_essek(), 112, 92, 0.92, 0, LAVANDA, 116))
    c.append(personagem(mini_caleb(), 732, 104, 0.92, 1.4, FOGO, 104))
    for k, (fx, fy, cor) in enumerate([(52, 70, LAVANDA), (178, 168, TEAL), (790, 56, OURO), (668, 176, FOGO), (186, 54, "#ffffff")]):
        c.append(faisca(fx, fy, 4 + k % 2 * 2, cor, k * 0.7))

    return moldura(w, h, "\n".join(c), "\n  ".join(estilo))


# ------------------------------------------------------------------ mochila
def icone_moeda(x, y):
    return (f'<g transform="translate({x},{y})"><circle r="10" fill="{OURO}"/><circle r="6.5" fill="none" stroke="#b8862b" stroke-width="1.6"/>'
            f'<rect x="-1.5" y="-4" width="3" height="8" rx="1" fill="#b8862b"/><circle cx="-4" cy="-5" r="1.6" fill="#fff6d6"/></g>')


def icone_grimorio(x, y):
    return (f'<g transform="translate({x},{y})"><rect x="-9" y="-10" width="18" height="20" rx="2" fill="#7a2e3a"/>'
            f'<rect x="-9" y="-10" width="4" height="20" rx="1.5" fill="#5a1f2a"/>'
            f'<rect x="7" y="-8.5" width="2.5" height="17" fill="#efe1c2"/>'
            f'<path d="M2 -5 l1.3 3 3 .4 -2.3 2 .6 3 -2.6 -1.5 -2.6 1.5 .6 -3 -2.3 -2 3 -.4 Z" fill="{OURO}"/></g>')


def icone_beacon(x, y):
    return beacon(x, y, 9, classe="")


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
    c.append(f'<text x="28" y="40" font-size="12" font-weight="700" letter-spacing="4" fill="{LAVANDA}" class="brilho">BOLSA DE COMPONENTES</text>')
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
        c.append(f'<text x="28" y="150" font-size="13" fill="{TEXTO_2}">A bolsa ainda está vazia.</text>')

    # recursos
    recursos = [
        (icone_moeda, "Peças de ouro (commits)", d["commits"]),
        (icone_grimorio, "Páginas do grimório (repositórios)", d["repos"]),
        (icone_beacon, "Fragmentos de dunamis (PRs e issues)", d["prs_issues"]),
        (icone_estrela, "Renome (estrelas e seguidores)", fama),
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

    # a Jester empoleirada em cima da bolsa, acenando com o pirulito
    c.append(f'<g class="surge" style="animation-delay: .9s">{personagem(mini_jester(), 714, 30, 0.6, 0.6, None)}</g>')
    for k, (fx, fy) in enumerate([(664, 30), (768, 20), (676, 68)]):
        c.append(faisca(fx, fy, 3.5 + k % 2 * 1.5, ROSA, k * 0.8))

    # conquistas (desbloqueiam com os números reais)
    conquistas = [
        ("Sessão zero", "1 repositório", d["repos"], 1),
        ("Linguista", "5 linguagens", n_ling, 5),
        ("Cobalt Soul", "10 repositórios", d["repos"], 10),
        ("Já é quinta?", "7 dias seguidos", seq, 7),
        ("Mighty Nein", "10 PRs ou issues", d["prs_issues"], 10),
        ("Dunamancia", "100 contribuições", total, 100),
    ]
    feitas = sum(1 for *_, v, meta in conquistas if v >= meta)
    c.append(f'<text x="28" y="246" font-size="12" font-weight="800" letter-spacing="3" fill="{LAVANDA}">CONQUISTAS</text>'
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
                      f'<rect class="progresso" x="{x + 44}" y="{y + 48}" width="{max(3, 40 * frac):.0f}" height="5" rx="2.5" fill="url(#arcano)"/>'
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
    c.append(f'<text x="{w - 28}" y="{h - 12}" text-anchor="end" font-size="10.5" fill="{TEXTO_2}">atualizada em {hoje}</text>')
    return moldura(w, h, "\n".join(c), "\n  ".join(estilo))


# ------------------------------------------------------------------ jornada
def gerar_jornada(d):
    semanas = d["semanas"]
    n = len(semanas)
    cel, gap = 11, 3
    passo = cel + gap
    x0, y0 = 49, 160  # espaço acima da grade para os dois voarem sem cobrir o texto
    w = 840
    h = y0 + 7 * passo + 34
    T = 18  # segundos de uma travessia
    viagem = 0.9  # fração do ciclo em que eles voam

    # cada dia acende: do roxo apagado à luz da dunamancia, ao fogo e ao dourado
    claro = {"NONE": "#261f42", "FIRST_QUARTILE": "#4d2f8f", "SECOND_QUARTILE": "#8b5cf6",
             "THIRD_QUARTILE": "#f08a4b", "FOURTH_QUARTILE": OURO}
    apagado = "#1b1634"
    estilo = []
    for nivel, cor in claro.items():
        estilo.append(
            f"@keyframes acende_{nivel} {{ 0% {{ fill: {apagado}; transform: scale(1) }} "
            f"1% {{ fill: {cor}; transform: scale(1.45) }} 4% {{ fill: {cor}; transform: scale(1) }} "
            f"88% {{ fill: {cor} }} 94%,100% {{ fill: {apagado} }} }}"
        )
        estilo.append(f".n_{nivel} {{ animation: acende_{nivel} {T}s linear infinite backwards; "
                      f"transform-box: fill-box; transform-origin: center; fill: {apagado}; }}")

    # o Caleb vai na frente; a faísca sai da mão dele e cai em cima da coluna que vai acender
    esc_c, esc_e = 0.58, 0.5
    mao_x, mao_y = 36 * esc_c, 22 * esc_c
    cy_c = y0 - 10 - 92 * esc_c
    queda_x = 10
    queda_y = y0 - (cy_c + mao_y) + 2
    cx_c = x0 + cel / 2 - mao_x - queda_x
    cx_e, cy_e = cx_c - 66, cy_c - 14
    distancia = (n - 1) * passo

    estilo += [
        f"@keyframes anda {{ 0% {{ transform: translateX(0) }} {viagem * 100:.0f}% {{ transform: translateX({distancia}px) }} 100% {{ transform: translateX({distancia}px) }} }}",
        f"@keyframes aparece {{ 0% {{ opacity: 0 }} 2% {{ opacity: 1 }} {viagem * 100 - 1:.0f}% {{ opacity: 1 }} {viagem * 100 + 3:.0f}%,100% {{ opacity: 0 }} }}",
        f".bando {{ animation: anda {T}s linear infinite, aparece {T}s linear infinite; }}",
        f"@keyframes cai {{ 0% {{ transform: translate(0,0) scale(1); opacity: 0 }} 10% {{ opacity: 1 }} "
        f"100% {{ transform: translate({queda_x}px,{queda_y:.0f}px) scale(.35); opacity: 0 }} }}",
        ".brasa { transform-box: fill-box; transform-origin: center; opacity: 0; animation: cai .7s ease-in infinite; }",
        "@keyframes rastro { 0% { transform: translate(0,0) scale(1); opacity: 0 } 15% { opacity: 1 } 100% { transform: translate(-26px,12px) scale(.2); opacity: 0 } }",
        ".rastro { transform-box: fill-box; transform-origin: center; opacity: 0; animation: rastro 1.4s ease-out infinite; }",
        "@keyframes facho { 0%,100% { opacity: .10 } 50% { opacity: .22 } }",
        ".facho { animation: facho 3s ease-in-out infinite; }",
    ]

    c = [estrelinhas(w, h, 12, 17)]
    total = d["total"]
    c.append(f'<text x="28" y="36" font-size="12" font-weight="800" letter-spacing="3" fill="{LAVANDA}">ENTRE O IMPÉRIO E A DINASTIA</text>')
    c.append(f'<text x="28" y="58" font-size="14" fill="{TEXTO_2}"><tspan fill="{TEXTO}" font-weight="700">{plural(total, "contribuição", "contribuições")}</tspan> '
             f'no último ano · cada dia de código acende com uma faísca de magia</text>')

    # o Beacon no fim do caminho, iluminando a grade
    bx, by = 806, 44
    c.append(f'<defs><linearGradient id="luz" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{LAVANDA}" stop-opacity=".9"/>'
             f'<stop offset="1" stop-color="{LAVANDA}" stop-opacity="0"/></linearGradient></defs>'
             f'<polygon class="facho" points="{bx - 6},{by + 10} {bx + 6},{by + 10} {bx + 22},{y0 + 7 * passo} {x0 + (n - 9) * passo},{y0 + 7 * passo}" fill="url(#luz)"/>')
    c.append(beacon(bx, by, 13))

    for i, semana in enumerate(semanas):
        atraso = viagem * T * i / max(1, n - 1)
        for dia in semana:
            wd = datetime.strptime(dia["date"], "%Y-%m-%d").weekday()  # seg=0
            linha = (wd + 1) % 7  # domingo no topo, como no GitHub
            c.append(f'<rect class="n_{dia["contributionLevel"]}" style="animation-delay: {atraso:.2f}s" '
                     f'x="{x0 + i * passo}" y="{y0 + linha * passo}" width="{cel}" height="{cel}" rx="2.5"/>')

    brasas = "".join(
        f'<rect class="brasa" x="{cx_c + mao_x - 2:.1f}" y="{cy_c + mao_y - 2:.1f}" width="{5 - k % 2}" height="{5 - k % 2}" rx="1.2" fill="{cor}" '
        f'style="animation-delay: {k * 0.14:.2f}s"/>'
        for k, cor in enumerate([OURO, FOGO, "#fff1b8", ROSA, OURO])
    )
    rastro = "".join(
        f'<rect class="rastro" x="{cx_e - 10 + (k % 2) * 6:.1f}" y="{cy_e + 30 + (k % 3) * 5:.1f}" width="3" height="3" rx="1" fill="{cor}" '
        f'style="animation-delay: {k * 0.35:.2f}s"/>'
        for k, cor in enumerate([LAVANDA, "#ffffff", TEAL, LAVANDA])
    )
    c.append(
        f'<g class="bando">{rastro}'
        f'{personagem(mini_essek(), cx_e, cy_e, esc_e, 0.9, None)}'
        f'{personagem(mini_caleb(), cx_c, cy_c, esc_c, 0, None)}'
        f'{brasas}</g>'
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
    print(f"ok: {dados['total']} contribuições, {dados['repos']} repos, linguagens: "
          f"{[n for n, _ in dados['linguagens'][:5]]}")


if __name__ == "__main__":
    main()
