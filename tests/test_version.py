"""The package version is never behind the newest release tag in its own history (v0.3.0 was tagged while
__version__ still said 0.2.0, so the server's update notice and the eval both read the wrong release)."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import __version__  # noqa: E402


def as_tuple(v):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(\.dev|a|b|rc)(\d+))?", v)
    if match is None:
        raise ValueError(f"unsupported version: {v}")
    # A development build of the next release is newer than every older
    # release, but still precedes the final release with the same numbers.
    major, minor, patch, phase, number = match.groups()
    order = {'.dev': 0, 'a': 1, 'b': 2, 'rc': 3, None: 4}
    return (int(major), int(minor), int(patch), order[phase], int(number or 0))


class Version(unittest.TestCase):
    def test_development_version_still_respects_release_order(self):
        self.assertGreater(as_tuple("0.9.0.dev0"), as_tuple("0.4.5"))
        self.assertLess(as_tuple("0.9.0.dev0"), as_tuple("0.9.0"))
        self.assertLess(as_tuple("0.4.4"), as_tuple("0.4.5"))

    def test_valid_release_candidates_follow_packaging_phase_order(self):
        versions = ['3.0.0.dev1', '3.0.0.dev2', '3.0.0a1', '3.0.0b1',
                    '3.0.0rc1', '3.0.0rc2', '3.0.0']
        for before, after in zip(versions, versions[1:]):
            self.assertLess(as_tuple(before), as_tuple(after))
        for invalid in ('3.0', '3.0.0garbage', '3.0.0rc-1', '3.0.0rc'):
            with self.assertRaises(ValueError):
                as_tuple(invalid)

    def test_version_not_behind_an_ancestor_tag(self):
        try:
            tags = subprocess.run(["git", "tag", "--merged", "HEAD", "--list", "v*"], cwd=ROOT, capture_output=True,
                                  text=True, timeout=20, check=True).stdout.split()
        except (OSError, subprocess.SubprocessError):
            self.skipTest("no git history here")
        rel = [t[1:] for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
        if not rel:
            self.skipTest("no release tag in this checkout")
        newest = max(rel, key=as_tuple)
        self.assertGreaterEqual(as_tuple(__version__), as_tuple(newest),
                                f"__version__ {__version__} is behind the release tag v{newest}")


if __name__ == "__main__":
    unittest.main()
