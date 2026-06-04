from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from feedback_agent.cli import _load_dotenv
from feedback_agent.llm import OptionalLLM


class OptionalLLMTest(unittest.TestCase):
    def test_api_key_enables_live_ai_by_default(self) -> None:
        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL": "demo-model",
        }
        with patch.dict(os.environ, env, clear=True):
            llm = OptionalLLM()

        self.assertTrue(llm.enabled)
        self.assertEqual(llm.model, "demo-model")
        self.assertEqual(llm.status()["mode"], "live-ai")

    def test_env_can_force_rules_mode(self) -> None:
        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "FEEDBACK_AGENT_USE_LLM": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            llm = OptionalLLM()

        self.assertFalse(llm.enabled)
        self.assertEqual(llm.status()["mode"], "rules")

    def test_dotenv_loader_sets_missing_values(self) -> None:
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("OPENAI_API_KEY=from-dotenv\nOPENAI_MODEL=dotenv-model\n")
            with patch.dict(os.environ, {}, clear=True):
                _load_dotenv(env_path)
                llm = OptionalLLM()

        self.assertTrue(llm.enabled)
        self.assertEqual(llm.model, "dotenv-model")

    def test_dotenv_loader_does_not_override_exported_environment(self) -> None:
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("OPENAI_API_KEY=from-dotenv\nOPENAI_MODEL=dotenv-model\n")
            with patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "from-shell", "OPENAI_MODEL": "shell-model"},
                clear=True,
            ):
                _load_dotenv(env_path)
                llm = OptionalLLM()

        self.assertTrue(llm.enabled)
        self.assertEqual(llm.api_key, "from-shell")
        self.assertEqual(llm.model, "shell-model")


if __name__ == "__main__":
    unittest.main()
