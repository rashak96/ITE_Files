"""
Create HTML presentations with embedded interactive polls.
Works with local WebSocket poll server (poll_server.py).
"""

import json
import re
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "ite_data.json"
OUTPUT_DIR = SCRIPT_DIR / "ITE_HTML"

REVEAL_CSS = "https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css"
REVEAL_THEME = "https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/simple.css"
REVEAL_JS = "https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"
MONTSERRAT = "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Segoe+UI:wght@400;600&display=swap"


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _truncate(s: str, max_len: int = 400) -> str:
    return s[:max_len] + "..." if len(s) > max_len else s


def build_poll_slide(q: dict, topic: str, subtopic: str, year: int, idx: int) -> str:
    poll_id = f"q_{q['number']}_{year}_{idx}"
    stem = _escape(_truncate(q["stem"], 600))
    options = q.get("options", {})
    opts_html = "".join(
        f'<button class="poll-opt" data-poll="{poll_id}" data-choice="{letter}">{letter}) {_escape(_truncate(txt, 120))}</button>'
        for letter, txt in options.items()
    )
    return f'''
    <section class="poll-slide" data-poll-id="{poll_id}">
        <p class="grey-label">{_escape(topic)} | {_escape(subtopic)}</p>
        <p class="q-meta">Question {q["number"]} ({year})</p>
        <div class="poll-stem">{stem}</div>
        <div class="poll-options">{opts_html}</div>
        <button class="poll-reset" data-poll="{poll_id}" style="display:none;">Reset</button>
    </section>'''


def build_results_placeholder_slide(q: dict, topic: str, subtopic: str, idx: int) -> str:
    poll_id = f"q_{q['number']}_{q['year']}_{idx}"
    return f'''
    <section class="results-slide">
        <p class="grey-label">{_escape(topic)} | {_escape(subtopic)}</p>
        <h3>Results — Question {q["number"]} ({q["year"]})</h3>
        <div class="poll-results" id="results-{poll_id}">Votes appear here in real-time.</div>
    </section>'''


def build_critique_slide(q: dict, topic: str, subtopic: str, year: int) -> str:
    ans = q.get("answer", "?")
    critique = _escape(_truncate(q.get("critique", "No critique."), 1500))
    return f'''
    <section>
        <p class="grey-label">{_escape(topic)} | {_escape(subtopic)}</p>
        <h3>Answer: {ans} — Question {q["number"]} ({year})</h3>
        <div class="critique-body">{critique}</div>
    </section>'''


