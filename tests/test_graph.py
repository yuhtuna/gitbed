import unittest
from langgraph.graph import END

from gitbed.graph import route_verification
from gitbed.state import AgentState


class TestGraphRouting(unittest.TestCase):

    def test_route_verification_retry(self):
        state: AgentState = {
            "diff_data": {},
            "original_code": "",
            "updated_code": "",
            "error_log": "Compiler error",
            "attempts": 1,
            "pr_url": "",
        }
        self.assertEqual(route_verification(state), "generate_patch")

    def test_route_verification_max_attempts_exceeded(self):
        state: AgentState = {
            "diff_data": {},
            "original_code": "",
            "updated_code": "",
            "error_log": "Compiler error",
            "attempts": 3,
            "pr_url": "",
        }
        self.assertEqual(route_verification(state), END)

    def test_route_verification_success(self):
        state: AgentState = {
            "diff_data": {},
            "original_code": "",
            "updated_code": "",
            "error_log": "",
            "attempts": 1,
            "pr_url": "",
        }
        self.assertEqual(route_verification(state), "open_pr")


if __name__ == "__main__":
    unittest.main()
