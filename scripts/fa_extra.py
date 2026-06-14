from pathlib import Path

EXTRA = {
    "&#10003;": "fa-check",
    "&#10007;": "fa-xmark",
    "&#128424;": "fa-print",
    "&#8681;": "fa-download",
    "&#8592;": "fa-arrow-left",
    "&#128465;": "fa-trash",
    "&#128190;": "fa-floppy-disk",
    "&#128260;": "fa-arrows-rotate",
    "&#10060;": "fa-circle-xmark",
    "&#128202;": "fa-chart-column",
    "&#129302;": "fa-robot",
    "&#128197;": "fa-calendar",
    "&#10004;": "fa-check",
    "&#9878;": "fa-scale-balanced",
    "&#128246;": "fa-comment-sms",
    "&#128065;": "fa-eye",
    "&#128220;": "fa-clock-rotate-left",
    "&#9432;": "fa-circle-info",
    "&#10148;": "fa-paper-plane",
    "&#128075;": "fa-hand",
}


def ic(fa: str) -> str:
    return f'<i class="fa-solid {fa}" aria-hidden="true"></i>'


root = Path(__file__).resolve().parents[1] / "templates"
for p in root.rglob("*.html"):
    t = p.read_text(encoding="utf-8")
    n = t
    for ent, fa in EXTRA.items():
        if ent in n:
            n = n.replace(ent, ic(fa) + " ")
    if n != t:
        p.write_text(n, encoding="utf-8")
        print(p.relative_to(root))
