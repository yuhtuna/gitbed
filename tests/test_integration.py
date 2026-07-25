import unittest
from unittest.mock import MagicMock, patch

from gitbed.graph import build_graph
from gitbed.state import AgentState


class TestIntegration(unittest.TestCase):

    @patch.dict("os.environ", {"GITHUB_TOKEN": "fake_token", "GITHUB_REPO": "user/repo"})
    @patch("gitbed.nodes.Github")
    @patch("gitbed.nodes.ChatOpenAI")
    def test_full_graph_execution_success(self, mock_chat_openai, mock_github):
        # 1. Mock LLM response
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "```cpp\n#define STATUS_LED_PIN PB7\nvoid init();\n```"
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance

        # 2. Mock PyGithub API response
        mock_branch = MagicMock()
        mock_branch.commit.sha = "abcdef1234567890"

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/user/repo/pull/42"

        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_repo.get_branch.return_value = mock_branch
        mock_repo.get_contents.side_effect = Exception("File not found")
        mock_repo.create_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance

        # 3. Build & Invoke Graph
        app = build_graph()

        initial_state: AgentState = {
            "diff_data": {
                "netlist_version": "v2.1.0",
                "signal_name": "STATUS_LED",
                "old_pin": "PB6",
                "new_pin": "PB7",
            },
            "original_code": "#define STATUS_LED_PIN PB6\nvoid init();\n",
            "updated_code": "",
            "error_log": "",
            "attempts": 0,
            "pr_url": "",
        }

        final_state = app.invoke(initial_state)

        self.assertEqual(final_state["pr_url"], "https://github.com/user/repo/pull/42")
        self.assertEqual(final_state["attempts"], 1)
        self.assertEqual(final_state["error_log"], "")


if __name__ == "__main__":
    unittest.main()
