"""Add verified knowledge data only; never install code or change client settings."""
import argparse
import os
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify bundle only; write nothing')
    parser.add_argument('--home', type=Path, help='explicit alternate user home')
    parser.add_argument('--harness-home', type=Path, help='explicit existing/custom harness data directory')
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    kit = runpy.run_path(str(bundle / 'install.py'), run_name='harness_knowledge_bootstrap')
    manifest = kit['validate'](bundle)
    if args.check:
        print('KNOWLEDGE VERIFIED: hashes, archive membership and exact bytes; no changes')
        return 0
    hh = (args.harness_home or (Path(os.environ['HARNESS_HOME']) if not args.home and
          os.environ.get('HARNESS_HOME') else (args.home or Path.home()) / '.agent-harness'))
    for path in (hh, hh / 'profile', hh / 'profile/knowledge'):
        if path.is_symlink():
            raise ValueError('knowledge destination contains a redirected directory')
    target = hh / 'profile/knowledge' / ('swe-core-' + manifest['knowledge']['sha256'][:16])
    kit['publish_knowledge'](bundle, manifest, target)
    print('Knowledge added at ' + str(target))
    print('Data only: no runtime, clients, permissions or hooks installed/changed. Open a fresh agent session.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print('Knowledge add-on refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
