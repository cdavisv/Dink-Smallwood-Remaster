"""Locate extraction inputs in the consolidated repo or the original sibling layout."""
from pathlib import Path


def default_data_repo(project_dir: Path) -> Path:
    parent = Path(project_dir).resolve().parent
    if (parent / 'bin' / 'dink').is_dir() and (parent / 'tools').is_dir():
        return parent
    return parent / 'Dink-Smallwood-Remaster'


if __name__ == '__main__':
    print(default_data_repo(Path(__file__).resolve().parent.parent))
