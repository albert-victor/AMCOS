"""Convert 'Swahili / English' in HTML text nodes to {% t "Swahili" "English" %}."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "templates"
SKIP = {"welcome.html", "register_member.html", "receipt.html"}


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def convert(content: str) -> str:
    def repl(m: re.Match) -> str:
        sw, en = m.group(1).strip(), m.group(2).strip()
        if "{%" in sw or "{%" in en or "}}" in sw:
            return m.group(0)
        if len(sw) > 150 or len(en) > 150:
            return m.group(0)
        return f">{{% t \"{esc(sw)}\" \"{esc(en)}\" %}}<"

    return re.sub(r">([^<>{}]+?)\s/\s([^<>{}]+?)<", repl, content)


def main():
    changed = []
    for path in ROOT.rglob("*.html"):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        new = convert(text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(ROOT.parent))
    print(f"Updated {len(changed)} files")
    for p in sorted(changed):
        print(f"  {p}")


if __name__ == "__main__":
    main()
