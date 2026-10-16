"""
Cross-run cache of per-file analysis results.

A repeat scan of an unchanged tree costs exactly what the first scan did, which
is the wrong trade for the edit-run-edit loop. This stores each file's own
results - its parsed blocks, complexity findings, size metrics, lint findings
and comments - keyed by a hash of that file's content, so a repeat scan only
analyses the files that actually changed.

Only file-local results are cached. Duplicate grouping is deliberately *not*:
it compares blocks across files, so it always runs over the combined block set.

Safety is the point of the design, because a cache that answers with stale
findings is worse than no cache at all:

* The whole cache is discarded when the schema, the scan root, or any setting
  that affects a per-file result changes, so it can never answer for a
  different configuration.
* A file whose content hash does not match is always re-analysed.
* An unreadable or malformed cache is ignored with a warning, never trusted.
* Nothing is written unless caching was asked for.
"""

import hashlib
import json
import sys
from pathlib import Path

CACHE_SCHEMA = 1
CACHE_FILENAME = ".replicheck-cache.json"

# Settings that change what a per-file analysis produces. Any difference
# invalidates every entry.
FINGERPRINT_KEYS = (
    "min_size",
    "complexity_threshold",
    "large_file_threshold",
    "large_class_threshold",
    "flake8_codes",
    "extensions",
)


def file_digest(path) -> str:
    """SHA-256 of the file's bytes, or "" when it cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


class ScanCache:
    """Per-file results from a previous scan, keyed by content hash."""

    def __init__(self, cache_file, root, settings):
        self.cache_file = Path(cache_file)
        self.root = str(Path(root).resolve())
        self.settings = {key: settings.get(key) for key in FINGERPRINT_KEYS}
        self.entries = {}
        self.hits = 0
        self.misses = 0
        self._resolved = {}
        self._digests = {}

    # -- persistence ------------------------------------------------------

    def load(self):
        """Read the cache, discarding it wholesale if it does not apply."""
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            print(
                f"[WARN] ignoring unreadable cache {self.cache_file}: {exc}",
                file=sys.stderr,
            )
            return

        if not isinstance(raw, dict):
            return
        if raw.get("schema") != CACHE_SCHEMA:
            return
        if raw.get("root") != self.root:
            # A cache from a different tree must never answer for this one.
            return
        if raw.get("settings") != self.settings:
            # Any change to the settings changes what a file's results mean.
            return
        entries = raw.get("entries")
        if isinstance(entries, dict):
            self.entries = entries

    def save(self):
        payload = {
            "schema": CACHE_SCHEMA,
            "root": self.root,
            "settings": self.settings,
            "entries": self.entries,
        }
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print(
                f"[WARN] could not write cache {self.cache_file}: {exc}",
                file=sys.stderr,
            )

    # -- lookups ----------------------------------------------------------

    def key_for(self, path):
        """The cache key for a path, or None if it sits outside the scan root."""
        text = str(path)
        resolved = self._resolved.get(text)
        if resolved is None:
            try:
                resolved = str(Path(path).resolve().relative_to(self.root))
            except (OSError, ValueError):
                resolved = ""
            self._resolved[text] = resolved
        return resolved or None

    def get(self, path):
        """
        Cached artifacts for an unchanged file, or None to re-analyse it.

        A hash mismatch means the file changed, so its stored results describe
        a different file and must not be used.
        """
        key = self.key_for(path)
        if key is None:
            self.misses += 1
            return None
        entry = self.entries.get(key)
        if not isinstance(entry, dict):
            self.misses += 1
            return None
        digest = file_digest(path)
        if not digest or entry.get("digest") != digest:
            self.misses += 1
            return None
        self._digests[key] = digest
        self.hits += 1
        artifacts = entry.get("artifacts")
        return artifacts if isinstance(artifacts, dict) else {}

    def put(self, path, artifacts):
        key = self.key_for(path)
        if key is None:
            return
        digest = self._digests.get(key) or file_digest(path)
        if not digest:
            return
        self.entries[key] = {"digest": digest, "artifacts": artifacts}

    def prune_to(self, files):
        """Forget files that are no longer part of the scan."""
        keep = {key for key in (self.key_for(f) for f in files) if key}
        self.entries = {
            key: value for key, value in self.entries.items() if key in keep
        }
