import unittest
from unittest.mock import MagicMock, patch

from gitbed.nodes import generate_patch, open_pr, verify_patch
from gitbed.state import AgentState


class TestNodes(unittest.TestCase):

    @patch("gitbed.nodes.ChatOpenAI")
    def test_generate_patch(self, mock_chat_openai):
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "```cpp\n#define STATUS_LED_PIN PB7\n```"
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance

        state: AgentState = {
            "diff_data": {"new_pin": "PB7", "signal_name": "STATUS_LED"},
            "original_code": "#define STATUS_LED_PIN PB6",
            "updated_code": "",
            "error_log": "",
            "attempts": 0,
            "pr_url": "",
        }

        result = generate_patch(state)
        self.assertEqual(result["updated_code"], "#define STATUS_LED_PIN PB7")
        self.assertEqual(result["attempts"], 1)

    def test_verify_patch_success(self):
        state: AgentState = {
            "diff_data": {"new_pin": "PB7"},
            "original_code": "",
            "updated_code": "#define STATUS_LED_PIN PB7\nvoid init();",
            "error_log": "",
            "attempts": 1,
            "pr_url": "",
        }

        result = verify_patch(state)
        self.assertEqual(result["error_log"], "")

    def test_verify_patch_missing_pin(self):
        state: AgentState = {
            "diff_data": {"new_pin": "PB7"},
            "original_code": "",
            "updated_code": "#define STATUS_LED_PIN PB6\nvoid init();",
            "error_log": "",
            "attempts": 1,
            "pr_url": "",
        }

        result = verify_patch(state)
        self.assertIn("missing in code", result["error_log"])

    def test_verify_patch_syntax_error(self):
        state: AgentState = {
            "diff_data": {"new_pin": "PB7"},
            "original_code": "",
            "updated_code": "int invalid_cpp ( {",
            "error_log": "",
            "attempts": 1,
            "pr_url": "",
        }

        result = verify_patch(state)
        self.assertIn("Compiler error:", result["error_log"])

    @patch.dict("os.environ", {"GITHUB_TOKEN": "fake_token", "GITHUB_REPO": "user/repo"})
    @patch("gitbed.nodes.Github")
    def test_open_pr(self, mock_github):
        mock_branch = MagicMock()
        mock_branch.commit.sha = "1234567890abcdef"

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/user/repo/pull/1"

        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_repo.get_branch.return_value = mock_branch
        mock_repo.get_contents.side_effect = Exception("File not found")
        mock_repo.create_pull.return_value = mock_pr

        mock_instance = MagicMock()
        mock_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_instance

        state: AgentState = {
            "diff_data": {"new_pin": "PB7", "signal_name": "STATUS_LED"},
            "original_code": "",
            "updated_code": "#define STATUS_LED_PIN PB7",
            "error_log": "",
            "attempts": 1,
            "pr_url": "",
        }

        result = open_pr(state)
        self.assertEqual(result["pr_url"], "https://github.com/user/repo/pull/1")
        self.assertEqual(mock_repo.create_file.call_count, 3)
        mock_repo.create_pull.assert_called_once()


if __name__ == "__main__":
    unittest.main()
