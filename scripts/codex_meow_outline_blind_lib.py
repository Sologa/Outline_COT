import ast
import json
import textwrap
from pathlib import Path


SYSTEM_PROMPT = (
    "You are a scientific writing assistant. Produce a structured outline "
    "based on the article metadata and references provided."
)

USER_PROMPT_TEMPLATE = textwrap.dedent(
    """
    Write an outline for a literature review based on the given title and references.
    If I set Output_references to False, do not generate the contents of the ref list for me
    Format: {{"level": 1, "numbering": "1", "title": "Introduction", "ref": ["key1","key2"...]}}
    Output_references: True
    Title:
    {title}
    {target_paper_abstract_block}References:
    {references_json}
    """
).strip()


def load_blind_payload(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")

    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raise ValueError(f"{path} is missing object field 'meta'")

    title = meta.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"{path} is missing non-empty meta.title")

    target_abstract = meta.get("abstract")
    if isinstance(target_abstract, str):
        target_abstract = target_abstract.strip()
    else:
        target_abstract = ""

    ref_meta = raw.get("ref_meta")
    if not isinstance(ref_meta, list):
        raise ValueError(f"{path} is missing list field 'ref_meta'")

    paper_id = raw.get("paper_id") or path.parent.name
    if not isinstance(paper_id, str) or not paper_id.strip():
        raise ValueError(f"{path} is missing non-empty paper_id")

    return {
        "paper_id": paper_id.strip(),
        "title": title.strip(),
        "target_abstract": target_abstract,
        "reference_metadata": ref_meta,
    }


def build_prompt(
    paper_id: str,
    title: str,
    reference_metadata: list[dict],
    *,
    target_meta_abstract: str | None = None,
    include_meta_abstract: bool = False,
) -> str:
    references_json = json.dumps(reference_metadata, ensure_ascii=False, indent=2)
    target_paper_abstract_block = ""
    if include_meta_abstract and isinstance(target_meta_abstract, str) and target_meta_abstract.strip():
        target_paper_abstract_block = f"Target Paper Abstract:\n{target_meta_abstract.strip()}\n"
    faithful_user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        target_paper_abstract_block=target_paper_abstract_block,
        references_json=references_json,
    )
    return textwrap.dedent(
        f"""
        You are running a constrained blind outline-generation test for paper `{paper_id}`.

        Hard restrictions:
        - Do not read `AGENTS.md`.
        - Do not read any local files.
        - The only allowed source file would be `meow_reconstructed_blind.json`, and its relevant contents have already been embedded below.
        - Do not use web search, external tools, or outside knowledge.
        - Do not add explanations, code fences, or any text before or after the outline.

        Faithful released MEOW system prompt:
        {SYSTEM_PROMPT}

        Faithful released MEOW user prompt:
        {faithful_user_prompt}
        """
    ).strip() + "\n"


def parse_outline_response(raw_text: str) -> list[dict]:
    cleaned = _strip_code_fences(raw_text)
    parsed = _parse_as_json_or_python(cleaned)
    return normalize_outline_items(parsed)


def write_normalized_outline(raw_text: str, output_path: Path) -> None:
    normalized = parse_outline_response(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _parse_as_json_or_python(text: str):
    errors = []
    for parser_name, parser in (("json", json.loads), ("python", ast.literal_eval)):
        try:
            return parser(text)
        except Exception as exc:  # pragma: no cover - error text only
            errors.append(f"{parser_name}: {exc}")
    linewise = _parse_linewise_objects(text)
    if linewise is not None:
        return linewise

    raise ValueError("Could not parse outline response as JSON or Python literal: " + "; ".join(errors))


def _parse_linewise_objects(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    items = []
    for index, line in enumerate(lines):
        parsed_line = None
        line_errors = []
        for parser_name, parser in (("json", json.loads), ("python", ast.literal_eval)):
            try:
                parsed_line = parser(line)
                break
            except Exception as exc:
                line_errors.append(f"{parser_name}: {exc}")
        if parsed_line is None:
            return None
        if not isinstance(parsed_line, dict):
            raise ValueError(
                f"Linewise outline item {index} must be an object, got {type(parsed_line).__name__}; "
                + "; ".join(line_errors)
            )
        items.append(parsed_line)
    return items


def normalize_outline_items(data) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError(f"Outline response must be a list, got {type(data).__name__}")

    normalized = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Outline item {index} must be an object, got {type(item).__name__}")

        for field in ("level", "numbering", "title", "ref"):
            if field not in item:
                raise ValueError(f"Outline item {index} is missing required field '{field}'")

        try:
            level = int(item["level"])
        except Exception as exc:
            raise ValueError(f"Outline item {index} has invalid level: {exc}") from exc
        if level < 1:
            raise ValueError(f"Outline item {index} has invalid level {level}; expected >= 1")

        refs = item["ref"]
        if not isinstance(refs, list):
            raise ValueError(f"Outline item {index} field 'ref' must be a list")

        normalized.append(
            {
                "level": level,
                "numbering": str(item["numbering"]),
                "title": str(item["title"]),
                "ref": [str(ref) for ref in refs],
            }
        )

    return normalized
