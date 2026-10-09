# Profile maintenance

`README.md` is the default English profile. `README.zh-CN.md` provides the Chinese version, with links at the top of both pages. The English page links to the English version of the existing personal website.

## Activity updates

`.github/workflows/profile-activity.yml` checks activity every six hours, on profile content changes, and on manual dispatch. The workflow uses the built-in, repository-scoped GitHub token. No personal access token or additional secret is required.

`scripts/update_activity.py` updates the activity block in both languages from one shared `activity-data.json` snapshot. It displays up to five public pushes and five recent authored commits from the ten most recently active candidate public repositories. Imported upstream commits and bot-authored refresh commits are excluded. This is a recent activity summary, not a full contribution count.

The events API includes a limited recent window and can take time to expose pushes. Commit timestamps are never presented as push timestamps. Event-based push links point to the before/after comparison when available, otherwise the push head or branch history.

The updater preserves the previous records if fetching fails, checks both language markers before writing, and makes no commit when the records are unchanged. Normal Git pushes protect concurrent manual edits; refreshes never force-push.

Run the checks with:

```bash
python3 -m py_compile scripts/update_activity.py
python3 -m unittest discover -s tests -v
python3 scripts/update_activity.py
```

The last command fetches public GitHub activity. Original commit subjects are retained as historical data in both languages.

## Visual assets

The banners are stored in `assets/`; `tools/build_assets.py` regenerates them with Pillow. Separate mobile and static images support narrow screens and reduced-motion preferences. The overall GitHub page theme remains the visitor's setting.

## Sources

- [GitHub public events API](https://docs.github.com/en/rest/activity/events#list-public-events-for-a-user)
- [GitHub commit API](https://docs.github.com/en/rest/commits/commits#list-commits)
- [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
