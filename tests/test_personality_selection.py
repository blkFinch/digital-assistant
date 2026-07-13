import importlib
import os
import unittest


class TestPersonalitySelection(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_personality_name = os.environ.get("PERSONALITY_NAME")

    def tearDown(self) -> None:
        if self._orig_personality_name is None:
            os.environ.pop("PERSONALITY_NAME", None)
        else:
            os.environ["PERSONALITY_NAME"] = self._orig_personality_name

    def _reload_modules(self):
        import core_agent.app.config as config
        import core_agent.app.llm.prompts as prompts

        config = importlib.reload(config)
        prompts = importlib.reload(prompts)
        return config, prompts

    def test_default_personality_path_is_used_when_env_unset(self):
        os.environ.pop("PERSONALITY_NAME", None)

        config, _ = self._reload_modules()
        self.assertEqual(config.PERSONALITY_PATH, config.DEFAULT_PERSONALITY_PATH)

    def test_personality_name_selects_prompt_under_personalities_dir(self):
        os.environ["PERSONALITY_NAME"] = "yuki"

        config, prompts = self._reload_modules()
        self.assertTrue(str(config.PERSONALITY_PATH).replace("\\", "/").endswith("/prompts/personalities/yuki.md"))

        text = prompts.get_personality()
        self.assertIn("# Yuki", text)

    def test_missing_personality_name_fails_fast(self):
        os.environ["PERSONALITY_NAME"] = "does_not_exist"

        import core_agent.app.config as config
        with self.assertRaises(RuntimeError) as ctx:
            importlib.reload(config)
        self.assertIn("PERSONALITY_NAME", str(ctx.exception))

        # Restore a valid config module for any subsequent tests.
        os.environ.pop("PERSONALITY_NAME", None)
        importlib.reload(config)

    def test_path_traversal_is_rejected(self):
        os.environ["PERSONALITY_NAME"] = "../personality"

        import core_agent.app.config as config
        with self.assertRaises(RuntimeError):
            importlib.reload(config)

        os.environ.pop("PERSONALITY_NAME", None)
        importlib.reload(config)


if __name__ == "__main__":
    unittest.main()

