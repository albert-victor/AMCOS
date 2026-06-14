"""Fix remaining Sw / En in block titles, placeholders, titles."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "templates"


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def convert(content: str) -> str:
    content = re.sub(
        r'\{% block (page_title|title) %\}([^%]+?)\s/\s([^%]+?)\{% endblock %\}',
        lambda m: f'{{% block {m.group(1)} %}}{{% t "{esc(m.group(2).strip())}" "{esc(m.group(3).strip())}" %}}{{% endblock %}}',
        content,
    )
    content = re.sub(
        r'(placeholder|title|aria-label)="([^"]+?)\s/\s([^"]+?)"',
        lambda m: f'{m.group(1)}="{{% te \'{esc(m.group(2).strip())}\' \'{esc(m.group(3).strip())}\' %}}"',
        content,
    )
    return content


def main():
    changed = []
    for path in ROOT.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        new = convert(text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT.parent)))
    print(f"Updated {len(changed)} files")
    for p in sorted(changed):
        print(f"  {p}")


if __name__ == "__main__":
    main()
