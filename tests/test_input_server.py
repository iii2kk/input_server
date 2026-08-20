import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

import input_server


class DetectInputBackendTest(unittest.TestCase):
    def test_explicit_backend_is_used(self):
        self.assertEqual(
            input_server.detect_input_backend({"INPUT_BACKEND": "ydotool"}),
            "ydotool",
        )

    def test_wayland_uses_ydotool(self):
        self.assertEqual(
            input_server.detect_input_backend({"XDG_SESSION_TYPE": "wayland"}),
            "ydotool",
        )

    def test_x11_uses_xdotool(self):
        self.assertEqual(
            input_server.detect_input_backend({"XDG_SESSION_TYPE": "x11"}),
            "xdotool",
        )

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            input_server.detect_input_backend({"INPUT_BACKEND": "unknown"})


class DetectYdotoolKeyboardLayoutTest(unittest.TestCase):
    def test_explicit_layout_is_used(self):
        self.assertEqual(
            input_server.detect_ydotool_keyboard_layout(
                {"YDOTOOL_KEYBOARD_LAYOUT": "jp"}
            ),
            "jp",
        )

    def test_xkb_environment_is_used(self):
        self.assertEqual(
            input_server.detect_ydotool_keyboard_layout(
                {"XKB_DEFAULT_LAYOUT": "us,jp"}
            ),
            "jp",
        )

    def test_system_keyboard_config_is_used(self):
        with TemporaryDirectory() as temporary_directory:
            keyboard_config = Path(temporary_directory) / "keyboard"
            keyboard_config.write_text('XKBLAYOUT="jp"\n', encoding="utf-8")

            self.assertEqual(
                input_server.detect_ydotool_keyboard_layout(
                    {}, keyboard_config
                ),
                "jp",
            )


class SendInputTest(unittest.TestCase):
    @mock.patch.object(input_server.subprocess, "run")
    def test_xdotool_control_key_keeps_original_command(self, run):
        with mock.patch.object(input_server, "INPUT_BACKEND", "xdotool"):
            input_server.send_control_key("Return")

        run.assert_called_once_with(
            ["xdotool", "key", "--clearmodifiers", "Return"]
        )

    @mock.patch.object(input_server.subprocess, "run")
    def test_ydotool_control_key_uses_press_and_release(self, run):
        with mock.patch.object(input_server, "INPUT_BACKEND", "ydotool"):
            input_server.send_control_key("Left")

        run.assert_called_once_with(["ydotool", "key", "105:1", "105:0"])

    @mock.patch.object(input_server.subprocess, "run")
    def test_ydotool_character_is_passed_through_stdin(self, run):
        with (
            mock.patch.object(input_server, "INPUT_BACKEND", "ydotool"),
            mock.patch.object(input_server, "YDOTOOL_KEYBOARD_LAYOUT", "us"),
        ):
            input_server.send_character("a")

        run.assert_called_once_with(
            ["ydotool", "type", "--file=-"],
            input="a",
            text=True,
        )

    @mock.patch.object(input_server.subprocess, "run")
    def test_ydotool_jp_underscore_uses_ro_key(self, run):
        with (
            mock.patch.object(input_server, "INPUT_BACKEND", "ydotool"),
            mock.patch.object(input_server, "YDOTOOL_KEYBOARD_LAYOUT", "jp"),
        ):
            input_server.send_character("_")

        run.assert_called_once_with(
            ["ydotool", "key", "42:1", "89:1", "89:0", "42:0"]
        )

    @mock.patch.object(input_server.subprocess, "run")
    def test_ydotool_jp_double_quote_uses_shift_and_two(self, run):
        with (
            mock.patch.object(input_server, "INPUT_BACKEND", "ydotool"),
            mock.patch.object(input_server, "YDOTOOL_KEYBOARD_LAYOUT", "jp"),
        ):
            input_server.send_character('"')

        run.assert_called_once_with(
            ["ydotool", "key", "42:1", "3:1", "3:0", "42:0"]
        )

    @mock.patch.object(input_server.subprocess, "run")
    def test_ydotool_does_not_pass_unsupported_unicode(self, run):
        with (
            mock.patch.object(input_server, "INPUT_BACKEND", "ydotool"),
            mock.patch("builtins.print"),
        ):
            input_server.send_character("日")

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
