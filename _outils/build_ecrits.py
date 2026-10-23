#!/usr/bin/env python3
"""Génère la section Écrits du portfolio à partir des articles Markdown.

Source : 2 CASQUETTES/Écriture et lecture/Publiés/*.md (+ images/<slug>/)
Sortie : ecrits.html, ecrits/<slug>.html, assets/ecrits/<slug>/*, sitemap.xml,
         et la liste des essais de about.html (entre les marqueurs ESSAYS).

Usage (depuis la racine du site) : python3 _outils/build_ecrits.py
"""
import html, json, os, re, shutil, sys
from datetime import date
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.abspath(os.path.join(SITE, '..', '..', 'Écriture et lecture', 'Publiés'))
BASE = 'https://willy-bonneton.vercel.app'
AUTHOR = 'Willy Bonneton'
MEDIUM_PROFILE = 'https://willybonneton.medium.com/'

# Descriptions courtes (liste + balises meta). Une phrase, factuelle.
DESC = {
    'optionnalite': "Antifragilité appliquée à l'ère de l'IA : stratégie barbell, workload creep, et ce que ça demande vraiment au niveau individuel et organisationnel.",
    'argent': "Niall Ferguson (The Ascent of Money) et Morgan Housel (The Psychology of Money) : la monnaie comme infrastructure historique des civilisations d'un côté, comme rapport psychologique individuel de l'autre, et ce que ce grand écart révèle.",
    'equilibre': "Tim Urban (What's Our Problem?) : l'axe vertical de qualité de pensée, la pensée primitive vs. avancée, et la défense de la nuance contre la polarisation.",
    'modele': "Balaji Srinivasan (The Network State) : décentralisation, gouvernance en réseau et cryptographie comme infrastructure de vérité.",
    'entrepreneuriat': "Tony Fadell (BUILD) : le cycle Do-Fail-Learn, la progression V1→V3, et le facteur humain comme variable décisive dans la construction.",
    'comprehension': "Vaclav Smil (How the World Really Works) : énergie, ammoniac, acier, ciment et plastique comme piliers matériels du monde moderne, et ce que ça implique pour la transition énergétique.",
    'passe': "David Deutsch (The Beginning of Infinity) : de la préhistoire aux Lumières, l'entropie, la créativité, et l'idée que la connaissance n'a pas de limite.",
}
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


def fr_date(iso):
    y, m, d = map(int, iso.split('-'))
    return f"{d} {MOIS[m - 1]} {y}" if d > 1 else f"1er {MOIS[m - 1]} {y}"


def esc(s):
    return html.escape(s, quote=True)


# ───────────────────────── Markdown (sous-ensemble utilisé par les articles)
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', s, flags=re.S)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s, flags=re.S)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


def autolink(s):
    def f(m):
        u = m.group(0).rstrip('.,;)')
        tail = m.group(0)[len(u):]
        label = re.sub(r'^https?://(www\.)?', '', u)
        label = label if len(label) <= 48 else label[:45] + '…'
        return f'<a href="{u}" target="_blank" rel="noopener">{label}</a>{tail}'
    return re.sub(r'(?<![">])https?://[^\s<]+', f, s)


def parse(path):
    raw = open(path, encoding='utf-8').read()
    _, fm, body = raw.split('---', 2)
    meta = {}
    for line in fm.strip().split('\n'):
        k, _, v = line.partition(': ')
        meta[k] = json.loads(v) if v[:1] in '["' else int(v) if v.isdigit() else v
    return meta, body.strip()


