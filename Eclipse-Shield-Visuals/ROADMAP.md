# Eclipse Shield roadmap

Written 2026-10-30 from the repo as it stands: its files, its docs
folder, and what the 2026-10-30 repair and comment campaigns recorded
about it. No invented dates on future items.

## Done

- The local way to run it: install-local.sh, Dockerfile.local, and a
  launchd plist, so the backend runs on my Mac without the full server
  stack (repair commit 2ba6f14).
- secure_app.py as the current backend: a Flask factory with the
  security hardening, /analyze, /get_question, /health, and
  /test-connection, serving the extension files itself.
- The extension in three browser flavors: background.js plus the
  Chrome and Opera variants, popup, block page, and new-tab override.
- app.py kept working as the older plain Flask app, with
  get_confidence_score doing the signal weighting in /analyze.
- An end-to-end test file, tests/test_app.py, with 27 tests, and a
  tests/conftest.py beside it.
- A docs folder with architecture, API, configuration, deployment,
  and monitoring notes, and these visuals.

## Working now

- Nothing in flight as of 2026-10-30. The campaigns that touched this
  repo (repair, comments, website) are finished; this roadmap is
  written from their end state.

## Next

- Run tests/test_app.py in one documented environment and record the
  result in the repo. The suite could not start in the campaign
  sandbox (pytest and Flask were not installed there), so its current
  pass state is unverified, and I would rather fix that fact than
  leave a claim standing on nothing.
- Decide the fate of the two backends. app.py and secure_app.py both
  serve /analyze today. Keeping both was right while the secure one
  proved itself; at some point one of them should become the only one,
  and the other should be marked as the historical version in the
  README instead of a second live option.

## Later

- Trim or fence the vendored matrix-animation subtree so a reader can
  tell at a glance which files are mine. The credit is written down in
  VISUAL.md; the tree itself does not show it yet.

## Not planned

- Accounts, sync, or any reporting to a second person. The tool judges
  my browsing against my own stated task and tells nobody. A version
  that reported upward would be a different product, and it is not
  this one.
- A store release. The extension is loaded by hand on my own browsers.
