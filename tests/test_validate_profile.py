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
        banner_copy = " | ".join(validate_profile.BANNER_REQUIRED_TEXT)
        (root / "assets" / "banner.svg").write_text(banner_copy, encoding="utf-8")
        (root / "README.md").write_text(readme, encoding="utf-8")
        return root

    @staticmethod
    def valid_readme(*, image: str = "./assets/banner.png") -> str:
        required_text = "\n".join(validate_profile.REQUIRED_TEXT)
        urls = "\n".join(sorted(validate_profile.REQUIRED_URLS))
        return (
            f'<img src="{image}" alt="Avery Quinn">\n'
            f"{validate_profile.HUMAN_NOTE}\n"
            f"{required_text}\n"
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

        self.assertEqual(counts, (5, 1))

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
            "https://etherscan.io/address/0xBDfFaEeD460B8297Aa8c832127F2556F32c1112C\n",
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

    def test_human_note_hash_is_historical_invariant(self) -> None:
        self.assertEqual(
            validate_profile.HUMAN_NOTE_SHA256,
            "54a2803a165c5a96217178e8bcba98788906209553c17d6192d329f3ef83cdc2",
        )

    def test_changed_human_note_fails(self) -> None:
        readme = self.valid_readme().replace(
            "I instructed it to be helpful",
            "I asked it to be helpful",
            1,
        )
        root = self.make_profile(readme)

        with self.assertRaisesRegex(AssertionError, "immutable HUMAN NOTE"):
            validate_profile.validate_profile(root=root)

    def test_duplicate_human_note_fails(self) -> None:
        readme = self.valid_readme() + validate_profile.HUMAN_NOTE
        root = self.make_profile(readme)

        with self.assertRaisesRegex(AssertionError, "immutable HUMAN NOTE"):
            validate_profile.validate_profile(root=root)

    def test_stale_identity_copy_fails(self) -> None:
        readme = self.valid_readme() + "AI-assisted open-source contributor\n"
        root = self.make_profile(readme)

        with self.assertRaisesRegex(AssertionError, "stale identity text"):
            validate_profile.validate_profile(root=root)

    def test_missing_optional_support_link_fails(self) -> None:
        readme = self.valid_readme().replace(
            "https://buymeacoffee.com/vivid0o0\n",
            "",
        )
        root = self.make_profile(readme)

        with self.assertRaisesRegex(AssertionError, "missing required public links"):
            validate_profile.validate_profile(root=root)

    def test_banner_identity_copy_is_validated(self) -> None:
        root = self.make_profile(self.valid_readme())
        (root / "assets" / "banner.svg").write_text(
            "AI-assisted | built with @vivid0o0 | open source, online",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(AssertionError, "banner source"):
            validate_profile.validate_profile(root=root)

    def test_check_links_flag_is_opt_in(self) -> None:
        self.assertFalse(validate_profile.parse_args([]).check_links)
        self.assertTrue(validate_profile.parse_args(["--check-links"]).check_links)


if __name__ == "__main__":
    unittest.main()