def render_body(slug, body):
    blocks = [b for b in body.split('\n\n') if b.strip()]
    out, subtitle, cover, lis, nfig = [], None, None, [], 0

    def flush():
        nonlocal lis
        if lis:
            out.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in lis) + '</ul>')
            lis = []

    for b in blocks:
        b = b.strip()
        if b.startswith('- '):
            lis.append(b[2:]); continue
        flush()
        if b.startswith('!['):
            m = re.match(r'!\[(.*?)\]\((.*?)\)(?:\n\*(.*)\*)?$', b, re.S)
            alt, src, cap = m.group(1), m.group(2), m.group(3) or ''
            fn = os.path.basename(src)
            web = f'assets/ecrits/{slug}/{fn}'
            w, h = Image.open(os.path.join(SRC, src)).size
            fig = (f'<figure class="art-fig"><img src="@@{web}" alt="{esc(alt)}" width="{w}" height="{h}" loading="lazy">'
                   + (f'<figcaption>{autolink(inline(cap))}</figcaption>' if cap else '') + '</figure>')
            if cover is None:
                cover = dict(src=web, w=w, h=h, alt=alt, cap=cap)
            else:
                out.append(fig)
            nfig += 1
        elif b.startswith('### '):
            out.append(f'<h3>{inline(b[4:])}</h3>')
        elif b.startswith('## '):
            out.append(f'<h2>{inline(b[3:])}</h2>')
        elif cover is None and re.fullmatch(r'\*[^*]+\*', b):
            subtitle = b[1:-1]
        else:
            out.append(f'<p>{inline(b)}</p>')
    flush()
    return '\n'.join(out), subtitle, cover


# ───────────────────────── gabarits
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&display=swap" rel="stylesheet">')

NAV = '''<header id="site-header">
    <div class="container">
      <nav>
        <a href="@@index.html" class="nav-brand">Willy Bonneton</a>
        <div class="nav-links">
          <a href="@@index.html#realisations">Réalisations</a>
          <a href="@@index.html#methode">Méthode</a>
          <a href="@@about.html#profil">Profil</a>
          <a href="@@ecrits.html">Écrits</a>
          <a href="@@about.html#lectures">Lectures</a>
          <a href="@@about.html">À propos</a>
          <a href="https://www.linkedin.com/in/willy-bonneton/" target="_blank" rel="noopener" class="nav-cta">LinkedIn ↗</a>
        </div>
        <button class="mobile-menu-btn" aria-label="Menu" aria-expanded="false">☰</button>
      </nav>
    </div>
    <div class="mobile-menu">
      <a href="@@index.html#realisations">Réalisations</a>
      <a href="@@index.html#methode">Méthode</a>
      <a href="@@about.html#profil">Profil</a>
      <a href="@@ecrits.html">Écrits</a>
      <a href="@@about.html#lectures">Lectures</a>
      <a href="@@about.html">À propos</a>
      <a href="https://www.linkedin.com/in/willy-bonneton/" target="_blank" rel="noopener" class="nav-cta">LinkedIn ↗</a>
    </div>
  </header>'''

FOOT = '''<footer>
    <div class="container">
      <p>Willy Bonneton · Lyon</p>
      <a href="@@about.html#ecrits">Retour</a>
    </div>
  </footer>'''

SCRIPT = '''<script>
    (function () {
      var header = document.getElementById('site-header');
      var bar = document.querySelector('.art-progress span');
      var onScroll = function () {
        header.classList.toggle('scrolled', window.scrollY > 20);
        if (bar) {
          var h = document.documentElement.scrollHeight - window.innerHeight;
          bar.style.transform = 'scaleX(' + (h > 0 ? Math.min(1, window.scrollY / h) : 0) + ')';
        }
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
      var btn = document.querySelector('.mobile-menu-btn');
      var menu = document.querySelector('.mobile-menu');
      btn.addEventListener('click', function () {
        var open = menu.classList.toggle('open');
        btn.textContent = open ? '✕' : '☰';
        btn.setAttribute('aria-expanded', open);
      });
    })();
  </script>
  <script defer src="/_vercel/insights/script.js"></script>'''


def og_image(a):
    c = a['cover']
    if c and 1.4 <= c['w'] / c['h'] <= 2.2:
        return BASE + '/' + c['src'], c['w'], c['h']
    return BASE + '/assets/og-image.jpg', 1200, 630


