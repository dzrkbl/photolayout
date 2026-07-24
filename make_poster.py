#!/usr/bin/env python3
"""Posters de plans de villes — style Japandi minimaliste, données OSM réelles.

Rendu à partir du vrai réseau routier OpenStreetMap (via osmnx, le moteur
qu'utilise prettymaps) : plus jamais de carte hallucinée par un modèle
texte→image. Typographie intégrée (titre serif fin en capitales espacées,
sous-titre italique, coordonnées GPS) → un seul PNG prêt à imprimer.

Usage:
    python make_poster.py                    # Larbâa Nath Irathen seulement
    python make_poster.py tizi_ouzou napoli  # villes choisies
    python make_poster.py --all              # les quatre villes
    python make_poster.py --no-buildings     # sans empreintes de bâtiments
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import osmnx as ox

# ---------------------------------------------------------------- palette
CREAM = "#F5F1E8"
CHARCOAL = "#2B2B28"
GREEN = "#3E5C4B"
GREEN_ALPHA = 0.5  # opacité de la végétation : accents verts francs, fond respirant

# ------------------------------------------------------------------ villes
CITIES = {
    "larbaa_nath_irathen": dict(
        title="LARBÂA NATH IRATHEN",
        subtitle="(Fort National)",
        point=(36.6366, 4.2067),
        coords="36.6366° N, 4.2067° E",
        radius=2500,      # englobe les villages alentour (Taza, At Etelli…)
        labels=True,      # noms des villages en petites capitales
    ),
    "tizi_ouzou": dict(
        title="TIZI OUZOU",
        subtitle="(Tizi Wezzu)",
        point=(36.7169, 4.0497),
        coords="36.7169° N, 4.0497° E",
        radius=2200,
    ),
    "bejaia": dict(
        title="BEJAÏA",
        subtitle="(Bgayet)",
        point=(36.7509, 5.0567),
        coords="36.7509° N, 5.0567° E",
        radius=2200,
    ),
    "napoli": dict(
        title="NAPOLI",
        subtitle="(Naples)",
        point=(40.8518, 14.2681),
        coords="40.8518° N, 14.2681° E",
        radius=2200,
    ),
}

# Épaisseur de trait (points) par type de voie OSM, du plus large au plus fin.
STREET_WIDTHS = {
    "motorway": 2.8, "motorway_link": 2.0,
    "trunk": 2.8, "trunk_link": 2.0,
    "primary": 2.4, "primary_link": 1.8,
    "secondary": 2.0, "secondary_link": 1.5,
    "tertiary": 1.6, "tertiary_link": 1.2,
    "residential": 1.0, "unclassified": 1.0, "living_street": 1.0,
    "pedestrian": 0.8, "service": 0.6, "track": 0.5,
    "path": 0.45, "footway": 0.45, "steps": 0.45, "cycleway": 0.45,
}
DEFAULT_WIDTH = 0.8

GREEN_TAGS = {
    "landuse": ["forest", "meadow", "orchard", "vineyard", "grass"],
    "natural": ["wood", "scrub", "grassland", "heath"],
    "leisure": ["park", "garden"],
}
WATER_TAGS = {"natural": ["water", "bay"], "waterway": True}
BUILDING_TAGS = {"building": True}
PLACE_TAGS = {"place": ["village", "hamlet"]}

# Translittération des noms kabyles vers l'ASCII imprimable par la fonte
# (Ɛ → E comme « At Ɛtelli » → « AT ETELLI », puis suppression des diacritiques).
TRANSLIT = str.maketrans({"Ɛ": "E", "ɛ": "e", "Ɣ": "G", "ɣ": "g"})

# Géométrie du poster : 12×18 in (ratio 2:3), 300 dpi → 3600×5400 px.
FIG_W, FIG_H = 12, 18
MAP_BOX = (0.07, 0.175, 0.86, 0.775)  # (gauche, bas, largeur, hauteur) en fraction

FONTS_DIR = Path(__file__).parent / "fonts"
OUT_DIR = Path(__file__).parent / "posters"


def register_fonts():
    """Enregistre les .ttf du dossier fonts/ et choisit les familles serif."""
    for ttf in sorted(FONTS_DIR.glob("*.ttf")):
        try:
            fm.fontManager.addfont(str(ttf))
        except Exception as exc:  # fonte corrompue → on garde les fallbacks
            print(f"  ! fonte ignorée {ttf.name}: {exc}", file=sys.stderr)
    available = {f.name for f in fm.fontManager.ttflist}
    for family in ("Cormorant Garamond", "EB Garamond", "DejaVu Serif"):
        if family in available:
            return family
    return "serif"


def letterspace(text, letter_gap=" ", word_gap="   "):
    """'FORT NATIONAL' → 'F O R T   N A T I O N A L' (capitales espacées)."""
    return word_gap.join(letter_gap.join(word) for word in text.split())


def clean_place_name(row):
    """Nom de lieu latin/ASCII à partir des tags OSM (souvent multi-écritures)."""
    for key in ("name:fr", "int_name", "name"):
        raw = row.get(key)
        if isinstance(raw, str) and raw.strip():
            s = raw.translate(TRANSLIT)
            s = unicodedata.normalize("NFKD", s)
            s = "".join(c for c in s if not unicodedata.combining(c))
            s = re.sub(r"[^A-Za-z' -]", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            if s:
                return s
    return None


def fetch_layers(point, radius, with_buildings, with_places):
    """Récupère rues, végétation, eau (bâtiments, villages) autour d'un point."""
    dist = int(radius * 1.25)  # marge pour couvrir les coins du cadre

    print("  · réseau routier…")
    graph = ox.graph_from_point(
        point, dist=dist, network_type="all",
        retain_all=True, truncate_by_edge=True, simplify=True,
    )
    edges = ox.graph_to_gdfs(ox.project_graph(graph), nodes=False)
    crs = edges.crs

    def features(tags, label):
        print(f"  · {label}…")
        try:
            gdf = ox.features_from_point(point, tags=tags, dist=dist)
            return gdf.to_crs(crs) if not gdf.empty else None
        except Exception:
            return None  # aucune entité de ce type dans la zone

    green = features(GREEN_TAGS, "végétation")
    water = features(WATER_TAGS, "eau")
    buildings = features(BUILDING_TAGS, "bâtiments") if with_buildings else None
    places = features(PLACE_TAGS, "villages") if with_places else None
    return edges, green, water, buildings, places, crs


