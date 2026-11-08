"""Case-insensitive path helpers (the game data is authored for Windows)."""

import os


class CIResolver:
    """Resolve '/' or '\\' separated relative paths case-insensitively under a root."""

    def __init__(self, root):
        self.root = root
        self._listing = {}

    def _list(self, directory):
        lst = self._listing.get(directory)
        if lst is None:
            try:
                lst = {e.lower(): e for e in os.listdir(directory)}
            except OSError:
                lst = {}
            self._listing[directory] = lst
        return lst

    def resolve(self, rel):
        """Return the real path for rel, or None if it does not exist."""
        cur = self.root
        for part in rel.replace("\\", "/").split("/"):
            if not part or part == ".":
                continue
            hit = self._list(cur).get(part.lower())
            if hit is None:
                return None
            cur = os.path.join(cur, hit)
        return cur

    def relpath(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/")
