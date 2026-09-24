"""Star Weebs: replaces ship hull art with anime-girl alternatives.

Approach:
  * Patches Client._get_ship_img (Client.py) to intercept lookups for ship
    types this mod has art for. The slug it checks against is computed the
    same way the original method computes it (lowercase, alphanumeric-only),
    so it matches regardless of how the server capitalizes/punctuates the
    ship_type string.
  * A ship type this mod has no art for falls straight through to the
    original method unchanged, so every other ship (and the fallback
    triangle for ships with no art at all) keeps working exactly as before.
  * Art is loaded once on client.startup and cached in this module, mirroring
    the original method's own raw-image cache -- no per-frame disk I/O.
"""
import os
import re

# ship_type slug (see Client._get_ship_img) -> art file under images/.
_REPLACEMENTS = {
    "250capital": "250Capital.png",
    "250carrier": "250Carrier.png",
    "250combatfreighter2": "250CombatFreighter2.png",
}

_images = {}
_install_path = [None]
_original_get_ship_img = None
_patched_class = None


def _load_images(pygame, install_path):
    images_dir = os.path.join(str(install_path), "mod", "star_weebs", "images")
    for slug, filename in _REPLACEMENTS.items():
        path = os.path.join(images_dir, filename)
        try:
            _images[slug] = pygame.image.load(path).convert_alpha()
        except Exception:
            _images[slug] = None


def _make_get_ship_img(original):
    def _get_ship_img_weebs(self, ship_type: str, size: int = 0):
        slug = re.sub(r'[^a-z0-9]', '', ship_type.lower())
        replacement = _images.get(slug)
        if replacement is not None:
            return replacement
        return original(self, ship_type, size)
    return _get_ship_img_weebs


def _on_startup(host, pygame, screen):
    global _original_get_ship_img, _patched_class

    _load_images(pygame, _install_path[0])

    cls = type(host)
    _patched_class = cls
    _original_get_ship_img = cls._get_ship_img
    cls._get_ship_img = _make_get_ship_img(_original_get_ship_img)


def _on_shutdown(**_kwargs):
    if _patched_class is not None and _original_get_ship_img is not None:
        _patched_class._get_ship_img = _original_get_ship_img


def apply(api):
    _install_path[0] = api.install_path
    api.on("client.startup", _on_startup)
    api.on("loader.shutdown", _on_shutdown)
    api.logger.info("star-weebs ready, waiting for client.startup")
