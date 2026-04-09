import json
import sys
import textwrap
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from codex_meow_outline_blind_lib import parse_outline_response, write_normalized_outline


READONLY_TOOL_NAMES = [
    "run_shell_command",
    "write_file",
    "replace",
]


def render_readonly_policy_toml() -> str:
    tool_list = ", ".join(f'"{tool}"' for tool in READONLY_TOOL_NAMES)
    return textwrap.dedent(
        f"""
        [[rule]]
        toolName = [{tool_list}]
        decision = "deny"
        interactive = false
        priority = 999
        """
    ).strip() + "\n"


def extract_gemini_response_text(stdout_text: str) -> str:
    try:
        payload = json.loads(stdout_text)
    except Exception as exc:
        raise ValueError(f"Gemini stdout must be a JSON object: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Gemini stdout must decode to an object, got {type(payload).__name__}")

    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Gemini stdout JSON must contain a non-empty string field 'response'")
    return response


def parse_gemini_stdout(stdout_text: str) -> list[dict]:
    return parse_outline_response(extract_gemini_response_text(stdout_text))


def write_outline_from_gemini_stdout(stdout_text: str, output_path: Path) -> None:
    write_normalized_outline(extract_gemini_response_text(stdout_text), output_path)
