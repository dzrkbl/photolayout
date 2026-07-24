# photolayout — posters de plans de villes (Japandi)

Posters minimalistes de plans de villes générés à partir des **vraies données
OpenStreetMap** (via [osmnx](https://osmnx.readthedocs.io/), le moteur
qu'utilise prettymaps) — plus jamais de carte hallucinée par un modèle
texte→image. Le plan **et** la typographie sortent en un seul PNG 300 dpi
prêt à imprimer (12×18 in, ratio 2:3).

## Palette (identique aux autres posters de la série)

| Rôle | Couleur |
|---|---|
| Fond crème | `#F5F1E8` |
| Rues (charbon) | `#2B2B28` |
| Végétation / eau (vert forêt) | `#3E5C4B` |

Typographie : titre en capitales espacées **Cormorant Garamond Light**,
sous-titre italique, coordonnées GPS — fontes incluses dans `fonts/`
(licence SIL OFL, fichiers `OFL-*.txt`).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python make_poster.py                     # Larbâa Nath Irathen (Fort National)
python make_poster.py tizi_ouzou bejaia   # villes choisies
python make_poster.py --all               # les 4 villes de la série
python make_poster.py --buildings         # ajoute les empreintes de bâtiments
```

Les PNG sortent dans `posters/`. Villes disponibles :
`larbaa_nath_irathen`, `tizi_ouzou`, `bejaia`, `napoli` — pour en ajouter
une, compléter le dict `CITIES` dans `make_poster.py` (titre, sous-titre,
point GPS, rayon en mètres).

## Réseau requis

Le script télécharge les données au premier lancement depuis
**overpass-api.de** (API Overpass d'OpenStreetMap), puis les met en cache
dans `.osmnx_cache/`. Dans un environnement à politique réseau restrictive
(p. ex. Claude Code on the web), ce domaine doit être autorisé dans la
politique d'egress de l'environnement — sinon, lancer le script en local.
