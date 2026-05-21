import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "cli_judge_backends.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cli_judge_backends", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CliJudgeBackendTests(unittest.TestCase):
    def test_render_cli_judge_prompt_embeds_prompts_and_restrictions(self):
        module = load_module()
        prompt = module.render_cli_judge_prompt("SYSTEM TEXT", "USER TEXT")
        self.assertIn("SYSTEM TEXT", prompt)
        self.assertIn("USER TEXT", prompt)
        self.assertIn("Do not read or inspect any local files", prompt)
        self.assertIn("Return only the final JSON object", prompt)

    def test_render_gemini_policy_denies_mutating_tools(self):
        module = load_module()
        policy = module.render_gemini_readonly_policy_toml()
        self.assertIn("run_shell_command", policy)
        self.assertIn("write_file", policy)
        self.assertIn("replace", policy)
        self.assertIn('decision = "deny"', policy)

    def test_extract_gemini_response_text_reads_response_field(self):
        module = load_module()
        payload = json.dumps({"response": '{"评价":"ok","结构_信息快速定位":8}'})
        self.assertEqual(module.extract_gemini_response_text(payload), '{"评价":"ok","结构_信息快速定位":8}')

    def test_extract_gemini_response_text_rejects_missing_response(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "non-empty string field 'response'"):
            module.extract_gemini_response_text(json.dumps({"session_id": "abc"}))


class CliJudgeBackendDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_judge_attempt_dispatches_to_openai_backend(self):
        module = load_module()
        fake_result = {"raw_response": '{"评价":"ok"}', "transport_debug": {"backend": "openai"}}
        with patch.object(module, "_run_openai_attempt", AsyncMock(return_value=fake_result)) as mocked:
            result = await module.run_judge_attempt(
                backend="openai",
                client=object(),
                model="gpt-5-nano",
                messages=[{"role": "system", "content": "a"}, {"role": "user", "content": "b"}],
                semaphore=module.asyncio.Semaphore(1),
                timeout=30,
                reasoning_effort=None,
            )
        self.assertEqual(result["transport_debug"]["backend"], "openai")
        mocked.assert_awaited_once()

    async def test_run_judge_attempt_dispatches_to_codex_backend(self):
        module = load_module()
        fake_result = {"raw_response": '{"评价":"ok"}', "transport_debug": {"backend": "codex"}}
        with patch.object(module, "_run_codex_attempt", AsyncMock(return_value=fake_result)) as mocked:
            result = await module.run_judge_attempt(
                backend="codex",
                client=None,
                model="gpt-5.4",
                messages=[{"role": "system", "content": "a"}, {"role": "user", "content": "b"}],
                semaphore=module.asyncio.Semaphore(1),
                timeout=30,
                reasoning_effort="xhigh",
            )
        self.assertEqual(result["transport_debug"]["backend"], "codex")
        mocked.assert_awaited_once()

    async def test_run_judge_attempt_dispatches_to_gemini_backend(self):
        module = load_module()
        fake_result = {"raw_response": '{"评价":"ok"}', "transport_debug": {"backend": "gemini"}}
        with patch.object(module, "_run_gemini_attempt", AsyncMock(return_value=fake_result)) as mocked:
            result = await module.run_judge_attempt(
                backend="gemini",
                client=None,
                model="gemini-3.1-pro-preview",
                messages=[{"role": "system", "content": "a"}, {"role": "user", "content": "b"}],
                semaphore=module.asyncio.Semaphore(1),
                timeout=30,
                reasoning_effort=None,
            )
        self.assertEqual(result["transport_debug"]["backend"], "gemini")
        mocked.assert_awaited_once()

    async def test_run_gemini_attempt_uses_yolo_approval_mode(self):
        module = load_module()
        completed = {
            "returncode": 0,
            "stdout_text": json.dumps({"response": '{"评价":"ok","结构_信息快速定位":8,"结构_详略得当":8,"内容_章节互斥性":8,"内容_逻辑深度":8,"内容_学术价值":8,"语用_描述性与简洁性":8}'}),
            "stderr_text": "",
            "cwd": "/tmp/workspace",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            policy_path = tmpdir_path / "readonly.toml"
            with (
                patch.object(module.shutil, "which", return_value="/usr/bin/gemini"),
                patch.object(module.tempfile, "TemporaryDirectory") as mocked_tmpdir,
                patch.object(module, "_communicate_subprocess", AsyncMock(return_value=completed)) as mocked_communicate,
            ):
                mocked_tmpdir.return_value.__enter__.return_value = str(tmpdir_path)
                mocked_tmpdir.return_value.__exit__.return_value = False
                result = await module._run_gemini_attempt(
                    model="gemini-3.1-pro-preview",
                    messages=[{"role": "system", "content": "system"}, {"role": "user", "content": "user"}],
                    semaphore=module.asyncio.Semaphore(1),
                    timeout=30,
                )

        command = mocked_communicate.await_args.args[0]
        self.assertIn("--approval-mode", command)
        approval_index = command.index("--approval-mode")
        self.assertEqual(command[approval_index + 1], "yolo")
        self.assertIn("--policy", command)
        self.assertEqual(result["transport_debug"]["backend"], "gemini")


if __name__ == "__main__":
    unittest.main()
