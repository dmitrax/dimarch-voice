import re
from pathlib import Path


def clean_text(raw: str) -> str:
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        line = re.sub(r"\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]", "", line)
        line = line.strip()
        if line:
            cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def write_markdown(text: str, output: Path, meta: dict | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if meta:
        frontmatter = "---\n"
        for key, value in meta.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        text = frontmatter + text
    output.write_text(text, encoding="utf-8")
