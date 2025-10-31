from __future__ import annotations
import glob
import os
import re
from pathlib import Path

def get_next_version(path_prefix: str) -> str:
    """Return a new versioned Markdown filename for the given prefix.

    Example:
      path_prefix = "knowledge_base/curated/curated_entry"
      -> returns e.g. "knowledge_base/curated/curated_entry_v01.md" (or next)
    """
    prefix = Path(path_prefix)
    directory = prefix.parent
    stem = prefix.name
    pattern = str(directory / f"{stem}_v*.md")
    existing = glob.glob(pattern)
    nums = []
    for p in existing:
        m = re.search(r"_v(\d+)\.md$", os.path.basename(p))
        if m:
            try:
                nums.append(int(m.group(1)))
            except ValueError:
                pass
    next_num = max(nums) + 1 if nums else 1
    return str(directory / f"{stem}_v{next_num:02d}.md")