def build_html(topic: str, questions: list[dict]) -> str:
    by_subtopic = defaultdict(list)
    for q in questions:
        by_subtopic[q.get("subtopic") or "Other"].append(q)
    subtopic_order = sorted(by_subtopic.keys(), key=lambda s: min(q["number"] for q in by_subtopic[s]))

    slides = []
    slides.append(f'''
    <section>
        <h1 style="font-family:Montserrat,sans-serif;">{_escape(topic)}</h1>
        <p style="color:#767676;font-size:1.2rem;">ITE Questions — Interactive Polls</p>
    </section>''')

    slides.append('''
    <section>
        <h2>Join the Poll</h2>
        <p>Open this page on your phone:</p>
        <p><strong id="join-url">Loading...</strong></p>
        <p style="font-size:0.9rem;color:#767676;">Use ?audience to vote.</p>
    </section>''')

    for subtopic in subtopic_order:
        for i, q in enumerate(sorted(by_subtopic[subtopic], key=lambda x: (x["year"], x["number"]))):
            slides.append(build_poll_slide(q, topic, subtopic, q["year"], i))
            slides.append(build_results_placeholder_slide(q, topic, subtopic, i))
            slides.append(build_critique_slide(q, topic, subtopic, q["year"]))

    slides_html = "\n".join(slides)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_escape(topic)} - ITE</title>
    <link rel="stylesheet" href="{REVEAL_CSS}">
    <link rel="stylesheet" href="{REVEAL_THEME}">
    <link href="{MONTSERRAT}" rel="stylesheet">
    <style>
        .reveal .slides {{ text-align: left; font-family: 'Segoe UI', sans-serif; }}
        .reveal h1, .reveal h2, .reveal h3 {{ font-family: 'Montserrat', sans-serif; }}
        .grey-label {{ color:#767676; font-size:0.75rem; text-transform:uppercase; margin-bottom:0.3em; }}
        .q-meta {{ color:#767676; font-size:0.9rem; margin-bottom:0.5em; }}
        .poll-stem {{ font-size:1.1rem; margin:0.8em 0; line-height:1.5; }}
        .poll-options {{ display:flex; flex-direction:column; gap:0.4em; }}
        .poll-opt {{
            padding:0.5em 0.8em; text-align:left; font-size:0.95rem;
            background:#f5f5f5; border:2px solid #ddd; border-radius:6px;
            cursor:pointer; transition:all 0.2s;
            font-family: inherit;
        }}
        .poll-opt:hover {{ background:#eaeaea; border-color:#999; }}
        .poll-opt.voted {{ background:#d4edda; border-color:#28a745; }}
        .poll-results {{ margin-top:1em; min-height:120px; }}
        .poll-reset {{ margin-top:0.5em; padding:0.3em 0.8em; font-size:0.85rem; cursor:pointer; }}
        .critique-body {{ font-size:0.95rem; line-height:1.6; color:#555; }}
        .bar-chart {{ display:flex; flex-direction:column; gap:0.3em; }}
        .bar-row {{ display:flex; align-items:center; gap:0.5em; }}
        .bar-label {{ width:2em; }}
        .bar-fill {{ height:1.5em; background:#4a90d9; border-radius:4px; min-width:2em; }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}
        </div>
    </div>
    <script src="{REVEAL_JS}"></script>
    <script>
        Reveal.initialize({{ hash: true, transition: 'slide' }});
        const wsUrl = (location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + location.host + '/ws';
        let ws = null;
        const pollResults = {{}};
        let role = location.search.includes('audience') ? 'audience' : 'presenter';
        document.getElementById('join-url').textContent = location.href.split('?')[0] + '?audience';
        function connect() {{
            ws = new WebSocket(wsUrl);
            ws.onopen = () => ws.send(JSON.stringify({{ role, poll: null }}));
            ws.onmessage = (e) => {{
                const d = JSON.parse(e.data);
                if (d.type === 'results') {{
                    pollResults[d.poll] = d.votes || {{}};
                    showResults(d.poll, pollResults[d.poll]);
                }} else if (d.type === 'reset') {{
                    pollResults[d.poll] = {{}};
                    const res = document.getElementById('results-' + d.poll);
                    if (res) res.innerHTML = 'Votes appear here in real-time.';
                }}
            }};
            ws.onclose = () => setTimeout(connect, 2000);
        }}
        connect();

        if (role === 'audience') {{
            document.querySelectorAll('.poll-reset').forEach(b => b.style.display = 'none');
        }} else {{
            document.querySelectorAll('.poll-reset').forEach(b => {{
                b.style.display = 'inline-block';
                b.onclick = () => {{
                    const pid = b.dataset.poll;
                    if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'reset', poll: pid }}));
                }};
            }});
        }}

        document.querySelectorAll('.poll-opt').forEach(btn => {{
            btn.onclick = () => {{
                if (role !== 'audience') return;
                const pid = btn.dataset.poll;
                const choice = btn.dataset.choice;
                if (ws && ws.readyState === 1) ws.send(JSON.stringify({{ type: 'vote', poll: pid, choice }}));
                btn.classList.add('voted');
            }};
        }});

        function showResults(pollId, votes) {{
            const el = document.getElementById('results-' + pollId);
            if (!el) return;
            const max = Math.max(...Object.values(votes), 1);
            el.innerHTML = '<div class="bar-chart">' + Object.entries(votes).sort((a,b)=>a[0].localeCompare(b[0])).map(([k,v]) =>
                '<div class="bar-row"><span class="bar-label">'+k+')</span><div class="bar-fill" style="width:'+(v/max*100)+'%"></div><span>'+v+'</span></div>'
            ).join('') + '</div>';
        }}

        Reveal.on('slidechanged', e => {{
            const resDiv = e.currentSlide?.querySelector?.('.poll-results[id^="results-"]');
            if (resDiv) {{
                const pollId = resDiv.id.replace('results-', '');
                if (pollResults[pollId] && Object.keys(pollResults[pollId]).length) {{
                    showResults(pollId, pollResults[pollId]);
                }}
            }}
        }});
    </script>
</body>
</html>'''


def main():
    data_path = DATA_FILE if DATA_FILE.exists() else SCRIPT_DIR / "ite_data_sample.json"
    if not data_path.exists():
        print("Run extract_ite.py first.")
        return 1

    with open(data_path, encoding="utf-8") as f:
        all_q = json.load(f)

    by_topic = defaultdict(list)
    for q in all_q:
        by_topic[q.get("topic") or "General Medicine"].append(q)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for topic in sorted(by_topic.keys()):
        safe = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")
        path = OUTPUT_DIR / f"{safe}.html"
        html = build_html(topic, by_topic[topic])
        path.write_text(html, encoding="utf-8")
        print(f"Created: {path}")

    index = OUTPUT_DIR / "index.html"
    items = "".join(
        f'<li><a href="{re.sub(r"[^\w\s-]", "", t).strip().replace(" ", "_")}.html">{_escape(t)}</a></li>\n'
        for t in sorted(by_topic.keys())
    )
    index.write_text(
        f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>ITE Presentations</title></head>
<body><h1>ITE Interactive Presentations</h1><ul>
{items}</ul>
<p style="color:#767676;margin-top:2em;">
  Open <strong>Open_ITE_HTML_Polls.bat</strong> in the ITE_Files folder, then use the URL it prints
  (for example <code>http://127.0.0.1:8765/</code>). Pick a topic below.
  <br/><br/>
  Do not double-click these .html files for live polls — voting needs the running server.
  For a public internet link, use Render hosting or <code>run_live.py</code> with cloudflared.
</p>
</body></html>""",
        encoding="utf-8",
    )
    print(f"Created: {index}")

    print("\nNext: double-click Open_ITE_HTML_Polls.bat or run: python poll_server.py")
    return 0


if __name__ == "__main__":
    exit(main())
