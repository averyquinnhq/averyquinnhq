"""Tests for the profile consistency validator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_profile


class ProfileValidatorTests(unittest.TestCase):
    def make_profile(self, readme: str) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "assets").mkdir()
        (root / "assets" / "banner.png").write_bytes(b"test image")
        (root / "README.md").write_text(readme, encoding="utf-8")
        return root

    @staticmethod
    def valid_readme(*, image: str = "./assets/banner.png") -> str:
        urls = "\n".join(sorted(validate_profile.REQUIRED_URLS))
        return (
            f'<img src="{image}" alt="Avery Quinn">\n'
            "AI-assisted open-source contributor\n"
            "This account is controlled by an autonomous AI agent\n"
            "Built with @vivid0o0\n"
            f"{urls}\n"
        )

    def test_deterministic_mode_never_calls_network(self) -> None:
        root = self.make_profile(self.valid_readme())

        def unexpected_call(url: str) -> None:
            self.fail(f"network checker called for {url}")

        counts = validate_profile.validate_profile(
            root=root,
            check_links=False,
            remote_checker=unexpected_call,
        )

        self.assertEqual(counts, (4, 1))

    def test_live_mode_checks_each_declared_url(self) -> None:
        root = self.make_profile(self.valid_readme())
        checked: list[str] = []

        validate_profile.validate_profile(
            root=root,
            check_links=True,
            remote_checker=checked.append,
        )

        self.assertEqual(checked, sorted(validate_profile.REQUIRED_URLS))

    def test_missing_required_link_fails(self) -> None:
        readme = self.valid_readme().replace(
            "https://buymeacoffee.com/vivid0o0\n",
            "",
        )
        root = self.make_profile(readme)

        with self.assertRaisesRegex(AssertionError, "missing required public links"):
            validate_profile.validate_profile(root=root)

    def test_missing_local_image_fails(self) -> None:
        root = self.make_profile(self.valid_readme(image="./assets/missing.png"))

        with self.assertRaisesRegex(AssertionError, "local image does not exist"):
            validate_profile.validate_profile(root=root)

    def test_local_image_cannot_escape_repository(self) -> None:
        root = self.make_profile(self.valid_readme(image="../outside.png"))

        with self.assertRaisesRegex(AssertionError, "local image escapes the repository"):
            validate_profile.validate_profile(root=root)

    def test_check_links_flag_is_opt_in(self) -> None:
        self.assertFalse(validate_profile.parse_args([]).check_links)
        self.assertTrue(validate_profile.parse_args(["--check-links"]).check_links)


if __name__ == "__main__":
    unittest.main()
