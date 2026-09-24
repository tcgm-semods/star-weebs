# Star Weebs

Replaces ship hull art with anime-girl (kanmusu-style) alternatives.

Currently covers:

- `250Capital`
- `250Carrier`
- `250CombatFreighter2`

Ships this mod has no art for are drawn with their normal hull art,
unaffected. Safe to disable/uninstall at any time -- it only patches the
ship-art lookup, never the files on disk.

## Adding more ships

1. Drop a new image into `images/` (any resolution -- it's scaled to fit the
   ship's normal draw size, aspect-ratio preserved).
2. Add an entry to `_REPLACEMENTS` in `main.py` mapping the ship type's slug
   (lowercase, alphanumeric only -- e.g. `"250Capital"` -> `"250capital"`) to
   the image filename.
3. Add the new image path to `manifest.json`'s `files` list.