def draw_map(ax, point, radius, edges, green, water, buildings, crs):
    """Dessine les couches dans l'axe, cadré sur un rectangle centré."""
    import geopandas as gpd
    from shapely.geometry import Point

    center = (
        gpd.GeoSeries([Point(point[1], point[0])], crs="EPSG:4326")
        .to_crs(crs).iloc[0]
    )
    box_ratio = (MAP_BOX[2] * FIG_W) / (MAP_BOX[3] * FIG_H)  # largeur / hauteur
    half_h = radius
    half_w = radius * box_ratio

    ax.set_facecolor(CREAM)

    if green is not None:
        polys = green[green.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        if not polys.empty:
            polys.plot(ax=ax, fc=GREEN, ec="none", alpha=GREEN_ALPHA, zorder=1)

    if water is not None:
        polys = water[water.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        lines = water[water.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        if not polys.empty:
            polys.plot(ax=ax, fc=GREEN, ec="none", alpha=0.9, zorder=2)
        if not lines.empty:
            lines.plot(ax=ax, color=GREEN, lw=0.9, alpha=0.7, zorder=2)

    if buildings is not None:
        polys = buildings[buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        if not polys.empty:
            polys.plot(ax=ax, fc=CREAM, ec=CHARCOAL, lw=0.35, alpha=0.9, zorder=3)

    # Rues : une passe par classe de voie pour moduler l'épaisseur.
    def width_of(highway):
        if isinstance(highway, list):
            return max(STREET_WIDTHS.get(h, DEFAULT_WIDTH) for h in highway)
        return STREET_WIDTHS.get(highway, DEFAULT_WIDTH)

    widths = edges["highway"].map(width_of)
    for w in sorted(widths.unique()):
        edges[widths == w].plot(
            ax=ax, color=CHARCOAL, lw=w, zorder=4,
            capstyle="round", joinstyle="round",
        )

    ax.set_xlim(center.x - half_w, center.x + half_w)
    ax.set_ylim(center.y - half_h, center.y + half_h)
    ax.set_aspect("equal")
    ax.set_axis_off()


def draw_place_labels(ax, places, serif, size=8.5, min_dist=350):
    """Noms des villages en petites capitales espacées — sans chevauchement,
    sans doublon, et jamais coupés par le bord du cadre."""
    if places is None:
        return
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    m_per_pt = (xmax - xmin) / (MAP_BOX[2] * FIG_W * 72)  # mètres par point typo

    kept, seen = [], set()
    order = {"village": 0, "hamlet": 1}
    rows = sorted(
        places.iterrows(),
        key=lambda kv: order.get(kv[1].get("place"), 2),
    )
    for _, row in rows:
        name = clean_place_name(row)
        if not name or name.lower() in seen:
            continue
        text = letterspace(name.upper(), " ", "  ")
        half_w_text = 0.5 * len(text) * 0.55 * size * m_per_pt
        half_h_text = 0.7 * size * m_per_pt
        pt = row.geometry.representative_point()
        if not (xmin + half_w_text + 50 < pt.x < xmax - half_w_text - 50
                and ymin + half_h_text + 50 < pt.y < ymax - half_h_text - 50):
            continue
        if any(pt.distance(other) < min_dist for other in kept):
            continue
        seen.add(name.lower())
        kept.append(pt)
        ax.text(pt.x, pt.y, text,
                ha="center", va="center", color=CHARCOAL, alpha=0.85,
                family=serif, size=size, zorder=6, clip_on=True)


def add_typography(fig, city, serif):
    fig.text(0.5, 0.108, letterspace(city["title"]),
             ha="center", va="center", color=CHARCOAL,
             family=serif, size=40)
    fig.text(0.5, 0.076, city["subtitle"],
             ha="center", va="center", color=CHARCOAL,
             family=serif, style="italic", size=21)
    fig.text(0.5, 0.050, city["coords"],
             ha="center", va="center", color=CHARCOAL,
             family=serif, size=13)


def make_poster(key, with_buildings=False, dpi=300):
    city = CITIES[key]
    print(f"▸ {city['title']}")
    serif = register_fonts()
    edges, green, water, buildings, places, crs = fetch_layers(
        city["point"], city["radius"], with_buildings, city.get("labels", False)
    )

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor(CREAM)
    ax = fig.add_axes(MAP_BOX)
    draw_map(ax, city["point"], city["radius"], edges, green, water, buildings, crs)
    draw_place_labels(ax, places, serif)
    add_typography(fig, city, serif)

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{key}.png"
    fig.savefig(out, dpi=dpi, facecolor=CREAM)
    plt.close(fig)
    print(f"  ✓ {out} ({dpi} dpi)")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cities", nargs="*", choices=[*CITIES, []],
                        help=f"villes parmi : {', '.join(CITIES)}")
    parser.add_argument("--all", action="store_true", help="toutes les villes")
    parser.add_argument("--buildings", action="store_true",
                        help="ajoute les empreintes de bâtiments (défaut : sans)")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    ox.settings.cache_folder = str(Path(__file__).parent / ".osmnx_cache")
    ox.settings.log_console = False

    keys = list(CITIES) if args.all else (args.cities or ["larbaa_nath_irathen"])
    for key in keys:
        make_poster(key, with_buildings=args.buildings, dpi=args.dpi)


if __name__ == "__main__":
    main()