def head(title, desc, url, og, og_type, extra=''):
    img, w, h = og
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{url}">

  <link rel="icon" href="@@favicon-32.png" type="image/png">
  <link rel="icon" href="@@favicon-192.png" type="image/png" sizes="192x192">
  <link rel="apple-touch-icon" href="@@apple-touch-icon.png">

  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{AUTHOR}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{img}">
  <meta property="og:image:width" content="{w}">
  <meta property="og:image:height" content="{h}">
  <meta property="og:locale" content="fr_FR">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{img}">
{extra}
  {FONTS}
  <link rel="stylesheet" href="@@style.css">
</head>
<body class="art-page">

  {NAV}
'''


def article_page(a, newer, older):
    url = f"{BASE}/ecrits/{a['slug']}.html"
    title = a['title']
    desc = DESC[a['slug']]
    ld = {
        '@context': 'https://schema.org', '@type': 'Article', 'headline': title,
        'description': desc, 'datePublished': a['date'], 'inLanguage': 'fr',
        'image': og_image(a)[0], 'mainEntityOfPage': url,
        'author': {'@type': 'Person', 'name': AUTHOR, 'url': BASE + '/'},
    }
    extra = f'  <script type="application/ld+json">\n  {json.dumps(ld, ensure_ascii=False)}\n  </script>'
    tags = ''.join(f'<span class="badge-pill">{esc(t)}</span>' for t in a['tags'])
    sub = f'<p class="art-sub">{inline(a["subtitle"])}</p>' if a['subtitle'] else ''
    c = a['cover']
    cover = ''
    if c:
        cover = (f'<figure class="art-cover"><img src="@@{c["src"]}" alt="{esc(c["alt"])}" width="{c["w"]}" height="{c["h"]}">'
                 + (f'<figcaption>{autolink(inline(c["cap"]))}</figcaption>' if c['cap'] else '') + '</figure>')

    def card(x, label):
        if not x: return '<span></span>'
        return (f'<a class="art-pn" href="@@ecrits/{x["slug"]}.html"><span class="art-pn-label">{label}</span>'
                f'<span class="art-pn-title">{esc(x["title"])}</span></a>')
    nav = f'<div class="art-pn-wrap">{card(older, "← Article précédent")}{card(newer, "Article suivant →")}</div>'
    return head(f'{title} · {AUTHOR}', desc, url, og_image(a), 'article', extra) + f'''
  <main>
    <div class="art-progress"><span></span></div>
    <article class="art">
      <div class="art-head">
        <a class="art-back" href="@@ecrits.html">← Tous les écrits</a>
        <div class="art-tags">{tags}</div>
        <h1>{esc(title)}</h1>
        {sub}
        <div class="art-byline">
          <img src="@@assets/willy-bonneton.jpg" alt="" width="44" height="44">
          <div><span class="art-by-name">{AUTHOR}</span>
          <span class="art-by-meta">{fr_date(a['date'])} · {a['read_time']} min de lecture</span></div>
        </div>
      </div>
      {cover}
      <div class="art-body">
{a['html']}
      </div>
      <div class="art-end">
        {nav}
      </div>
    </article>
  </main>

  {FOOT}

  {SCRIPT}
</body>
</html>
'''


def list_page(arts):
    url = f'{BASE}/ecrits.html'
    desc = "Notes de lecture longues sur l'IA, l'argent, l'entrepreneuriat, la société et le progrès. Willy Bonneton."
    items = []
    for a in arts:
        c = a['cover']
        thumb = (f'<span class="lst-thumb"><img src="@@{c["src"]}" alt="" width="{c["w"]}" height="{c["h"]}" loading="lazy"></span>' if c else '')
        tags = ' · '.join(esc(t) for t in a['tags'][:3])
        items.append(f'''        <a class="lst-item" href="@@ecrits/{a['slug']}.html">
          {thumb}
          <span class="lst-text">
            <span class="lst-meta">{fr_date(a['date'])} · {a['read_time']} min · {tags}</span>
            <span class="lst-title">{esc(a['title'])}</span>
            <span class="lst-desc">{esc(DESC[a['slug']])}</span>
          </span>
        </a>''')
    return head(f'Écrits · {AUTHOR}', desc, url, (BASE + '/assets/og-image.jpg', 1200, 630), 'website') + f'''
  <main>
    <section class="lst">
      <div class="container lst-inner">
        <span class="badge-pill">Écrits</span>
        <h1>Ce que je lis, ce que j'en pense</h1>
        <p class="lst-intro">Des notes de lecture longues : un livre, une idée centrale, et ce qu'elle change dans ma façon de voir les choses. Aussi publiées sur <a href="{MEDIUM_PROFILE}" target="_blank" rel="noopener">Medium ↗</a>.</p>
        <div class="lst-list">
{chr(10).join(items)}
        </div>
      </div>
    </section>
  </main>

  {FOOT}

  {SCRIPT}
