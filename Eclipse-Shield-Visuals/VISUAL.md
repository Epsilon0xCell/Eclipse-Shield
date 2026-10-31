# Eclipse Shield, drawn out

This repo is the biggest one I own, and the hardest to explain in a
paragraph: a browser extension, two Flask backends, a pile of
deployment shapes, and a vendored animation subtree that is not mine.
These five pictures are my attempt to make the shape of it visible in
one sitting.

## The visuals

- [architecture.svg](architecture.svg): three bands. The browser at
  the top, the backend on localhost:5000 in the middle, and the two
  outside parties at the bottom: the Gemini API and the web itself.
  The gold ring at the corner is the eclipse the product is named for.
- [components.svg](components.svg): the six parts that carry the
  product, as a grid, each with its one job written under it. If a
  reader only opens one picture, this is the one that tells them where
  a change belongs.
- [flowchart.svg](flowchart.svg): one navigation followed end to end,
  in two swimlanes. Browser lane on top, backend lane below, because
  the interesting moment in this product is the handoff between them.
- [product-map.svg](product-map.svg): a quadrant map. Who it serves,
  what it judges, the capability groups, and what it does not do.

- [statistics.svg](statistics.svg): the numbers from the table below, drawn as bars on paper: lines by language, with the test count stated honestly under them.

Each sheet also ships as a PNG beside its SVG (architecture.png, flowchart.png, and so on): the same drawing, finished as a photograph of the paper page.

Every sheet here is drawn to look like what it is: a page sketched by hand on paper, and each one is signed GK somewhere in the drawing, never twice in the same place, because that is what I do with a page I made.

## Written product map

What it is: a focus tool I built for myself. I start a session and
type the task I am supposed to be doing. While the session runs, the
extension watches where I navigate, and the backend judges each new
site against my own stated task. A site that fits loads. A site that
does not fit sends me to a block page that asks me a question about
what I was meant to be doing.

Who it serves: one person, me, at my desk. It is not built for a
workplace, a school, or a parent, and the map says so because that
boundary shaped the design.

Capabilities, grouped:

- Watching: extension/background.js (with Chrome and Opera variants)
  hooks navigation, normalizes URLs, keeps the per-session record of
  what was already analyzed, and holds the session state.
- Deciding: POST /analyze on the backend, with the URL and my task
  context. app.py carries get_confidence_score, the signal weighting.
  secure_app.py is the current backend, a Flask factory with the
  hardening from security.py; app.py is the older plain Flask app,
  kept working.
- Interrupting: the block page (extension/block.html and block.js) and
  questions served from /get_question and /contextualize.
- Serving itself: the backend also serves the extension files, the
  popup, the matrix animation pages, and, through update_server.py
  and update.xml, extension updates.
- Running shapes: install-local.sh and Dockerfile.local for the local
  way I run it, plus Docker, nginx, gunicorn, and supervisord files
  for a server deployment.

Inputs: a navigation, and the task text I type at session start.
Outputs: a page that loads, or a block page with a question. With a
Gemini key configured the judging uses the Gemini API; the health
endpoint says plainly when no key is configured.

Boundaries, what it does NOT do: it reports to nobody else. It is not
a monitor for an employer or a parent, it does not ship my history
anywhere, and when no API key is configured the AI judging stops
rather than guessing.

Upstream credit, plainly: the matrix-animation subtree under
extension/ is a vendored third-party animation project, included as
decoration for the block and new-tab pages. It is not my code, and the
line counts below include it because the files ship in this repo; the
components picture only maps my own parts.

## Statistics, with citations

Counted 2026-10-30, from the clone this folder ships in, at the commit
before this visuals commit. Line counts count a final line without a
trailing newline as a line; a wc -l cross-check of the Python files
read 4,304 against the table's 4,305 for exactly that reason.

| Number | Value | How it was counted, and from what |
|---|---|---|
| Files in the repo | 299 | git ls-files in the clone, counted 2026-10-30 |
| JavaScript lines | 26,108 | Line count over the 36 tracked .js files, same method as the Python count, 2026-10-30. Most of this is the vendored matrix-animation subtree |
| Markdown lines | 5,974 | Line count over the 22 tracked .md files, same method, 2026-10-30 |
| Python lines | 4,305 | Line count over the 12 tracked .py files, same method, 2026-10-30 |
| HTML lines | 3,922 | Line count over the 19 tracked .html files, same method, 2026-10-30 |
| Commits | 8 | git log in the clone, counted 2026-10-30. The migrated history is short; the work predates it |
| First commit | 2025-07-26 | git log, oldest entry, 2026-10-30 |
| Last commit before this one | 2026-10-30 | git log, newest entry, 2026-10-30 |
| Tests | 27 test functions in tests/test_app.py; run state: not run in this campaign | Counted by grep for test definitions in tests/test_app.py, 2026-10-30. I attempted the suite in the sandbox on 2026-10-30 and it could not start there: pytest and Flask are not installed in that environment and installing them was out of scope, so I claim no pass here |
| Languages (API) | JavaScript 763,404 bytes; Python 193,631; HTML 150,220; Shell 39,316; WGSL 29,382; GLSL 23,023; plus C, Lua, CMake, Dockerfile | GitHub API, GET /repos/Epsilon0xCell/Eclipse-Shield/languages, read 2026-10-30 |
| Repo size (API) | 12,229 KB | GitHub API, GET /repos/Epsilon0xCell/Eclipse-Shield, size field, read 2026-10-30 |
| Stars / forks (API) | 1 / 0 | Same API response, read 2026-10-30 |

External statistics: none. Nothing outside this repo measures this
repo honestly, so its own numbers are the whole table.

## Roadmap summary

Done: local mode runs, the extension and the current backend talk to
each other, and the test file exists with 27 end-to-end tests. Next:
get that suite running in one documented place and record the result,
because right now its pass state is a claim I cannot point at. The
full roadmap is in [ROADMAP.md](ROADMAP.md).
