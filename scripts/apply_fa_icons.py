"""Replace HTML entity icons with Font Awesome across app templates."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "templates"

IC = 'i class="fa-solid {fa}{extra}" aria-hidden="true"></i>'


def ic(fa: str, extra: str = "") -> str:
    ex = f" {extra}" if extra else ""
    return f"<{IC.format(fa=fa, extra=ex)}>"


ENTITY_FA = {
    "&#9681;": "fa-gauge-high",
    "&#9776;": "fa-table-cells",
    "&#9673;": "fa-users",
    "&#128179;": "fa-id-card",
    "&#9699;": "fa-sitemap",
    "&#36;": "fa-piggy-bank",
    "&#8381;": "fa-hand-holding-dollar",
    "&#9733;": "fa-chart-pie",
    "&#128196;": "fa-file-invoice-dollar",
    "&#9783;": "fa-calculator",
    "&#8593;": "fa-arrow-trend-up",
    "&#8595;": "fa-arrow-trend-down",
    "&#9998;": "fa-calendar-days",
    "&#9746;": "fa-check-to-slot",
    "&#9745;": "fa-clipboard-check",
    "&#9888;": "fa-triangle-exclamation",
    "&#9997;": "fa-pen-to-square",
    "&#128227;": "fa-bullhorn",
    "&#9992;": "fa-paper-plane",
    "&#9881;": "fa-gear",
    "&#43;": "fa-plus",
    "&#9203;": "fa-hourglass-half",
    "&#128276;": "fa-bell",
    "&#128100;": "fa-user",
    "&#128682;": "fa-right-from-bracket",
    "&#9672;": "fa-circle-check",
}


def process_text(text: str) -> str:
    # Messages vs payments
    def msg_or_pay(m):
        line = m.group(0)
        fa = "fa-envelope" if re.search(r"Ujumbe|Message|inbox|Messages", line, re.I) else "fa-money-bill-wave"
        return line.replace("&#9993;", ic(fa, "nav-icon"))

    text = re.sub(r"^.*&#9993;.*$", msg_or_pay, text, flags=re.M)

    # nav-item
    for ent, fa in ENTITY_FA.items():
        text = re.sub(
            rf'(class="nav-item"[^>]*>)\s*{re.escape(ent)}\s*',
            rf'\1{ic(fa, "nav-icon")} ',
            text,
        )
        text = re.sub(
            rf'(class="nav-item[^"]*"[^>]*>)\s*{re.escape(ent)}\s*',
            rf'\1{ic(fa, "nav-icon")} ',
            text,
        )

    # nav-section with star -> chairperson
    text = text.replace(
        '<div class="nav-section">&#9733;',
        f'<div class="nav-section">{ic("fa-user-tie")} ',
    )

    # stat-icon
    for ent, fa in ENTITY_FA.items():
        text = re.sub(
            rf'(<div class="stat-icon[^"]*">)\s*{re.escape(ent)}\s*(</div>)',
            rf'\1{ic(fa)}\2',
            text,
        )

    # empty-icon
    for ent, fa in ENTITY_FA.items():
        text = re.sub(
            rf'(<div class="empty-icon">)\s*{re.escape(ent)}\s*(</div>)',
            rf'\1{ic(fa)}\2',
            text,
        )

    # hamburger
    text = text.replace('id="hamburger">&#9776;', f'id="hamburger">{ic("fa-bars")}')

    # notif badges (no nav-icon)
    text = text.replace("&#128276;", ic("fa-bell"))
    text = re.sub(
        r'(notif-badge[^>]*>[\s\S]*?)(fa-envelope|fa-money-bill-wave)',
        lambda m: m.group(0),
        text,
    )

    # buttons: entity before span or text
    for ent, fa in ENTITY_FA.items():
        text = re.sub(rf'>\s*{re.escape(ent)}\s*<span', f">{ic(fa)} <span", text)
        text = re.sub(rf'btn[^>]*>\s*{re.escape(ent)}\s*', lambda m: m.group(0).replace(ent, ic(fa) + " "), text)

    # remaining entities
    for ent, fa in ENTITY_FA.items():
        if ent in text:
            text = text.replace(ent, ic(fa) + " ")

    # cleanup double spaces in tags
    text = re.sub(r"\s+</i>\s+</i>", "</i>", text)
    return text


def main():
    changed = []
    for path in ROOT.rglob("*.html"):
        raw = path.read_text(encoding="utf-8")
        if "&#" not in raw:
            continue
        new = process_text(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files")


if __name__ == "__main__":
    main()
