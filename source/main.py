"""Star Weebs: replaces ship hull art with anime-girl alternatives.

Approach:
  * Since 0.5.82 the client finds a hull picture along several paths
    (Client.py / render_mixin.py):
      - SolarSystemWindow._ship_picture(ship_type): the in-space renderer's
        non-blocking, worker-decoded lookup by ship type;
      - RenderMixin._ship_picture_for(ship_type, image): (texture key,
        picture), preferring a server-named ``ship_image`` file over the type;
      - RenderMixin._ship_img_for(ship_type, image): the same for panels;
      - SolarSystemWindow._get_ship_img(ship_type): the blocking lookup.
    Each one that exists is wrapped to intercept ship types this mod has art
    for. The slug is computed the same way the client computes it
    (lowercase, alphanumeric-only), so it matches regardless of how the
    server capitalizes/punctuates the ship_type string.
  * The art is also seeded into the window's raw ship-picture cache under the
    same slug key the client uses, so any lookup by type finds it.
  * A ship type this mod has no art for falls straight through to the
    original method unchanged, so every other ship (and the fallback
    triangle for ships with no art at all) keeps working exactly as before.
  * Art is loaded once on client.startup and cached in this module -- no
    per-frame disk I/O.
"""
import os
import re

# ship_type slug (see Client._get_ship_img) -> art file under images/.
_REPLACEMENTS = {
    "250capital": "250Capital.png",
    "250carrier": "250Carrier.png",
    "250combatfreighter2": "250CombatFreighter2.png",
}

# Client methods wrapped, and the kind of wrapper each gets.
_HOOKS = ("_get_ship_img", "_ship_picture", "_ship_picture_for",
          "_ship_img_for")

_images = {}
_install_path = [None]
_logger = [None]
_patched_class = None
_originals = {}       # name -> (original, was defined on the class itself)
_seeded = {}          # slug -> surface placed in host._ship_raw_cache
_host = [None]
_slug_cache = {}


def _slug(ship_type):
    if not isinstance(ship_type, str):
        return None
    slug = _slug_cache.get(ship_type)
    if slug is None:
        slug = _slug_cache[ship_type] = re.sub(
            r'[^a-z0-9]', '', ship_type.lower())
    return slug


def _replacement(ship_type):
    slug = _slug(ship_type)
    return _images.get(slug) if slug is not None else None


def _load_images(pygame, install_path):
    images_dir = os.path.join(str(install_path), "mod", "star_weebs", "images")
    for slug, filename in _REPLACEMENTS.items():
        path = os.path.join(images_dir, filename)
        try:
            _images[slug] = pygame.image.load(path).convert_alpha()
        except Exception:
            _images[slug] = None
            if _logger[0] is not None:
                _logger[0].warning("star-weebs: could not load %s", path)


def _ship_type_arg(args, kwargs):
    return args[0] if args else kwargs.get("ship_type")


def _wrap_picture(original):
    """For getters returning just the picture: _get_ship_img, _ship_picture,
    _ship_img_for."""
    def wrapper(self, *args, **kwargs):
        replacement = _replacement(_ship_type_arg(args, kwargs))
        if replacement is not None:
            return replacement
        return original(self, *args, **kwargs)
    wrapper.__name__ = getattr(original, "__name__", "wrapper")
    wrapper.__doc__ = getattr(original, "__doc__", None)
    return wrapper


def _wrap_picture_for(original):
    """_ship_picture_for returns (texture key, picture). A replaced hull is
    keyed by its ship type, exactly like the client's own by-type path, so it
    never shares a texture with a server-named ``ship_image`` file."""
    def wrapper(self, *args, **kwargs):
        ship_type = _ship_type_arg(args, kwargs)
        replacement = _replacement(ship_type)
        if replacement is not None:
            return ship_type, replacement
        return original(self, *args, **kwargs)
    wrapper.__name__ = getattr(original, "__name__", "wrapper")
    wrapper.__doc__ = getattr(original, "__doc__", None)
    return wrapper


def _seed_cache(host):
    cache = getattr(host, "_ship_raw_cache", None)
    if not isinstance(cache, dict):
        return
    for slug, surface in _images.items():
        if surface is not None:
            cache[slug] = surface
            _seeded[slug] = surface


def _on_startup(host, pygame, screen):
    global _patched_class

    _load_images(pygame, _install_path[0])
    if not any(surface is not None for surface in _images.values()):
        return

    cls = type(host)
    _patched_class = cls
    _host[0] = host
    hooked = []
    for name in _HOOKS:
        original = getattr(cls, name, None)
        if original is None or not callable(original):
            continue
        wrap = _wrap_picture_for if name == "_ship_picture_for" else _wrap_picture
        _originals[name] = (original, name in cls.__dict__)
        setattr(cls, name, wrap(original))
        hooked.append(name)
    _seed_cache(host)
    if _logger[0] is not None:
        if hooked:
            _logger[0].info("star-weebs: hooked %s", ", ".join(hooked))
        else:
            _logger[0].warning(
                "star-weebs: no ship-picture hooks found on %s; only the "
                "picture cache was seeded", cls.__name__)


def _on_shutdown(**_kwargs):
    if _patched_class is not None:
        for name, (original, was_own) in _originals.items():
            try:
                if was_own:
                    setattr(_patched_class, name, original)
                else:
                    delattr(_patched_class, name)
            except Exception:
                pass
        _originals.clear()
    cache = getattr(_host[0], "_ship_raw_cache", None)
    if isinstance(cache, dict):
        for slug, surface in _seeded.items():
            if cache.get(slug) is surface:
                del cache[slug]
    _seeded.clear()


def apply(api):
    _install_path[0] = api.install_path
    _logger[0] = getattr(api, "logger", None)
    api.on("client.startup", _on_startup)
    api.on("loader.shutdown", _on_shutdown)
    api.logger.info("star-weebs ready, waiting for client.startup")
