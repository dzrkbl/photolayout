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
import sys
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

# ------------------------------------------------------------------ villes
CITIES = {
    "larbaa_nath_irathen": dict(
        title="LARBÂA NATH IRATHEN",
        subtitle="(Fort National)",
        point=(36.6366, 4.2067),
        coords="36.6366° N, 4.2067° E",
        radius=1300,
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


def fetch_layers(point, radius, with_buildings):
    """Récupère rues, végétation, eau (et bâtiments) autour d'un point."""
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
    return edges, green, water, buildings, crs


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
            polys.plot(ax=ax, fc=GREEN, ec="none", alpha=0.15, zorder=1)

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


def make_poster(key, with_buildings=True, dpi=300):
    city = CITIES[key]
    print(f"▸ {city['title']}")
    serif = register_fonts()
    edges, green, water, buildings, crs = fetch_layers(
        city["point"], city["radius"], with_buildings
    )

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor(CREAM)
    ax = fig.add_axes(MAP_BOX)
    draw_map(ax, city["point"], city["radius"], edges, green, water, buildings, crs)
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
    parser.add_argument("--no-buildings", action="store_true",
                        help="sans empreintes de bâtiments")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    ox.settings.cache_folder = str(Path(__file__).parent / ".osmnx_cache")
    ox.settings.log_console = False

    keys = list(CITIES) if args.all else (args.cities or ["larbaa_nath_irathen"])
    for key in keys:
        make_poster(key, with_buildings=not args.no_buildings, dpi=args.dpi)


if __name__ == "__main__":
    main()
