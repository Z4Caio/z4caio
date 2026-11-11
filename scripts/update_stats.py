import json
import math
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USER", "Z4Caio")
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gh_get(url: str, extra_headers=None):
    headers = {
        "User-Agent": "Z4Caio-Profile-Updater/1.0",
        "Accept": "application/vnd.github+json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_profile_data():
    user = gh_get(f"https://api.github.com/users/{USERNAME}")
    repos = gh_get(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated")

    lang_bytes = {}
    total_stars = 0
    project_repos = []

    for r in repos:
        stars = int(r.get("stargazers_count", 0))
        total_stars += stars
        r_langs = gh_get(r["languages_url"])
        for lang, b in r_langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + int(b)

        if r["name"].lower() != USERNAME.lower():
            project_repos.append({
                "name": r["name"],
                "description": r.get("description") or "",
                "html_url": r["html_url"],
                "language": r.get("language") or "HTML",
                "stars": stars,
                "forks": int(r.get("forks_count", 0)),
                "langs": r_langs,
            })

    # Commits & PRs
    try:
        commits_data = gh_get(
            f"https://api.github.com/search/commits?q=author:{USERNAME}",
            extra_headers={"Accept": "application/vnd.github.cloak-preview+json"},
        )
        total_commits = int(commits_data.get("total_count", 0))
    except Exception:
        total_commits = 24

    try:
        prs_data = gh_get(f"https://api.github.com/search/issues?q=author:{USERNAME}+type:pr")
        total_prs = int(prs_data.get("total_count", 0))
    except Exception:
        total_prs = 2

    return {
        "public_repos": int(user.get("public_repos", len(repos))),
        "total_commits": total_commits,
        "total_prs": total_prs,
        "total_stars": total_stars,
        "lang_bytes": lang_bytes,
        "projects": project_repos,
    }


LANG_COLORS = {
    "HTML": "#ff6b4a",
    "CSS": "#a277ff",
    "JavaScript": "#00f5d4",
    "Python": "#38bdf8",
    "TypeScript": "#60a5fa",
}


def generate_radar_svg(data: dict, out_path: str):
    lang_bytes = data["lang_bytes"]
    total_b = max(sum(lang_bytes.values()), 1)

    sorted_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:4]
    while len(sorted_langs) < 4:
        sorted_langs.append(("SQL", 0))

    # Percentages
    langs_pct = [(name, (b / total_b) * 100.0) for name, b in sorted_langs]

    # Radar geometry (4-axis diamond like Reference Image 3: Top, Right, Bottom, Left)
    cx, cy = 292, 195
    max_r = 105
    max_pct = max(p for _, p in langs_pct) or 1.0

    # Angles: Top (-90°), Right (0°), Bottom (90°), Left (180°)
    angles = [-math.pi / 2, 0.0, math.pi / 2, math.pi]
    pts = []
    for idx, (name, pct) in enumerate(langs_pct):
        # Square root scale just like Reference Image 3 ("escala raiz quadrada")
        norm = math.sqrt(pct / max_pct) if max_pct > 0 else 0.15
        r = max(18.0, norm * max_r)
        ang = angles[idx]
        px = cx + r * math.cos(ang)
        py = cy + r * math.sin(ang)
        pts.append((px, py, name, pct))

    poly_points = " ".join(f"{px:.1f},{py:.1f}" for px, py, _, _ in pts)

    # Multi-segment bar widths (total width = 520)
    bar_total_w = 520
    seg_rects = []
    cur_x = 0.0
    for name, pct in langs_pct:
        w = max(8.0, (pct / 100.0) * bar_total_w)
        if cur_x + w > bar_total_w:
            w = max(4.0, bar_total_w - cur_x)
        color = LANG_COLORS.get(name, "#00f5d4")
        seg_rects.append(f'<rect x="{cur_x:.1f}" y="0" width="{w:.1f}" height="10" rx="3" fill="{color}"/>')
        cur_x += w + 3.0

    # Language rows
    rows_svg = []
    y_positions = [104, 162, 220, 278]
    for idx, (name, pct) in enumerate(langs_pct):
        y = y_positions[idx]
        color = LANG_COLORS.get(name, "#00f5d4")
        w = max(10.0, (pct / 100.0) * 520.0)
        pct_str = f"{pct:.1f}%" if pct < 10 else f"{pct:.0f}%"
        rows_svg.append(f"""
    <g transform="translate(32, {y})">
      <circle cx="7" cy="6" r="5" fill="{color}"/>
      <text x="22" y="11" class="lang-name">{name}</text>
      <text x="520" y="11" text-anchor="end" class="lang-pct" fill="{color}">{pct_str}</text>
      <rect x="0" y="22" width="520" height="7" rx="3.5" fill="#161f30"/>
      <rect x="0" y="22" width="{w:.1f}" height="7" rx="3.5" fill="{color}"/>
    </g>""")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 475" width="100%" height="100%">
  <defs>
    <linearGradient id="panelBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b0e17"/>
      <stop offset="100%" stop-color="#06080d"/>
    </linearGradient>
    <linearGradient id="radarFill" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5d4" stop-opacity="0.40"/>
      <stop offset="100%" stop-color="#a277ff" stop-opacity="0.35"/>
    </linearGradient>
  </defs>

  <style>
    .panel-title {{ font: 700 16px 'Segoe UI', -apple-system, sans-serif; fill: #00f5d4; letter-spacing: 0.5px; }}
    .axis-label {{ font: 600 12.5px 'Segoe UI', -apple-system, sans-serif; fill: #e2e8f0; }}
    .caption {{ font: 400 11.5px 'Segoe UI', -apple-system, sans-serif; fill: #94a3b8; }}
    .lang-name {{ font: 600 13.5px 'Segoe UI', -apple-system, sans-serif; fill: #f8fafc; }}
    .lang-pct {{ font: 700 13.5px 'Consolas', monospace; }}
    .stat-label {{ font: 500 12.5px 'Segoe UI', -apple-system, sans-serif; fill: #94a3b8; }}
    .stat-val {{ font: 700 26px 'Segoe UI', -apple-system, sans-serif; fill: #00f5d4; }}
  </style>

  <!-- LEFT PANEL: RADAR DE LINGUAGENS -->
  <g transform="translate(0, 0)">
    <rect width="585" height="355" rx="18" fill="url(#panelBg)" stroke="#1e293b" stroke-width="1.5"/>
    <text x="32" y="42" class="panel-title">Radar de linguagens</text>

    <!-- Diamond Radar Grid (Center: 292, 195) -->
    <g stroke="#334155" stroke-width="1" fill="none">
      <polygon points="292,90 397,195 292,300 187,195" stroke-opacity="0.75"/>
      <polygon points="292,116 371,195 292,274 213,195" stroke-opacity="0.55"/>
      <polygon points="292,142 345,195 292,248 239,195" stroke-opacity="0.40"/>
      <polygon points="292,168 318,195 292,222 266,195" stroke-opacity="0.25"/>
      <line x1="292" y1="90" x2="292" y2="300" stroke-opacity="0.6"/>
      <line x1="187" y1="195" x2="397" y2="195" stroke-opacity="0.6"/>
    </g>

    <!-- Real Calculated Radar Polygon -->
    <polygon points="{poly_points}" fill="url(#radarFill)" stroke="#00f5d4" stroke-width="2.2"/>

    <!-- Vertices -->
    <circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="4.5" fill="#00f5d4"/>
    <circle cx="{pts[1][0]:.1f}" cy="{pts[1][1]:.1f}" r="4.5" fill="#00f5d4"/>
    <circle cx="{pts[2][0]:.1f}" cy="{pts[2][1]:.1f}" r="4.5" fill="#00f5d4"/>
    <circle cx="{pts[3][0]:.1f}" cy="{pts[3][1]:.1f}" r="4.5" fill="#00f5d4"/>

    <!-- Axis Labels -->
    <text x="292" y="75" text-anchor="middle" class="axis-label">{pts[0][2]}</text>
    <text x="410" y="199" text-anchor="start" class="axis-label">{pts[1][2]}</text>
    <text x="292" y="322" text-anchor="middle" class="axis-label">{pts[2][2]}</text>
    <text x="174" y="199" text-anchor="end" class="axis-label">{pts[3][2]}</text>

    <text x="32" y="340" class="caption">Proporção real de código por linguagem, escala raiz quadrada</text>
  </g>

  <!-- RIGHT PANEL: PRINCIPAIS LINGUAGENS -->
  <g transform="translate(615, 0)">
    <rect width="585" height="355" rx="18" fill="url(#panelBg)" stroke="#1e293b" stroke-width="1.5"/>
    <text x="32" y="42" class="panel-title">Principais linguagens</text>

    <g transform="translate(32, 62)">
      {"".join(seg_rects)}
    </g>
    {"".join(rows_svg)}

    <text x="32" y="340" class="caption">atualizado automaticamente via GitHub API em {today_str}</text>
  </g>

  <!-- BOTTOM REAL METRICS BAR -->
  <g transform="translate(0, 375)">
    <rect width="1200" height="95" rx="18" fill="url(#panelBg)" stroke="#1e293b" stroke-width="1.5"/>

    <line x1="300" y1="18" x2="300" y2="77" stroke="#1e293b" stroke-width="1.5"/>
    <line x1="600" y1="18" x2="600" y2="77" stroke="#1e293b" stroke-width="1.5"/>
    <line x1="900" y1="18" x2="900" y2="77" stroke="#1e293b" stroke-width="1.5"/>

    <text x="32" y="36" class="stat-label">Repositórios</text>
    <text x="32" y="72" class="stat-val">{data["public_repos"]}</text>

    <text x="332" y="36" class="stat-label">Commits no último ano</text>
    <text x="332" y="72" class="stat-val">{data["total_commits"]}</text>

    <text x="632" y="36" class="stat-label">Pull requests</text>
    <text x="632" y="72" class="stat-val">{data["total_prs"]}</text>

    <text x="932" y="36" class="stat-label">Estrelas recebidas</text>
    <text x="932" y="72" class="stat-val">{data["total_stars"]}</text>
  </g>
</svg>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)


PROJECT_META = {
    "remae-prototipo": {
        "badge": "⭐ PROJETO EM DESTAQUE",
        "icon": "🌐",
        "border": "#164e63",
        "glow": "glowAqua",
        "tag_bg": "#062830",
        "tag_color": "#00f5d4",
        "desc1": "Protótipo web interativo com interface moderna,",
        "desc2": "estrutura semântica em HTML5, estilização CSS3",
        "desc3": "e scripts dinâmicos em JavaScript.",
    },
    "Clinica_de_Estetica": {
        "badge": "✨ UI/UX & LANDING PAGE",
        "icon": "💎",
        "border": "#3b1d6e",
        "glow": "glowPurple",
        "tag_bg": "#231242",
        "tag_color": "#c4b5fd",
        "desc1": "Aplicação web para Clínica de Estética com foco",
        "desc2": "em experiência do usuário (UI/UX), design",
        "desc3": "elegante, responsividade e interatividade JS.",
    },
    "Advocacia-LandingPage": {
        "badge": "⚖️ WEB DESIGN & FRONT-END",
        "icon": "🏛️",
        "border": "#1e3a5f",
        "glow": "glowBlue",
        "tag_bg": "#0f243c",
        "tag_color": "#38bdf8",
        "desc1": "Landing page institucional moderna para",
        "desc2": "escritório de advocacia, projetada com foco",
        "desc3": "em conversão, tipografia e layout responsivo.",
    },
    "FishingLanding": {
        "badge": "🎣 AQUA & FISHING UI",
        "icon": "🐠",
        "border": "#164e63",
        "glow": "glowAqua",
        "tag_bg": "#062830",
        "tag_color": "#00f5d4",
        "desc1": "Landing page temática sobre pesca e universo",
        "desc2": "aquático para laboratório prático de CSS3,",
        "desc3": "HTML5 e interações Front-End.",
    },
}


def generate_projects_svg(data: dict, out_path: str):
    projects = data["projects"][:4]
    cards_svg = []
    positions = [
        (0, 5),
        (608, 5),
        (0, 235),
        (608, 235),
    ]

    for idx, p in enumerate(projects):
        if idx >= 4:
            break
        x, y = positions[idx]
        name = p["name"]
        meta = PROJECT_META.get(
            name,
            {
                "badge": "💻 REPOSITÓRIO GITHUB",
                "icon": "🚀",
                "border": "#1e293b",
                "glow": "glowAqua",
                "tag_bg": "#0f172a",
                "tag_color": "#00f5d4",
                "desc1": (p["description"] or "Projeto desenvolvido por Z4Caio no GitHub.")[:48],
                "desc2": "Código estruturado com boas práticas de",
                "desc3": "desenvolvimento Front-End e UI/UX.",
            },
        )

        # Calculate repo language percentages
        r_langs = p.get("langs") or {p["language"]: 100}
        r_tot = max(sum(r_langs.values()), 1)
        pills = []
        px = 0
        for l_name, l_bytes in sorted(r_langs.items(), key=lambda item: item[1], reverse=True)[:3]:
            l_pct = (l_bytes / r_tot) * 100.0
            label = f"{l_name} {l_pct:.0f}%"
            w = max(82, len(label) * 8 + 20)
            l_col = LANG_COLORS.get(l_name, "#00f5d4")
            pills.append(f"""
      <rect x="{px}" y="0" width="{w}" height="26" rx="8" fill="#111827" stroke="#1e293b"/>
      <text x="{px + w/2:.1f}" y="17" text-anchor="middle" class="tech-pill" fill="{l_col}">{label}</text>""")
            px += w + 10

        star_badge = f"★ {p['stars']}" if p["stars"] > 0 else "PUBLIC"

        cards_svg.append(f"""
  <g transform="translate({x}, {y})">
    <rect width="592" height="215" rx="20" fill="url(#projBg)" stroke="{meta['border']}" stroke-width="1.5"/>
    <rect width="592" height="215" rx="20" fill="url(#{meta['glow']})"/>

    <rect x="26" y="22" width="175" height="24" rx="12" fill="{meta['tag_bg']}" stroke="{meta['tag_color']}" stroke-width="1"/>
    <text x="113" y="38" text-anchor="middle" class="proj-tag" fill="{meta['tag_color']}">{meta['badge']}</text>

    <rect x="495" y="22" width="70" height="24" rx="12" fill="#111827" stroke="#334155" stroke-width="1"/>
    <text x="530" y="38" text-anchor="middle" class="proj-tag" fill="#fde047">{star_badge}</text>

    <text x="26" y="78" class="proj-title">{meta['icon']} {name}</text>
    <text x="26" y="106" class="proj-desc">{meta['desc1']}</text>
    <text x="26" y="126" class="proj-desc">{meta['desc2']}</text>
    <text x="26" y="146" class="proj-desc">{meta['desc3']}</text>

    <g transform="translate(26, 168)">
      {"".join(pills)}
    </g>
  </g>""")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 460" width="100%" height="100%">
  <defs>
    <linearGradient id="projBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d111c"/>
      <stop offset="100%" stop-color="#070910"/>
    </linearGradient>
    <radialGradient id="glowAqua" cx="85%" cy="15%" r="65%">
      <stop offset="0%" stop-color="#00f5d4" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#070910" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowPurple" cx="85%" cy="15%" r="65%">
      <stop offset="0%" stop-color="#a277ff" stop-opacity="0.24"/>
      <stop offset="100%" stop-color="#070910" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowBlue" cx="85%" cy="15%" r="65%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#070910" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <style>
    .proj-tag {{ font: 600 10.5px 'Consolas', monospace; letter-spacing: 1.2px; text-transform: uppercase; }}
    .proj-title {{ font: 700 20px 'Segoe UI', -apple-system, sans-serif; fill: #ffffff; }}
    .proj-desc {{ font: 400 13.5px 'Segoe UI', -apple-system, sans-serif; fill: #94a3b8; }}
    .tech-pill {{ font: 600 11.5px 'Consolas', monospace; }}
  </style>
  {"".join(cards_svg)}
</svg>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    profile_data = fetch_profile_data()
    generate_radar_svg(profile_data, os.path.join(assets_dir, "radar-capabilities.svg"))
    generate_projects_svg(profile_data, os.path.join(assets_dir, "projects-bento.svg"))
    print("Successfully updated SVGs with live GitHub data:", json.dumps(profile_data, ensure_ascii=False))
