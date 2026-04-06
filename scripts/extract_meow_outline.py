#!/usr/bin/env python3

import argparse
import json
import os
import re
from pathlib import Path


BACK_MATTER_KEYWORDS = (
    "acknowledgment",
    "acknowledgement",
    "appendix",
    "appendices",
    "references",
    "bibliography",
    "author contribution",
    "author contributions",
    "funding",
    "funding statement",
    "declaration of interest",
    "declaration of competing interest",
    "conflict of interest",
    "conflicts of interest",
    "ethics statement",
    "ethics approval",
    "data availability",
    "code availability",
)


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)


def parse_single_braced_arg(text: str, brace_start: int) -> tuple[str | None, int]:
    if brace_start >= len(text) or text[brace_start] != "{":
        return None, brace_start

    depth = 0
    i = brace_start
    while i < len(text):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start + 1 : i], i + 1
        i += 1
    return text[brace_start + 1 : i], i


def preprocess_color_edits(text: str) -> str:
    if r"\usepackage[suppress]{color-edits}" not in text:
        return text

    authors = re.findall(r"\\addauthor\{([^}]+)\}\{[^}]+\}", text)
    if not authors:
        return text

    macro_behavior: dict[str, str] = {}
    for author in authors:
        macro_behavior[f"{author}edit"] = "unwrap"
        macro_behavior[f"{author}delete"] = "drop"
        macro_behavior[f"{author}comment"] = "drop"
        macro_behavior[f"{author}margincomment"] = "drop"
        macro_behavior[f"{author}addition"] = "drop"

    macro_names = sorted(macro_behavior, key=len, reverse=True)

    def apply_once(source: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(source):
            if source[i] != "\\":
                out.append(source[i])
                i += 1
                continue

            matched = next(
                (name for name in macro_names if source.startswith(f"\\{name}", i)),
                None,
            )
            if matched is None:
                out.append(source[i])
                i += 1
                continue

            arg_start = i + 1 + len(matched)
            while arg_start < len(source) and source[arg_start].isspace():
                arg_start += 1

            arg, end = parse_single_braced_arg(source, arg_start)
            if arg is None:
                out.append(source[i])
                i += 1
                continue

            if macro_behavior[matched] == "unwrap":
                out.append(arg)
            else:
                out.append("\n" * arg.count("\n"))
            i = end

        return "".join(out)

    previous = None
    while previous != text:
        previous = text
        text = apply_once(text)
    return text


def find_main_tex_file(tex_files: list[Path]) -> Path | None:
    candidates: list[tuple[Path, int]] = []
    for tex_file in tex_files:
        try:
            content = tex_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        score = 0
        if re.search(r"\\begin\s*\{\s*document\s*\}", content):
            score += 10
        if re.search(r"\\documentclass", content):
            score += 8
        if re.search(r"\\maketitle", content):
            score += 5
        if re.search(r"\\title", content):
            score += 4
        if re.search(r"\\author", content):
            score += 4
        if re.search(r"\\bibliography", content) or re.search(r"\\bibliographystyle", content):
            score += 3

        include_count = len(re.findall(r"\\input\s*\{", content))
        include_count += len(re.findall(r"\\include\s*\{", content))
        score += min(include_count, 5)
        candidates.append((tex_file, score))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def resolve_include_path(base_dir: Path, raw_name: str) -> Path:
    filename = raw_name.strip()
    if not filename.endswith(".tex"):
        filename = f"{filename}.tex"
    return (base_dir / filename).resolve()


def merge_tex_content(main_tex_file: Path, visited: set[Path] | None = None) -> str:
    if visited is None:
        visited = set()
    main_tex_file = main_tex_file.resolve()
    if main_tex_file in visited:
        return ""
    visited.add(main_tex_file)

    try:
        content = main_tex_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    base_dir = main_tex_file.parent
    patterns = [
        r"\\input\s*\{\s*([^}]+)\s*\}",
        r"\\include\s*\{\s*([^}]+)\s*\}",
    ]

    for pattern in patterns:
        offset = 0
        for match in re.finditer(pattern, content):
            filepath = resolve_include_path(base_dir, match.group(1))
            if not filepath.exists():
                continue
            included = merge_tex_content(filepath, visited)
            replacement = (
                f"% START OF INCLUDED FILE: {filepath.name}\n"
                f"{included}\n"
                f"% END OF INCLUDED FILE: {filepath.name}"
            )
            start = match.start() + offset
            end = match.end() + offset
            content = content[:start] + replacement + content[end:]
            offset += len(replacement) - (end - start)
    return content


def detect_level_hierarchy(tex_content: str) -> list[str]:
    doc_class = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]*)\}", tex_content)
    if not doc_class:
        return ["chapter", "section", "subsection", "subsubsection"]

    doc_type = doc_class.group(1).strip()
    if doc_type == "article":
        return ["section", "subsection", "subsubsection", "paragraph"]
    return ["chapter", "section", "subsection", "subsubsection"]


