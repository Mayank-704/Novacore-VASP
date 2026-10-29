"""Exchange label files. CSV columns: address,entity,type,source,verified (lines starting with # are skipped)."""
import csv
from pathlib import Path


def load_labels(*paths):
    labels = {}
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding='utf-8').splitlines() if line.strip() and not line.startswith('#')]
        for row in csv.DictReader(lines):
            address = row['address'].strip()
            labels[address] = {'entity': row['entity'].strip(), 'type': row['type'].strip(),
                               'source': row['source'].strip(),
                               'verified': row['verified'].strip().lower() in ('1', 'true', 'yes')}
    return labels
