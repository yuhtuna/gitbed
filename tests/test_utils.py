import unittest
from unittest.mock import MagicMock, patch

from gitbed.utils import clean_code_block, fetch_github_file, verify_cpp_compilation


class TestUtils(unittest.TestCase):

    def test_clean_code_block_with_markdown_fences(self):
        raw_llm_output = "```cpp\n#define STATUS_LED_PIN PB7\nvoid init();\n```"
        expected = "#define STATUS_LED_PIN PB7\nvoid init();"
        self.assertEqual(clean_code_block(raw_llm_output), expected)

    def test_clean_code_block_without_fences(self):
        raw_text = "#define STATUS_LED_PIN PB7"
        self.assertEqual(clean_code_block(raw_text), raw_text)

    def test_verify_cpp_compilation_valid_code(self):
        valid_cpp = (
            "#ifndef PIN_CONFIG_H\n"
            "#define PIN_CONFIG_H\n"
            "#define STATUS_LED_PIN PB7\n"
            "void init_pins();\n"
            "#endif\n"
        )
        valid, err = verify_cpp_compilation(valid_cpp)
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_verify_cpp_compilation_invalid_code(self):
        invalid_cpp = "int main( {"
        valid, err = verify_cpp_compilation(invalid_cpp)
        self.assertFalse(valid)
        self.assertIn("error", err.lower())

    @patch("gitbed.utils.Github")
    def test_fetch_github_file(self, mock_github):
        mock_repo = MagicMock()
        mock_content = MagicMock()
        mock_content.decoded_content = b"#define STATUS_LED_PIN PB6"
        mock_repo.get_contents.return_value = mock_content
        mock_repo.default_branch = "main"

        mock_instance = MagicMock()
        mock_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_instance

        content = fetch_github_file("user/repo", "fake_token", "pin_config.h")
        self.assertEqual(content, "#define STATUS_LED_PIN PB6")
        mock_github.assert_called_once_with("fake_token")
        mock_instance.get_repo.assert_called_once_with("user/repo")


if __name__ == "__main__":
    unittest.main()
