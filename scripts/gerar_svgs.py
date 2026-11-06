"""Gera as artes animadas do README do perfil (tema: RPG + música pop).

- dist/banner.svg   cabeçalho com d20 rolando, equalizador e subtítulo digitando
- dist/ficha.svg    ficha de personagem estilo D&D com os dados reais do GitHub
- dist/jornada.svg  um bardo atravessa o gráfico de contribuições acendendo notas

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


# ------------------------------------------------------------------ ficha
def atributo(valor, referencia):
    """Converte um número real numa nota de 3 a 20 (escala logarítmica)."""
    nota = 8 + 12 * math.log1p(valor) / math.log1p(referencia)
    return max(3, min(20, round(nota)))


def gerar_ficha(d):
    w, h = 840, 330
    total = d["total"]
    nivel = 1 + int(math.sqrt(total / 5))
    xp_atual = 5 * (nivel - 1) ** 2
    xp_prox = 5 * nivel ** 2
    frac = (total - xp_atual) / max(1, xp_prox - xp_atual)

    seq = maior_sequencia(d["dias"])
    n_ling = len(d["linguagens"])
    atrs = [
        ("FOR", atributo(d["commits"], 1500), plural(d["commits"], "commit", "commits")),
        ("DES", atributo(d["prs_issues"], 150), plural(d["prs_issues"], "PR ou issue", "PRs e issues")),
        ("CON", atributo(seq, 100), plural(seq, "dia seguido", "dias seguidos")),
        ("INT", atributo(d["repos"], 40), plural(d["repos"], "repositório", "repositórios")),
        ("SAB", atributo(n_ling, 12), plural(n_ling, "linguagem", "linguagens")),
        ("CAR", atributo(d["seguidores"] + d["estrelas"], 100), plural(d["seguidores"] + d["estrelas"], "fã ou estrela", "fãs e estrelas")),
    ]

    estilo = [
        f"@keyframes enche {{ from {{ width: 0 }} to {{ width: {max(4, 300 * frac):.0f}px }} }}",
        ".xp { animation: enche 2.2s cubic-bezier(.2,.8,.2,1) forwards; width: 0; }",
        "@keyframes surge { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }",
        ".atr { opacity: 0; animation: surge .6s ease-out forwards; }",
        "@keyframes cresce { from { transform: scaleX(0) } to { transform: scaleX(1) } }",
        ".pericia { transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: cresce 1.4s cubic-bezier(.2,.8,.2,1) forwards; }",
        "@keyframes brilho { 0%,100% { opacity: .55 } 50% { opacity: 1 } }",
        ".brilho { animation: brilho 2.4s ease-in-out infinite; }",
    ]
    c = [estrelinhas(w, h, 14, 99)]
    c.append(f'<text x="28" y="40" font-size="12" font-weight="700" letter-spacing="4" fill="{OURO}" class="brilho">FICHA DE PERSONAGEM</text>')
    c.append(f'<text x="28" y="74" font-size="26" font-weight="800" fill="{TEXTO}">{esc(NOME)}</text>')
    c.append(f'<text x="28" y="98" font-size="14" fill="{TEXTO_2}">Classe: <tspan fill="{ROSA}" font-weight="700">Bardo do Código</tspan>'
             f'  ·  Antecedente: <tspan fill="{CIANO}" font-weight="700">Estudante da UNIFAL</tspan>'
             f'  ·  Alinhamento: <tspan fill="{OURO}" font-weight="700">Caótico Criativo</tspan></text>')

    # nível + XP
    c.append(f'<g transform="translate(610,26)">'
             f'<rect width="202" height="76" rx="10" fill="{ROXO}" fill-opacity=".15" stroke="{ROXO}" stroke-opacity=".6"/>'
             f'<text x="16" y="28" font-size="12" letter-spacing="2" fill="{TEXTO_2}">NÍVEL</text>'
             f'<text x="16" y="62" font-size="34" font-weight="800" fill="{TEXTO}">{nivel}</text>'
             f'<text x="186" y="62" text-anchor="end" font-size="12" fill="{TEXTO_2}">{total} XP no ano</text></g>')
    c.append(f'<text x="28" y="128" font-size="12" fill="{TEXTO_2}">XP</text>'
             f'<rect x="56" y="118" width="300" height="12" rx="6" fill="{BORDA}"/>'
             f'<rect class="xp" x="56" y="118" height="12" rx="6" fill="url(#pop)"/>'
             f'<text x="366" y="128" font-size="12" fill="{TEXTO_2}">{xp_prox - total} XP para o nível {nivel + 1}</text>')

    # atributos
    for i, (sig, nota, real) in enumerate(atrs):
        x = 28 + i * 132
        mod = (nota - 10) // 2
        mod_s = f"+{mod}" if mod >= 0 else str(mod)
        # posição no <g> de fora; animação no de dentro (transform do CSS sobrescreve o do SVG)
        c.append(f'<g transform="translate({x},150)"><g class="atr" style="animation-delay: {0.2 + i * 0.12:.2f}s">'
                 f'<rect width="120" height="92" rx="12" fill="{FUNDO_1}" stroke="{BORDA}" stroke-width="2"/>'
                 f'<text x="60" y="22" text-anchor="middle" font-size="12" font-weight="800" letter-spacing="2" fill="{OURO}">{sig}</text>'
                 f'<text x="60" y="56" text-anchor="middle" font-size="30" font-weight="800" fill="{TEXTO}">{nota}</text>'
                 f'<text x="60" y="74" text-anchor="middle" font-size="12" font-weight="700" fill="{ROSA}">{mod_s}</text>'
                 f'<text x="60" y="88" text-anchor="middle" font-size="9.5" fill="{TEXTO_2}">{esc(real)}</text></g></g>')

    # perícias = linguagens
    c.append(f'<text x="28" y="270" font-size="12" font-weight="800" letter-spacing="3" fill="{OURO}">PERÍCIAS</text>')
    soma = sum(v for _, v in d["linguagens"]) or 1
    top = d["linguagens"][:4]
    for i, (nome, bytes_) in enumerate(top):
        x = 130 + i * 172
        pct = bytes_ / soma
        cor = d["cores"].get(nome, ROXO)
        c.append(f'<text x="{x}" y="270" font-size="13" font-weight="700" fill="{TEXTO}">{esc(nome)}'
                 f'<tspan fill="{TEXTO_2}" font-weight="400"> {pct * 100:.0f}%</tspan></text>'
                 f'<rect x="{x}" y="280" width="150" height="8" rx="4" fill="{BORDA}"/>'
                 f'<rect class="pericia" style="animation-delay: {0.6 + i * 0.15:.2f}s" x="{x}" y="280" '
                 f'width="{max(6, 150 * pct):.0f}" height="8" rx="4" fill="{cor}"/>')

    hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    c.append(f'<text x="{w - 28}" y="{h - 16}" text-anchor="end" font-size="10.5" fill="{TEXTO_2}">'
             f'atributos calculados dos dados públicos do GitHub · atualizada em {hoje}</text>')
    return moldura(w, h, "\n".join(c), "\n  ".join(estilo))


# ------------------------------------------------------------------ jornada
BARDO = [
    "....pp......",
    "...hhhp.....",
    "..hhhhhh....",
    "...ssss.....",
    "...sese.....",
    "...ssss.....",
    "..cttttc....",
    ".cttttttc.ll",
    ".ctttttllll.",
    ".cttttllll..",
    "..tttt.ll...",
    "..tttt......",
    "..bb..bb....",
    "..bb..bb....",
    ".bbb..bbb...",
]
CORES_BARDO = {"p": ROSA, "h": ROXO, "s": "#f2c9a0", "e": "#1a1030", "c": "#5b2fa8",
               "t": CIANO, "l": OURO, "b": "#6b4a2f"}


def sprite_bardo(px=2.4):
    rects = []
    for y, linha in enumerate(BARDO):
        for x, ch in enumerate(linha):
            if ch in CORES_BARDO:
                rects.append(f'<rect x="{x * px:.1f}" y="{y * px:.1f}" width="{px + 0.2:.1f}" height="{px + 0.2:.1f}" fill="{CORES_BARDO[ch]}"/>')
    return "".join(rects), len(BARDO[0]) * px, len(BARDO) * px


def gerar_jornada(d):
    semanas = d["semanas"]
    n = len(semanas)
    cel, gap = 11, 3
    passo = cel + gap
    x0, y0 = 49, 108  # espaço acima da grade para o bardo andar sem cobrir o texto
    w = 840
    h = y0 + 7 * passo + 34
    T = 16  # segundos de uma travessia
    viagem = 0.9  # fração do ciclo em que o bardo anda

    claro = {"NONE": "#2c2347", "FIRST_QUARTILE": ROXO, "SECOND_QUARTILE": ROSA,
             "THIRD_QUARTILE": CIANO, "FOURTH_QUARTILE": OURO}
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
    estilo += [
        f"@keyframes anda {{ 0% {{ transform: translateX(0) }} {viagem * 100:.0f}% {{ transform: translateX({(n - 1) * passo}px) }} 100% {{ transform: translateX({(n - 1) * passo}px) }} }}",
        f"@keyframes aparece {{ 0% {{ opacity: 0 }} 2% {{ opacity: 1 }} {viagem * 100 - 1:.0f}% {{ opacity: 1 }} {viagem * 100 + 3:.0f}%,100% {{ opacity: 0 }} }}",
        f".bardo {{ animation: anda {T}s linear infinite, aparece {T}s linear infinite; }}",
        "@keyframes pula { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-3px) } }",
        ".passo { animation: pula .35s ease-in-out infinite; }",
        "@keyframes sobe { 0% { opacity: 0; transform: translate(0,0) } 20% { opacity: 1 } 100% { opacity: 0; transform: translate(-10px,-34px) } }",
        ".som { opacity: 0; animation: sobe 1.6s ease-out infinite; }",
    ]

    c = [estrelinhas(w, h, 10, 3)]
    total = d["total"]
    c.append(f'<text x="28" y="36" font-size="12" font-weight="800" letter-spacing="3" fill="{OURO}">A JORNADA DO BARDO</text>')
    c.append(f'<text x="28" y="58" font-size="14" fill="{TEXTO_2}"><tspan fill="{TEXTO}" font-weight="700">{total}</tspan> '
             f'contribuições no último ano · cada dia de código vira uma nota</text>')

    for i, semana in enumerate(semanas):
        atraso = viagem * T * i / max(1, n - 1)
        for dia in semana:
            wd = datetime.strptime(dia["date"], "%Y-%m-%d").weekday()  # seg=0
            linha = (wd + 1) % 7  # domingo no topo, como no GitHub
            c.append(f'<rect class="n_{dia["contributionLevel"]}" style="animation-delay: {atraso:.2f}s" '
                     f'x="{x0 + i * passo}" y="{y0 + linha * passo}" width="{cel}" height="{cel}" rx="2.5"/>')

    sprite, sw, sh = sprite_bardo()
    bx = x0 + cel / 2 - sw / 2
    by = y0 - sh - 2
    sons = "".join(
        f'<text class="som" x="{sw - 4}" y="10" font-size="13" fill="{cor}" style="animation-delay: {k * 0.55:.2f}s">{s}</text>'
        for k, (s, cor) in enumerate([("♪", ROSA), ("♫", CIANO), ("♪", OURO)])
    )
    c.append(f'<g class="bardo"><g transform="translate({bx:.1f},{by:.1f})"><g class="passo">{sprite}</g>{sons}</g></g>')

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
    (SAIDA / "ficha.svg").write_text(gerar_ficha(dados), encoding="utf-8")
    (SAIDA / "jornada.svg").write_text(gerar_jornada(dados), encoding="utf-8")
    print(f"ok: {dados['total']} contribuições, {dados['repos']} repos, linguagens: "
          f"{[n for n, _ in dados['linguagens'][:5]]}")


if __name__ == "__main__":
    main()