def collect_section_patterns(tex_content: str) -> dict[str, str]:
    patterns = {
        "chapter": r"\\chapter(?:\*|\s*\[[^\]]*\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}",
        "section": r"\\section(?:\*|\s*\[[^\]]*\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}",
        "subsection": r"\\subsection(?:\*|\s*\[[^\]]*\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}",
        "subsubsection": r"\\subsubsection(?:\*|\s*\[[^\]]*\])?\s*\{((?:[^{}]|(?:\{[^{}]*\}))*)\}",
    }

    custom_section_pattern = r"\\(?:new|renew)command\s*\{\\([a-zA-Z]+section[a-zA-Z]*)\}"
    for cmd in re.findall(custom_section_pattern, tex_content):
        patterns[cmd] = (
            fr"\\{cmd}(?:\*|\s*\[[^\]]*\])?\s*\{{((?:[^{{}}]|(?:\{{[^{{}}]*\}}))*)\}}"
        )
    return patterns


def clean_title(title: str) -> str:
    title = re.sub(r"\\label\s*\{[^}]*\}", "", title)
    title = re.sub(
        r"\\(?:cite|ref|pageref|footnote|url|href|thanks)[a-zA-Z*]*\s*(\[[^\]]*\]){0,2}\s*\{[^}]*\}",
        "",
        title,
    )
    title = re.sub(r"\\texorpdfstring\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\1", title)

    # Unwrap simple formatting commands while keeping their contents.
    unwrap_pattern = re.compile(r"\\[a-zA-Z@]+(?:\*|\s*\[[^\]]*\])?\s*\{([^{}]*)\}")
    previous = None
    while previous != title:
        previous = title
        title = unwrap_pattern.sub(r"\1", title)

    title = re.sub(r"\\[a-zA-Z@]+", "", title)
    title = title.replace("~", " ")
    title = title.replace("{", "").replace("}", "")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def extract_sections(tex_content: str) -> list[dict]:
    patterns = collect_section_patterns(tex_content)
    level_hierarchy = detect_level_hierarchy(tex_content)

    begin_doc = re.search(r"\\begin\{document\}", tex_content)
    start_idx = begin_doc.end() if begin_doc else 0
    end_doc = re.search(r"\\end\{document\}", tex_content)
    end_idx = end_doc.start() if end_doc else len(tex_content)

    body = preprocess_color_edits(strip_comments(tex_content[start_idx:end_idx]))

    sections: list[dict] = []
    for level, pattern in patterns.items():
        for match in re.finditer(pattern, body):
            title = clean_title(match.group(1))
            if not title:
                continue
            sections.append(
                {
                    "level": level,
                    "title": title,
                    "line_num": body.count("\n", 0, match.start()),
                    "char_pos": match.start(),
                    "char_end": match.end(),
                }
            )

    sections.sort(key=lambda item: item["char_pos"])
    structured_outline: list[dict] = []
    stack = [{"children": structured_outline, "level": "root"}]

    for section in sections:
        current_level = level_hierarchy.index(section["level"]) if section["level"] in level_hierarchy else 999
        while len(stack) > 1:
            parent_level = level_hierarchy.index(stack[-1]["level"]) if stack[-1]["level"] in level_hierarchy else -1
            if parent_level < current_level:
                break
            stack.pop()

        node = {
            "title": section["title"],
            "level": section["level"],
            "line_num": section["line_num"],
            "char_pos": section["char_pos"],
            "char_end": section["char_end"],
            "ref": [],
            "children": [],
        }
        stack[-1]["children"].append(node)
        stack.append(node)

    return structured_outline


def extract_citations(tex_content: str, outline: list[dict]) -> list[dict]:
    if not outline:
        return outline

    tex_content = preprocess_color_edits(strip_comments(tex_content))
    level_hierarchy = ["chapter", "section", "subsection", "subsubsection", "paragraph"]
    citation_patterns = [
        r"\\cite[a-zA-Z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}",
        r"\\text(?:cite|cquote)[a-zA-Z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}",
        r"\\parencite[a-zA-Z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}",
        r"\\footcite[a-zA-Z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}",
        r"\\autocite[a-zA-Z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]*)\}",
    ]

    markers: list[dict] = []

    def collect(sections: list[dict]) -> None:
        for section in sections:
            markers.append(
                {
                    "line": section["line_num"],
                    "level": section["level"],
                    "char_pos": section.get("char_pos", 0),
                    "char_end": section.get("char_end", 0),
                    "section": section,
                }
            )
            if section["children"]:
                collect(section["children"])

    collect(outline)
    markers.sort(key=lambda item: item["line"])

    for i, marker in enumerate(markers):
        current = marker["section"]
        current_level_idx = level_hierarchy.index(current["level"]) if current["level"] in level_hierarchy else 999
        start_char = marker["char_end"]
        end_char = len(tex_content)
        for next_marker in markers[i + 1 :]:
            next_level_idx = level_hierarchy.index(next_marker["level"]) if next_marker["level"] in level_hierarchy else -1
            if next_level_idx <= current_level_idx:
                end_char = next_marker["char_pos"]
                break

        section_text = tex_content[start_char:end_char]
        citations: list[str] = []
        for pattern in citation_patterns:
            for match in re.finditer(pattern, section_text):
                for cite in match.group(1).split(","):
                    cite = cite.strip()
                    if cite and cite not in citations:
                        citations.append(cite)
        current["ref"] = citations
    return outline


