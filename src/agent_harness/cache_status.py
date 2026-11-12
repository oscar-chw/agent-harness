"""Read-only inventory, not a purge plan or a declaration that the harness is healthy."""
from pathlib import Path
import sqlite3

from .mcp.kb import default_kb_paths, discover_files


def inspect_cache(home, paths=None):
    home = Path(home)
    roots = [Path(p) for p in paths] if paths is not None else default_kb_paths(home)
    live = {str(p) for p, _ in discover_files(roots)}
    result = {"schema": "harness.cache-status/v1", "status": "ABSENT",
              "scope": {"configured_roots": len(roots), "discovered_files": len(live)},
              "eviction_authorized": False}
    path = home / "index.sqlite"
    con = None
    try:
        size = path.stat().st_size
        # Never initialize schemas, refresh source records, checkpoint, or VACUUM here.
        con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        page_size = con.execute("PRAGMA page_size").fetchone()[0]
        result["database"] = {
            "file_bytes": size,
            "page_bytes": page_size * con.execute("PRAGMA page_count").fetchone()[0],
            "free_page_bytes": page_size * con.execute("PRAGMA freelist_count").fetchone()[0]}
        counts = {label: {"files": 0, "sections": 0, "cached_section_bytes": 0}
                  for label in ("current_discovery", "outside_current_discovery")}

        def bucket(key):
            return counts["current_discovery" if key in live else "outside_current_discovery"]

        if "kb_files" in tables:
            for (key,) in con.execute("SELECT path FROM kb_files"):
                bucket(key)["files"] += 1
        if "kb_sections" in tables:
            for key, sections, nbytes in con.execute(
                    "SELECT path, COUNT(*), SUM(bytes) FROM kb_sections GROUP BY path"):
                row = bucket(key)
                row["sections"] += sections
                row["cached_section_bytes"] += nbytes or 0
        result["kb"] = counts
        result["sessions"] = {
            "files": con.execute("SELECT COUNT(*) FROM sess_files").fetchone()[0]
            if "sess_files" in tables else 0,
            "messages": con.execute("SELECT COUNT(*) FROM sess_msgs").fetchone()[0]
            if "sess_msgs" in tables else 0}
        allocated = {"kb": 0, "sessions": 0, "other": 0}
        try:
            for name, nbytes in con.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"):
                group = "kb" if name.startswith("kb_") else "sessions" if name.startswith("sess_") else "other"
                allocated[group] += nbytes
            result["allocated_bytes"] = allocated
        except sqlite3.OperationalError as error:
            if "no such table: dbstat" not in str(error):
                raise
            result["allocated_bytes"] = None  # dbstat is an optional SQLite build feature.
        result["status"] = "PRESENT"
    except FileNotFoundError:
        pass
    except (OSError, sqlite3.Error):
        # Errors may contain private paths. Report unavailable evidence, never an empty healthy index.
        result = {"schema": result["schema"], "status": "UNREADABLE",
                  "scope": result["scope"], "eviction_authorized": False}
    finally:
        if con is not None:
            con.close()
    return result