</body>
</html>
'''


def about_items(arts):
    rows = []
    for a in arts:
        rows.append(f'''          <a href="@@ecrits/{a['slug']}.html" class="essay-item">
            <span class="essay-date">{a['date'][:4]}</span>
            <div class="essay-content">
              <span class="essay-title">{esc(a['title'].rstrip('…'))}</span>
              <span class="essay-desc">{esc(DESC[a['slug']])}</span>
            </div>
            <span class="essay-arrow">→</span>
          </a>''')
    return '\n'.join(rows)


def main():
    arts = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith('.md'): continue
        meta, body = parse(os.path.join(SRC, f))
        a = dict(meta)
        a['html'], a['subtitle'], a['cover'] = render_body(a['slug'], body)
        arts.append(a)
    arts.sort(key=lambda a: a['date'], reverse=True)
    for a in arts:
        assert a['slug'] in DESC, 'description manquante : ' + a['slug']

    # images
    for a in arts:
        dst = os.path.join(SITE, 'assets', 'ecrits', a['slug'])
        os.makedirs(dst, exist_ok=True)
        for fn in os.listdir(os.path.join(SRC, 'images', a['slug'])):
            shutil.copy2(os.path.join(SRC, 'images', a['slug'], fn), os.path.join(dst, fn))

    os.makedirs(os.path.join(SITE, 'ecrits'), exist_ok=True)
    for i, a in enumerate(arts):
        newer = arts[i - 1] if i > 0 else None
        older = arts[i + 1] if i + 1 < len(arts) else None
        open(os.path.join(SITE, 'ecrits', a['slug'] + '.html'), 'w', encoding='utf-8').write(article_page(a, newer, older).replace('@@', '../'))
    open(os.path.join(SITE, 'ecrits.html'), 'w', encoding='utf-8').write(list_page(arts).replace('@@', ''))

    # sitemap
    urls = [(BASE + '/', '1.0'), (BASE + '/about.html', '0.8'), (BASE + '/case-etude-support-ops.html', '0.6'),
            (BASE + '/ecrits.html', '0.6')] + [(f"{BASE}/ecrits/{a['slug']}.html", '0.5') for a in arts]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, p in urls:
        sm.append(f'  <url>\n    <loc>{u}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>{p}</priority>\n  </url>')
    sm.append('</urlset>')
    open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(sm) + '\n')

    # about.html : liste des essais entre marqueurs
    p = os.path.join(SITE, 'about.html')
    s = open(p, encoding='utf-8').read()
    if '<!-- ESSAYS:START -->' not in s:
        s = re.sub(r'(<div class="essays-list reveal">)(.*?)(\n        </div>\n\n        <div style="text-align:center">)',
                   lambda m: m.group(1) + '\n<!-- ESSAYS:START -->\n<!-- ESSAYS:END -->' + m.group(3), s, count=1, flags=re.S)
    s = re.sub(r'<!-- ESSAYS:START -->.*?<!-- ESSAYS:END -->',
               lambda m: '<!-- ESSAYS:START -->\n' + about_items(arts).replace('@@', '') + '\n          <!-- ESSAYS:END -->', s, flags=re.S)
    open(p, 'w', encoding='utf-8').write(s)
    print(f'{len(arts)} articles générés ·', ', '.join(a['slug'] for a in arts))


if __name__ == '__main__':
    main()
