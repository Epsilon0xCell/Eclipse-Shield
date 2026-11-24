# Eclipse Shield demo: production script and capture notes

Demo video for Eclipse-Shield (Flask backend plus MV3 Chrome extension),
produced 2026-11-24. Every shot is a real run of the fixed code in `../repo`.
No fake UI, no staged verdicts, no mock data. Where a capture method needs
explaining, it is explained below, in the open.

## Deliverables

- `eclipse-shield-demo.mp4`: 1920x1080, H.264 (CRF 20) plus AAC 192k,
  112.0 s, 6,073,941 bytes, audio measured at -14.5 LUFS integrated,
  true peak -1.5 dB.
- `eclipse-shield-demo.gif`: hero loop only, 800x450, 15 fps, 12.0 s,
  1,066,654 bytes (under the 5 MB target), silent, loops forever.
- Raw captures: `raw/` (API transcripts, pytest output, server logs,
  screenshots). Capture and build scripts: `work/` (`cdp.js`,
  `phase_*.js`, `build_frames.py`, `make_music.py`). The `raw/` and
  `work/` production folders are kept with the local production copy
  of this demo and are not committed to this repository; the MP4, the
  GIF, and this script are the committed deliverables.

## Environment

- Backend: the real Flask app from `../repo`, run keyless (no
  `GEMINI_API_KEY` in the environment) on 127.0.0.1:5000.
- Browser: Chromium (Hatch build v157) on Xvfb :99 at 1920x1080, with the
  real extension loaded unpacked from `../repo/extension`
  (`--load-extension`). Extension ID in this profile:
  `hbemdlmneaphhjbencjkafhiojgfcdkn`.
- Driving: Chrome DevTools Protocol from Node scripts in `work/`
  (real DOM clicks and real navigations; screenshots via
  `Page.captureScreenshot`).

## Exact commands

Backend (run from `../repo`):

```
~/workspace/.venvs/eclipse/bin/python app.py
# log line on a keyless start:
# WARNING - script - No Gemini API key configured; running in local rules-only mode
#  * Running on http://127.0.0.1:5000
```

API beats (full transcript in `raw/api-calls.txt`):

```
curl -s http://127.0.0.1:5000/health
curl -s -X POST http://127.0.0.1:5000/api/check -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com","profile":"work"}'
curl -s -X POST http://127.0.0.1:5000/api/check -H 'Content-Type: application/json' \
  -d '{"url":"https://www.google.com/search?q=best+board+games+for+family+night","profile":"work"}'
curl -s -X POST http://127.0.0.1:5000/api/check -H 'Content-Type: application/json' \
  -d '{"url":"https://www.google.com/search?q=best+board+games+for+family+night","profile":"personal"}'
```

Tests (output in `raw/pytest.txt`):

```
python -m pytest -q
# 59 passed in 8.20s
```

Video assembly (per-frame stills from `work/build_frames.py`, then):

```
ffmpeg -loop 1 -t <dur> -i frame.png \
  -vf "fade=t=in:st=0:d=0.4,fade=t=out:st=<dur-0.4>:d=0.4,format=yuv420p" \
  -r 30 -c:v libx264 -preset veryfast -crf 20 clip.mp4   # x14 clips
ffmpeg -f concat -safe 0 -i concat.txt -i music.wav -map 0:v -map 1:a \
  -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k \
  -movflags +faststart -shortest eclipse-shield-demo.mp4
```

GIF (two-pass palette, from the hero segment of the finished MP4, 75s to 87s):

```
ffmpeg -ss 75 -t 12 -i eclipse-shield-demo.mp4 \
  -vf "fps=15,scale=800:-1:flags=lanczos,palettegen=stats_mode=diff" palette.png
ffmpeg -ss 75 -t 12 -i eclipse-shield-demo.mp4 -i palette.png \
  -lavfi "fps=15,scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -loop 0 eclipse-shield-demo.gif
```

## Shot list (final video, 112 s)

| Time | Shot | How it was captured |
| --- | --- | --- |
| 0:00-0:08 | Title over the repo banner art | `assets/banner.png` from the repo, captioned |
| 0:08-0:18 | Terminal: server start, /health, one /api/check | Rendered from the real captured lines in `raw/api-calls.txt` and the real keyless start log; the two JSON lines are copied from the capture file by the build script, never retyped |
| 0:18-0:27 | No session: a real tab asks for youtube.com | Real tab navigation in the loaded extension; the background worker redirected it to `block.html?reason=no-session`. Screenshot: `raw/shots/site-nosession-youtube.png` |
| 0:27-0:41 | Popup flow: set 30 minutes, pick Work, answer two context questions, session active | The extension's real popup composition: `redirect.html` (extension page) hosting the backend-served `http://localhost:5000/ext-popup` iframe, driven with real clicks and typed answers ("Preparing the quarterly status report for my team" / "Finish the report and share it with my team for review"). Keyless mode served the two deterministic local questions. Session verified in `chrome.storage.local`: `sessionData` state active, domain work |
| 0:41-0:50 | Work profile: notion.so Allowed | Side panel verdict (see panel method note). Verdict: Allowed, source list |
| 0:50-1:01 | Work profile: youtube.com blocked in a real tab, with the panel verdict beside it | Real tab navigation during the active Work session; the extension served its ACCESS BLOCKED page with the reason and the live countdown (`raw/shots/site-youtube-blocked.png`). Panel inset: Blocked, source list |
| 1:01-1:12 | School profile: Canvas Allowed, Reddit Blocked | Two side panel verdicts, profile switched with the panel's real School button |
| 1:12-1:27 | HERO: the same Google search under Work, then Personal | One URL in the side panel: `https://www.google.com/search?q=best+board+games+for+family+night`. Work (clicked for real): Blocked, "Blocked keyword found: 'games'.", source list. Personal (clicked for real, panel auto-rechecks): Allowed, "Allowed by local rules (AI unavailable): search with an explicit query.", source keyless-default |
| 1:27-1:37 | Unlisted sites, no key: github.com Allowed (development), example.com Blocked (no local rule matched) | Two side panel verdicts under Personal, both source keyless-default |
| 1:37-1:45 | Terminal: pytest | Real run captured in this session, `raw/pytest.txt`: 59 passed. The security suite line is labelled in the frame itself as the audit-pass result (30 passed, 0 failed on a fresh server) |
| 1:45-1:52 | End card | Repo `logo.png`, project URL |

