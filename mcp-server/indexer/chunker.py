"""CogniLayer chunker — splits files into indexable chunks."""

import json
import re
from pathlib import Path


def chunk_markdown(content: str, file_path: str) -> list[dict]:
    """Split markdown by headings (H1/H2/H3). Each section = one chunk."""
    chunks = []
    # Split by headings
    sections = re.split(r'^(#{1,3}\s+.+)$', content, flags=re.MULTILINE)

    current_title = Path(file_path).name
    current_content = []
    chunk_idx = 0

    for part in sections:
        if re.match(r'^#{1,3}\s+', part):
            # Save previous section if it has content
            if current_content:
                text = "\n".join(current_content).strip()
                if text:
                    for sub_chunk in _split_large(text, current_title, chunk_idx):
                        chunks.append(sub_chunk)
                        chunk_idx += 1
            current_title = part.strip().lstrip("#").strip()
            current_content = []
        else:
            current_content.append(part)

    # Last section
    if current_content:
        text = "\n".join(current_content).strip()
        if text:
            for sub_chunk in _split_large(text, current_title, chunk_idx):
                chunks.append(sub_chunk)
                chunk_idx += 1

    return chunks


def chunk_json(content: str, file_path: str) -> list[dict]:
    """Chunk JSON files. package.json gets special treatment."""
    chunks = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [{"section_title": Path(file_path).name, "content": content[:2000], "chunk_index": 0}]

    fname = Path(file_path).name

    if fname == "package.json":
        # Special: extract key sections
        for key in ["name", "version", "scripts", "dependencies", "devDependencies"]:
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    text = json.dumps(val, indent=2)
                else:
                    text = str(val)
                chunks.append({
                    "section_title": f"{fname} — {key}",
                    "content": text[:2000],
                    "chunk_index": len(chunks)
                })
    else:
        # Generic: top-level keys as chunks
        if isinstance(data, dict):
            for key, val in data.items():
                text = json.dumps(val, indent=2) if isinstance(val, (dict, list)) else str(val)
                chunks.append({
                    "section_title": f"{fname} — {key}",
                    "content": text[:2000],
                    "chunk_index": len(chunks)
                })
        else:
            chunks.append({
                "section_title": fname,
                "content": content[:2000],
                "chunk_index": 0
            })

    return chunks or [{"section_title": fname, "content": content[:2000], "chunk_index": 0}]


def chunk_yaml(content: str, file_path: str) -> list[dict]:
    """Chunk YAML/TOML by top-level keys."""
    chunks = []
    fname = Path(file_path).name
    current_key = fname
    current_lines = []
    chunk_idx = 0

    for line in content.splitlines():
        # Top-level key (no leading whitespace, ends with :)
        if line and not line[0].isspace() and ":" in line:
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    chunks.append({
                        "section_title": current_key,
                        "content": text[:2000],
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
            current_key = line.split(":")[0].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append({
                "section_title": current_key,
                "content": text[:2000],
                "chunk_index": chunk_idx
            })

    return chunks or [{"section_title": fname, "content": content[:2000], "chunk_index": 0}]


def chunk_text(content: str, file_path: str) -> list[dict]:
    """Generic text chunking by paragraphs/size."""
    fname = Path(file_path).name
    if len(content) <= 2000:
        return [{"section_title": fname, "content": content, "chunk_index": 0}]

    chunks = []
    for sub in _split_large(content, fname, 0):
        chunks.append(sub)
    return chunks


def chunk_file(content: str, file_path: str) -> list[dict]:
    """Auto-detect file type and chunk accordingly."""
    ext = Path(file_path).suffix.lower()

    if ext == ".md":
        return chunk_markdown(content, file_path)
    elif ext == ".json":
        return chunk_json(content, file_path)
    elif ext in (".yaml", ".yml", ".toml"):
        return chunk_yaml(content, file_path)
    else:
        return chunk_text(content, file_path)


def _split_large(text: str, title: str, start_idx: int,
                 max_chars: int = 2000, overlap: int = 200) -> list[dict]:
    """Split text larger than max_chars into overlapping sub-chunks."""
    if len(text) <= max_chars:
        return [{"section_title": title, "content": text, "chunk_index": start_idx}]

    chunks = []
    pos = 0
    idx = start_idx
    while pos < len(text):
        end = min(pos + max_chars, len(text))
        chunk_text_val = text[pos:end]
        chunks.append({
            "section_title": f"{title} (part {idx - start_idx + 1})",
            "content": chunk_text_val,
            "chunk_index": idx
        })
        idx += 1
        pos = end - overlap if end < len(text) else end

    return chunks
