import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, title):
        self.title = title
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        return Response(f"<title>{self.title}</title>" if "/watch/" in url else "encrypted")


class DownloadPageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name)
        self.session = Session("Reply 1994 - Loi Hoi Dap 1994 - S01E02")

    def download(self, tracks, **options):
        with patch.object(main, "get_subtitles", return_value=tracks), patch.object(main, "decrypt_subtitle", return_value=b"subtitle"):
            main.download_page(self.session, "https://phimfly.com/watch/abc", self.output, set(), **options)

    def track(self, language, number):
        return {"language": language, "fileName": f"original{number}.srt", "subsceneId": number, "id": number}

    def test_single_language_and_repeat_download(self):
        tracks = [self.track("vi", 1)]
        self.download(tracks)
        self.download(tracks)
        target = self.output / "Reply.1994" / "Reply.1994.S01E02.1080p.vi.srt"
        self.assertEqual(target.read_bytes(), b"subtitle")
        self.assertEqual(len(self.session.calls), 3)

    def test_multiple_languages_and_overrides(self):
        self.download([self.track("vi", 1), self.track("en", 2)], show="Custom Show", season=3, resolution="720p")
        for language in ("vi", "en"):
            target = self.output / "Custom.Show" / language / f"Custom.Show.S03E02.720p.{language}.srt"
            self.assertEqual(target.read_bytes(), b"subtitle")

    def test_different_language_selection_skips_existing_target(self):
        self.download([self.track("vi", 1)])
        self.download([self.track("vi", 1), self.track("en", 2)])
        self.assertEqual(len(self.session.calls), 4)
        self.assertFalse((self.output / "Reply.1994" / "vi").exists())

    def test_duplicate_language_tracks_are_preserved(self):
        self.download([self.track("vi", 1), self.track("vi", 2)])
        episode = self.output / self.session.title
        self.assertEqual((episode / "vi.1.original1.srt").read_bytes(), b"subtitle")
        self.assertEqual((episode / "vi.2.original2.srt").read_bytes(), b"subtitle")

    def test_unrecognized_episode_title_preserves_original_filename(self):
        self.session.title = "A Movie (2019)"
        self.download([self.track("vi", 1)])
        self.assertEqual((self.output / self.session.title / "vi.1.original1.srt").read_bytes(), b"subtitle")


if __name__ == "__main__":
    unittest.main()