## Side panel capture method (read this before judging the panel shots)

CDP cannot screenshot a docked side panel in this VM, so the panel shots
were captured with the side panel's own page (`sidepanel.html`, the exact
page Chrome docks) opened as an extension page tab at panel size
(430x920 CSS px at 2x). The page's own scripts ran unmodified: health
check, profile buttons, and `checkCurrentTab()` are the panel's real code
paths, and every verdict on screen is the panel's own live `/api/check`
response from the local backend. One assistance was given: the page reads
the current tab's URL through `chrome.tabs.query`, which returns the
panel tab itself when the page is not docked, so the capture script set
the page's current-tab field to the demo URL before invoking its real
check function. Profile switches were done by clicking the panel's real
profile buttons (which also trigger its real auto-recheck). The popup
shots needed no such help: the popup composition works as a page, and it
was driven exactly as a user drives it.

## Music provenance

Original track, generated programmatically for this demo. No samples, no
third-party audio, no library music, nothing to license.
`work/make_music.py` synthesizes a 112 s dark ambient loop with numpy:
sine partials with slow tremolo for the Am(add9), Fmaj7, Cmaj7, G6 pad
progression, a soft A1 sub pulse, and a sparse A minor pentatonic
arpeggio with exponential decay, master fade 2 s in and 5 s out, peak
-3 dBFS. Mixed into the video with ffmpeg loudnorm to I=-14, TP=-1.5,
LRA=11 (final file measured -14.5 LUFS integrated).

## Deviations and production incidents, disclosed

1. **No Gemini beat.** The demo was specified with a Gemini AI verdict
   shot, and a Gemini API key was created for this project in Google AI
   Studio on 2026-11-24, but the key value was not available to the
   capture environment at run time, so the backend ran keyless for the
   whole shoot. The AI beat is replaced by the keyless-resilience beat
   (unlisted sites decided by local rules, `source: keyless-default`),
   which is real shipped behavior. Nothing in the video claims an AI
   verdict was shown. To add the Gemini beat later: export
   `GEMINI_API_KEY`, restart `app.py`, and re-run the panel capture for
   one unlisted site; its verdict will carry `source: gemini`.
2. **Hero site changed.** The script's original hero was youtube.com
   flipping on the Work to Personal switch. Verified live, keyless
   YouTube stays Blocked under Personal (local category rule:
   streaming), so that flip does not exist without a key. The hero uses
   the Google search URL above instead, whose flip was verified live
   before capture: Work Blocked by keyword, Personal Allowed by local
   rules. Same mechanic, honest example.
3. **External site content does not load in this VM's browser.** Tabs
   for notion.so and github.com render Chrome's
   ERR_TUNNEL_CONNECTION_FAILED error page here (the egress proxy needs
   authentication Chromium cannot be given from the command line).
   Those error-page screenshots were discarded and are not in the
   video. Allowed-site beats are therefore panel-verdict-led, and the
   two real tab shots that are used (no-session block, YouTube block)
   show the extension's own block pages, which are local and real.
4. **Backend restarts between capture groups.** `/api/check` is rate
   limited to 10 requests per minute per IP by design. The backend was
   restarted between capture groups to reset its in-memory limiter
   (logs: `raw/server-terminal-*.log`). No limiter was disabled or
   patched for the demo.
5. **A service restart wiped /tmp mid-capture** and killed the first
   browser and server. The browser profile and all work files were
   moved into this workspace directory and the popup flow was re-run
   from scratch; no shot from the lost session is used.
6. **Disk quota incidents.** The VM's per-user disk quota filled during
   production (the same wall the repo audit hit). Chromium crashed once
   when its crash-dump write hit the quota; it was relaunched and the
   affected shot (Canvas under School) was re-captured at the correct
   size and profile. Video assembly was done in /tmp and the finished
   files were copied here and checksum-verified. The derived
   `work/frames/` stills were deleted after assembly to fit the quota;
   regenerate them any time with `python3 work/build_frames.py`.

## Verification performed

- ffprobe: MP4 1920x1080, 112.0 s, 6,073,941 bytes; GIF 800x450,
  12.0 s, 1,066,654 bytes.
- Every composed frame was viewed before assembly, and frames were
  extracted from the finished MP4 and GIF at shot boundaries (including
  both hero states) and viewed again.
- No terminal frame contains a traceback; server logs show clean starts.
- Captions and this file were scanned for em dashes and for leaked home
  paths or usernames: none. Terminal frames use the neutral prompt
  `demo $`.
