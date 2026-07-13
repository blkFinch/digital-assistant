import importlib
import json
import os
import shutil
import unittest
import uuid


class TestLtmSelection(unittest.TestCase):
	def setUp(self) -> None:
		self._orig_ltm_name = os.environ.get("LTM_NAME")
		self._test_id = uuid.uuid4().hex
		self._ltm_a = f"test_ltm_{self._test_id}_a"
		self._ltm_b = f"test_ltm_{self._test_id}_b"
		self._session_path = None

	def tearDown(self) -> None:
		# Restore env first so importing config can't fail due to a bad LTM_NAME.
		if self._orig_ltm_name is None:
			os.environ.pop("LTM_NAME", None)
		else:
			os.environ["LTM_NAME"] = self._orig_ltm_name

		# Clean up any test-created LTM dirs.
		try:
			import core_agent.app.config as config
			ltm_root = config.LTM_ROOT_DIR
			for name in (self._ltm_a, self._ltm_b):
				candidate = (ltm_root / name).resolve()
				if candidate.exists() and candidate.is_dir() and name.startswith("test_ltm_"):
					shutil.rmtree(candidate, ignore_errors=True)
		except Exception:
			pass

		# Clean up any test-created session file.
		try:
			if self._session_path and self._session_path.exists():
				self._session_path.unlink(missing_ok=True)
		except Exception:
			pass

	def _reload_config_and_memory(self):
		import core_agent.app.config as config
		import core_agent.app.memory.memory_system as memory_system
		config = importlib.reload(config)
		memory_system = importlib.reload(memory_system)
		return config, memory_system

	def test_default_paths_used_when_ltm_name_unset(self):
		os.environ.pop("LTM_NAME", None)
		config, _ = self._reload_config_and_memory()
		self.assertEqual(config.LTM_PATH, config.DEFAULT_LTM_PATH)
		self.assertEqual(config.REVISION_LOG_PATH, config.DEFAULT_REVISION_LOG_PATH)

	def test_ltm_name_selects_paths_under_data_ltm(self):
		os.environ["LTM_NAME"] = self._ltm_a
		config, _ = self._reload_config_and_memory()

		norm_ltm_path = str(config.LTM_PATH).replace("\\", "/")
		norm_rev_path = str(config.REVISION_LOG_PATH).replace("\\", "/")
		self.assertTrue(norm_ltm_path.endswith(f"/data/ltm/{self._ltm_a}/ltm.json"))
		self.assertTrue(norm_rev_path.endswith(f"/data/ltm/{self._ltm_a}/revision_log.jsonl"))

	def test_ltm_path_traversal_is_rejected(self):
		os.environ["LTM_NAME"] = "../evil"
		import core_agent.app.config as config
		with self.assertRaises(RuntimeError):
			importlib.reload(config)

	def test_ltm_is_isolated_per_name(self):
		os.environ["LTM_NAME"] = self._ltm_a
		_, memory_system = self._reload_config_and_memory()
		memory_system.save_ltm([{"id": "mem_a"}])

		os.environ["LTM_NAME"] = self._ltm_b
		_, memory_system = self._reload_config_and_memory()
		self.assertEqual(memory_system.load_ltm(), [])

		os.environ["LTM_NAME"] = self._ltm_a
		_, memory_system = self._reload_config_and_memory()
		self.assertEqual(memory_system.load_ltm(), [{"id": "mem_a"}])

	def test_session_ltm_name_is_stamped_and_mismatch_fails_fast(self):
		os.environ["LTM_NAME"] = self._ltm_a
		import core_agent.app.config as config
		import core_agent.app.memory.session as session_module
		config = importlib.reload(config)
		session_module = importlib.reload(session_module)

		session = session_module.create_new_session()
		sid = f"test_session_{self._test_id}"
		session.session_id = sid
		session.file_path = config.SESSIONS_DIR / f"{sid}.json"
		self._session_path = session.file_path
		session_module.save_session(session)

		raw = json.loads(self._session_path.read_text())
		self.assertEqual(raw.get("ltm_name"), self._ltm_a)

		os.environ["LTM_NAME"] = self._ltm_b
		importlib.reload(config)
		with self.assertRaises(RuntimeError):
			session_module.load_session(self._session_path)


if __name__ == "__main__":
	unittest.main()
