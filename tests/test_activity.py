from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "update_activity.py"
spec = importlib.util.spec_from_file_location("activity", path)
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)


class ActivityTests(unittest.TestCase):
    def event(self, **extra):
        return {"id": "1", "type": "PushEvent", "public": True,
                "actor": {"login": activity.USER}, "repo": {"name": activity.USER + "/Simulation"},
                "created_at": "2026-10-09T11:00:00Z",
                "payload": {"ref": "refs/heads/main", "head": "a" * 40, "before": "b" * 40}, **extra}

    def test_current_push_schema_and_private_event_filter(self):
        public = self.event()
        private = self.event(id="2", public=False)
        bot = self.event(id="3", actor={"login": "github-actions[bot]"})
        rows = activity.public_pushes([public, private, bot, public])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["branch"], "main")
        self.assertTrue(rows[0]["url"].endswith("/compare/" + "b" * 40 + "..." + "a" * 40))

    def test_commit_author_filter(self):
        commit = {"sha": "a" * 40, "author": {"login": "upstream-author"},
                  "commit": {"message": "Imported work", "committer": {"date": "2026-10-09T11:00:00Z"}}}
        self.assertIsNone(activity.normalize_commit(commit, activity.USER + "/Simulation"))
        commit["author"]["login"] = activity.USER
        self.assertIsNotNone(activity.normalize_commit(commit, activity.USER + "/Simulation"))

    def test_selected_projects_are_included_when_many_forks_are_active(self):
        recent = [{"full_name": f"{activity.USER}/fork-{i}"} for i in range(12)]
        selected = {"full_name": activity.USER + "/IsaacLab_Walker_S2"}
        names = activity.candidate_repos(recent + [selected], [])
        self.assertIn(selected["full_name"], names)
        self.assertEqual(len(names), 10)

    def test_markdown_and_html_from_public_events_are_escaped(self):
        row = activity.public_pushes([self.event(payload={"ref": "refs/heads/[bad](evil)<script>", "head": "a" * 40})])[0]
        data = {"updated_at": "2026-10-09T11:00:00Z", "pushes_available": True, "pushes": [row], "commits": []}
        text = activity.render(data, "en")
        self.assertNotIn("<script>", text)
        self.assertIn("\\[bad\\]", text)
        self.assertIn("2026-10-09 19:00", text)

    def test_bilingual_update_is_idempotent_and_preserves_surrounding_content(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            template = "before\n" + activity.START + "\nold\n" + activity.END + "\nafter"
            for name in ["README.md", "README.zh-CN.md"]:
                (root / name).write_text(template)
            data = {"pushes_available": True, "pushes": [], "commits": []}
            self.assertTrue(activity.update_files(root, data, "2026-10-09T11:00:00Z"))
            self.assertFalse(activity.update_files(root, data, "2026-10-10T11:00:00Z"))
            for name in ["README.md", "README.zh-CN.md"]:
                text = (root / name).read_text()
                self.assertTrue(text.startswith("before\n"))
                self.assertTrue(text.endswith("\nafter"))
            self.assertIn("Recent Pushes", (root / "README.md").read_text())
            self.assertIn("最近推送", (root / "README.zh-CN.md").read_text())

    def test_invalid_second_language_does_not_partially_write(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            original = activity.START + "\nold\n" + activity.END
            (root / "README.md").write_text(original)
            (root / "README.zh-CN.md").write_text("missing markers")
            with self.assertRaises(ValueError):
                activity.update_files(root, {"pushes_available": True, "pushes": [], "commits": []}, "2026-10-09T11:00:00Z")
            self.assertEqual((root / "README.md").read_text(), original)


if __name__ == "__main__":
    unittest.main()