def slice_from_introduction(outline: list[dict]) -> list[dict]:
    idx = next(
        (
            i
            for i, item in enumerate(outline)
            if item.get("level") == "section" and item.get("title", "").strip().lower() == "introduction"
        ),
        None,
    )
    if idx is None:
        return outline
    return outline[idx:]


def is_back_matter(title: str) -> bool:
    title = title.strip().lower()
    return any(keyword in title for keyword in BACK_MATTER_KEYWORDS)


def filter_back_matter(outline: list[dict]) -> list[dict]:
    filtered: list[dict] = []
    for section in outline:
        if is_back_matter(section["title"]):
            continue
        node = {
            "title": section["title"],
            "level": section["level"],
            "line_num": section["line_num"],
            "ref": list(section.get("ref", [])),
            "children": filter_back_matter(section.get("children", [])),
        }
        filtered.append(node)
    return filtered


def truncate_after_conclusion(outline: list[dict]) -> list[dict]:
    truncated: list[dict] = []
    for section in outline:
        truncated.append(section)
        title = section.get("title", "").strip().lower()
        if "conclusion" in title or "conclusions" in title:
            break
    return truncated


def format_outline_flat(sections: list[dict], number_prefix: str = "", level: int = 1) -> list[dict]:
    outline: list[dict] = []
    for i, section in enumerate(sections):
        section_number = f"{number_prefix}{i + 1}" if not number_prefix else f"{number_prefix}.{i + 1}"
        entry = {
            "level": level,
            "numbering": section_number,
            "title": section["title"],
            "ref": list(section.get("ref", [])),
        }
        outline.append(entry)
        if section.get("children"):
            outline.extend(format_outline_flat(section["children"], section_number, level + 1))
    return outline


def extract_outline_from_tex_dir(tex_dir: Path) -> list[dict]:
    tex_files = sorted(tex_dir.rglob("*.tex"))
    if not tex_files:
        return []

    main_tex = find_main_tex_file(tex_files)
    if main_tex is None:
        main_tex = max(tex_files, key=lambda path: path.stat().st_size, default=None)
    if main_tex is None:
        return []

    merged = merge_tex_content(main_tex)
    if not merged.strip():
        merged = main_tex.read_text(encoding="utf-8", errors="ignore")

    merged = preprocess_color_edits(merged)

    begin_doc = re.search(r"\\begin\{document\}", merged)
    start_idx = begin_doc.end() if begin_doc else 0
    end_doc = re.search(r"\\end\{document\}", merged)
    end_idx = end_doc.start() if end_doc else len(merged)
    body = merged[start_idx:end_idx]

    outline = extract_sections(merged)
    outline = extract_citations(body, outline)
    outline = slice_from_introduction(outline)
    outline = filter_back_matter(outline)
    outline = truncate_after_conclusion(outline)
    return format_outline_flat(outline)


def write_outline_json(ref_dir: Path, outline: list[dict]) -> None:
    output_path = ref_dir / "outline.json"
    output_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")


def process_ref_dir(ref_dir: Path) -> tuple[bool, str]:
    tex_dir = ref_dir / "tex_src"
    if not tex_dir.exists():
        return False, f"{ref_dir.name}: missing tex_src"

    outline = extract_outline_from_tex_dir(tex_dir)
    if not outline:
        return False, f"{ref_dir.name}: no outline extracted"

    write_outline_json(ref_dir, outline)
    return True, f"{ref_dir.name}: wrote {len(outline)} outline nodes"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract MEOW-style outlines from refs/*/tex_src")
    parser.add_argument("--refs-root", default="refs", help="Root directory containing per-paper ref directories")
    parser.add_argument("--paper-id", action="append", help="Specific paper id(s) to process")
    args = parser.parse_args()

    refs_root = Path(args.refs_root).resolve()
    if not refs_root.exists():
        raise SystemExit(f"refs root does not exist: {refs_root}")

    if args.paper_id:
        ref_dirs = [refs_root / paper_id for paper_id in args.paper_id]
    else:
        ref_dirs = sorted(path for path in refs_root.iterdir() if path.is_dir())

    processed = 0
    failed = 0
    for ref_dir in ref_dirs:
        ok, message = process_ref_dir(ref_dir)
        print(message)
        if ok:
            processed += 1
        else:
            failed += 1

    print(f"done: {processed} succeeded, {failed} failed")
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
