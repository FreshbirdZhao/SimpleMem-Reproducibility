import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import nltk

from reproduction.run import memory_digest

with patch.object(nltk, "download", return_value=True):
    from test_locomo10 import LoCoMoTester


class PairedMemoryTests(unittest.TestCase):
    def test_category_five_calls_model_without_local_config_module(self):
        tester = LoCoMoTester.__new__(LoCoMoTester)
        tester.system = Mock()
        tester.system.llm_client.extract_json.return_value = {"answer": "model answer"}
        with patch.dict("sys.modules", {"config": None}):
            answer = tester.generate_category5_answer("question", [], "distractor")
        self.assertEqual(answer, "model answer")
        tester.system.llm_client.chat_completion.assert_called_once()

    def test_copy_preserves_digest_and_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "memory").write_bytes(b"original memory")
            target = Path(directory) / "copy"
            shutil.copytree(source, target)
            self.assertEqual(memory_digest(source), memory_digest(target))
            (target / "memory").write_bytes(b"changed memory")
            self.assertNotEqual(memory_digest(source), memory_digest(target))

    def test_reuse_skips_ingestion_and_keeps_question_evaluation(self):
        tester = LoCoMoTester.__new__(LoCoMoTester)
        tester.system = Mock()
        tester.convert_to_dialogues = Mock(return_value=["dialogue"])
        tester._test_questions_sequential = Mock(return_value=["result"])
        sample = Mock(qa=["question"])
        result = tester.test_sample(sample, 0, reuse_memory=True)
        self.assertEqual(result, ["result"])
        tester.system.add_dialogues.assert_not_called()
        tester.system.finalize.assert_not_called()
        tester._test_questions_sequential.assert_called_once_with(sample.qa)

    def test_default_still_builds_memory(self):
        tester = LoCoMoTester.__new__(LoCoMoTester)
        tester.system = Mock()
        tester.convert_to_dialogues = Mock(return_value=["dialogue"])
        tester._test_questions_sequential = Mock(return_value=[])
        tester.test_sample(Mock(qa=[]), 0)
        tester.system.add_dialogues.assert_called_once_with(["dialogue"])
        tester.system.finalize.assert_called_once_with()

    def test_reuse_rejects_multiple_conversations(self):
        tester = LoCoMoTester.__new__(LoCoMoTester)
        tester.load_dataset = Mock(return_value=[Mock(), Mock()])
        with self.assertRaisesRegex(ValueError, "exactly one"):
            tester.run_test(reuse_memory=True)

    def test_reuse_rejects_empty_memory(self):
        tester = LoCoMoTester.__new__(LoCoMoTester)
        tester.load_dataset = Mock(return_value=[Mock()])
        tester.system = Mock()
        tester.system.vector_store.backend.count.return_value = 0
        with self.assertRaisesRegex(ValueError, "empty"):
            tester.run_test(reuse_memory=True)


if __name__ == "__main__":
    unittest.main()
