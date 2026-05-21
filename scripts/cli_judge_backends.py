#!/usr/bin/env python3
import asyncio
import json
import shlex
import shutil
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional


JUDGE_BACKENDS = ("openai", "codex", "gemini")
CODEX_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")
GEMINI_POLICY_TOOL_NAMES = (
    "run_shell_command",
    "write_file",
    "replace",
)
CLI_PREVIEW_LIMIT = 4000


def build_openai_async_client(api_key: str, timeout: int, base_url: Optional[str]) -> Any:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'openai'. Install it before running LLM judge evaluation: "
            "`python3 -m pip install openai`."
        ) from exc

    kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)


def render_cli_judge_prompt(system_prompt: str, user_prompt: str) -> str:
    return textwrap.dedent(
        f"""
        You are running a constrained outline-judge task in non-interactive CLI mode.

        Hard restrictions:
        - Do not read or inspect any local files, directories, repositories, or workspace metadata.
        - Do not use shell commands, tools, MCP servers, web search, or external resources.
        - Do not rely on outside knowledge beyond the embedded judge prompts and outline content.
        - Return only the final JSON object required by the judge prompt.
        - Do not add code fences, preambles, or explanations.

        Embedded system prompt:
        {system_prompt}

        Embedded user prompt:
        {user_prompt}
        """
    ).strip() + "\n"


def render_gemini_readonly_policy_toml() -> str:
    tool_list = ", ".join(f'"{tool}"' for tool in GEMINI_POLICY_TOOL_NAMES)
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


def _preview(text: str) -> str:
    if len(text) <= CLI_PREVIEW_LIMIT:
        return text
    return text[:CLI_PREVIEW_LIMIT] + "\n...[truncated]..."


async def _communicate_subprocess(
    command: List[str],
    *,
    cwd: Path,
    timeout: int,
    stdin_text: Optional[str] = None,
) -> Dict[str, Any]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(stdin_text.encode("utf-8") if stdin_text is not None else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise TimeoutError(f"Judge subprocess timed out after {timeout}s") from exc

    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")
    return {
        "returncode": process.returncode,
        "stdout_text": stdout_text,
        "stderr_text": stderr_text,
        "cwd": str(cwd),
    }


async def run_judge_attempt(
    *,
    backend: str,
    model: str,
    messages: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    timeout: int,
    client: Any = None,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Any]:
    if backend == "openai":
        return await _run_openai_attempt(
            client=client,
            model=model,
            messages=messages,
            semaphore=semaphore,
            timeout=timeout,
        )
    if backend == "codex":
        return await _run_codex_attempt(
            model=model,
            messages=messages,
            semaphore=semaphore,
            timeout=timeout,
            reasoning_effort=reasoning_effort or "medium",
        )
    if backend == "gemini":
        return await _run_gemini_attempt(
            model=model,
            messages=messages,
            semaphore=semaphore,
            timeout=timeout,
        )
    raise ValueError(f"Unsupported judge backend '{backend}'")


async def _run_openai_attempt(
    *,
    client: Any,
    model: str,
    messages: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    timeout: int,
) -> Dict[str, Any]:
    if client is None:
        raise ValueError("OpenAI judge backend requires an initialized client")

    async with semaphore:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
            ),
            timeout=timeout,
        )

    raw_response = (response.choices[0].message.content or "").strip()
    return {
        "raw_response": raw_response,
        "transport_debug": {
            "backend": "openai",
            "message_count": len(messages),
        },
    }


async def _run_codex_attempt(
    *,
    model: str,
    messages: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    timeout: int,
    reasoning_effort: str,
) -> Dict[str, Any]:
    if shutil.which("codex") is None:
        raise RuntimeError("codex CLI is required but was not found on PATH")

    prompt = render_cli_judge_prompt(messages[0]["content"], messages[1]["content"])

    async with semaphore:
        with tempfile.TemporaryDirectory(prefix="codex-judge-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            workdir = tmpdir_path / "workspace"
            workdir.mkdir()
            last_message_path = tmpdir_path / "last_message.txt"
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "-C",
                str(workdir),
                "-m",
                model,
                "-s",
                "read-only",
                "-c",
                f'model_reasoning_effort="{reasoning_effort}"',
                "-o",
                str(last_message_path),
                "-",
            ]
            command_debug = command[:-1] + ["<prompt-from-stdin>"]
            completed = await _communicate_subprocess(
                command,
                cwd=workdir,
                timeout=timeout,
                stdin_text=prompt,
            )

            if completed["returncode"] != 0:
                raise RuntimeError(
                    "codex judge exited with status "
                    f"{completed['returncode']}: {completed['stderr_text'].strip() or completed['stdout_text'].strip()}"
                )
            if not last_message_path.exists():
                raise RuntimeError("codex judge did not produce a last-message file")

            raw_response = last_message_path.read_text(encoding="utf-8").strip()
            if not raw_response:
                raise RuntimeError("codex judge produced an empty final message")

            return {
                "raw_response": raw_response,
                "transport_debug": {
                    "backend": "codex",
                    "command": shlex.join(command_debug),
                    "cwd": completed["cwd"],
                    "stdout_preview": _preview(completed["stdout_text"]),
                    "stderr_preview": _preview(completed["stderr_text"]),
                    "reasoning_effort": reasoning_effort,
                },
            }


async def _run_gemini_attempt(
    *,
    model: str,
    messages: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    timeout: int,
) -> Dict[str, Any]:
    if shutil.which("gemini") is None:
        raise RuntimeError("gemini CLI is required but was not found on PATH")

    prompt = render_cli_judge_prompt(messages[0]["content"], messages[1]["content"])

    async with semaphore:
        with tempfile.TemporaryDirectory(prefix="gemini-judge-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            workdir = tmpdir_path / "workspace"
            workdir.mkdir()
            policy_path = tmpdir_path / "readonly.toml"
            policy_path.write_text(render_gemini_readonly_policy_toml(), encoding="utf-8")
            command = [
                "gemini",
                "-m",
                model,
                "-p",
                prompt,
                "--approval-mode",
                "yolo",
                "--policy",
                str(policy_path),
                "--output-format",
                "json",
            ]
            command_debug = [
                "gemini",
                "-m",
                model,
                "-p",
                "<prompt omitted>",
                "--approval-mode",
                "yolo",
                "--policy",
                str(policy_path),
                "--output-format",
                "json",
            ]
            completed = await _communicate_subprocess(
                command,
                cwd=workdir,
                timeout=timeout,
            )

            if completed["returncode"] != 0:
                raise RuntimeError(
                    "gemini judge exited with status "
                    f"{completed['returncode']}: {completed['stderr_text'].strip() or completed['stdout_text'].strip()}"
                )

            raw_response = extract_gemini_response_text(completed["stdout_text"]).strip()
            if not raw_response:
                raise RuntimeError("gemini judge produced an empty response field")

            return {
                "raw_response": raw_response,
                "transport_debug": {
                    "backend": "gemini",
                    "command": shlex.join(command_debug),
                    "cwd": completed["cwd"],
                    "stdout_preview": _preview(completed["stdout_text"]),
                    "stderr_preview": _preview(completed["stderr_text"]),
                },
            }
