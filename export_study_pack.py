"""
Build ONE shareable study file — no Python, server, or folder needed for recipients.

  python export_study_pack.py
  python export_study_pack.py --out "C:\\Users\\Me\\Desktop\\ITE_Study.html"

Opens in any browser (Chrome, Edge, Safari). Works offline after you save/send the file.
This is for self-paced study (reveal answer + critique). It is NOT live audience polling.

Live voting always needs either: this repo + Python, or a hosted URL, or Vevox/Slido/etc.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "ite_data.json"


def _strip_replacement_glyphs(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"[\uFFFD\uF000-\uF8FF]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description="Export single-file ITE study HTML")
    ap.add_argument("--out", type=Path, help="Output .html path (default: ITE_Study_Pack.html here)")
    ap.add_argument("--topic", help="Only include questions whose topic contains this (case-insensitive)")
    ap.add_argument("--year", type=int, help="Only include this exam year")
    ap.add_argument("--limit", type=int, help="Max questions after filters")
    args = ap.parse_args()

    if not DATA.is_file():
        raise SystemExit(f"Missing {DATA} — run extract_ite.py first.")

    raw = json.loads(DATA.read_text(encoding="utf-8"))
    rows = []
    for item in raw:
        if args.topic and args.topic.lower() not in (item.get("topic") or "").lower():
            continue
        if args.year is not None and item.get("year") != args.year:
            continue
        opts = item.get("options") or {}
        letters = sorted(opts.keys())
        rows.append(
            {
                "n": item.get("number"),
                "y": item.get("year"),
                "topic": _strip_replacement_glyphs(item.get("topic") or ""),
                "subtopic": _strip_replacement_glyphs(item.get("subtopic") or ""),
                "stem": _strip_replacement_glyphs(item.get("stem") or ""),
                "options": {k: _strip_replacement_glyphs(v) for k, v in opts.items()},
                "letters": letters,
                "answer": (item.get("answer") or "").strip().upper()[:1],
                "critique": _strip_replacement_glyphs(item.get("critique") or ""),
            }
        )
        if args.limit and len(rows) >= args.limit:
            break

    if not rows:
        raise SystemExit("No questions after filters.")

    payload = json.dumps(rows, ensure_ascii=False)
    payload = payload.replace("</script>", "<\\/script>")

    out = args.out or (ROOT / "ITE_Study_Pack.html")
    out = out.resolve()
    out.write_text(TEMPLATE.replace("__EMBED__", payload), encoding="utf-8")
    print(f"Wrote {len(rows)} questions -> {out}")
    print("Share only that .html file. Recipients double-click it (or open in browser).")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ITE study pack</title>
<style>
  :root { --ink:#37474f; --muted:#78909c; --ok:#2e7d32; --bg:#eceff1; --card:#fff; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", system-ui, sans-serif; background:var(--bg); color:var(--ink); min-height:100vh; }
  header { background:var(--ink); color:#fff; padding:0.6rem 1rem; display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center; justify-content:space-between; }
  header label { font-size:0.8rem; opacity:0.9; }
  header select { font-size:0.85rem; padding:0.25rem 0.5rem; border-radius:4px; border:none; max-width:14rem; }
  .bar { font-size:0.85rem; opacity:0.9; }
  main { max-width:40rem; margin:0 auto; padding:1rem 1rem 5rem; }
  .card { background:var(--card); border-radius:10px; padding:1rem 1.1rem; box-shadow:0 2px 10px rgba(0,0,0,.08); }
  .meta { font-size:0.78rem; color:var(--muted); margin-bottom:0.5rem; }
  .stem { font-size:0.98rem; line-height:1.45; white-space:pre-wrap; margin-bottom:0.75rem; }
  .opts { margin:0; padding:0; list-style:none; }
  .opts li { padding:0.4rem 0; border-bottom:1px solid #eee; font-size:0.9rem; line-height:1.35; }
  .opts li.correct { background:#e8f5e9; margin:0 -0.5rem; padding-left:0.5rem; padding-right:0.5rem; border-radius:4px; border-bottom-color:transparent; }
  .opts .L { font-weight:700; margin-right:0.35rem; }
  .hidden { display:none !important; }
  .reveal-box { margin-top:0.85rem; padding:0.75rem; border-radius:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-size:0.88rem; line-height:1.4; white-space:pre-wrap; }
  .reveal-box.ok { background:#e8f5e9; border-color:#a5d6a7; color:#1b5e20; }
  .foot { position:fixed; left:0; right:0; bottom:0; padding:0.55rem 1rem; background:rgba(255,255,255,.98); border-top:1px solid #ccc; display:flex; flex-wrap:wrap; gap:0.45rem; justify-content:center; align-items:center; z-index:10; }
  button { font:inherit; font-weight:600; padding:0.5rem 0.9rem; border:none; border-radius:8px; cursor:pointer; background:#1565c0; color:#fff; }
  button.secondary { background:#607d8b; }
  button.ghost { background:#cfd8dc; color:var(--ink); }
  .hint { width:100%; text-align:center; font-size:0.72rem; color:var(--muted); margin:0; }
</style>
</head>
<body>
<header>
  <span class="bar" id="progress">—</span>
  <label>Topic <select id="topic"></select></label>
</header>
<main>
  <div id="empty" class="card hidden"><p>No questions for this topic.</p></div>
  <div id="panel" class="card hidden">
    <div class="meta" id="qmeta"></div>
    <div class="stem" id="stem"></div>
    <ul class="opts" id="opts"></ul>
    <div id="answerLine" class="reveal-box ok hidden"></div>
    <div id="critBox" class="reveal-box hidden"></div>
  </div>
</main>
<div class="foot">
  <button type="button" id="btnAns" class="ghost">Show answer</button>
  <button type="button" id="btnCrit" class="ghost" disabled>Show critique</button>
  <button type="button" id="btnPrev" class="secondary">← Previous</button>
  <button type="button" id="btnNext">Next →</button>
  <p class="hint">Arrow keys ← → also work</p>
</div>
<script type="application/json" id="deck">__EMBED__</script>
<script>
(function(){
  var ALL = JSON.parse(document.getElementById('deck').textContent);
  var topics = {};
  ALL.forEach(function(q){
    var t = q.topic || 'General';
    if (!topics[t]) topics[t] = [];
    topics[t].push(q);
  });
  var topicNames = Object.keys(topics).sort();
  var sel = document.getElementById('topic');
  var optAll = document.createElement('option');
  optAll.value = '__all__';
  optAll.textContent = 'All topics (' + ALL.length + ')';
  sel.appendChild(optAll);
  topicNames.forEach(function(t){
    var o = document.createElement('option');
    o.value = t;
    o.textContent = t + ' (' + topics[t].length + ')';
    sel.appendChild(o);
  });

  var qs = ALL.slice();
  var i = 0;

  function current() { return qs[i]; }

  function applyTopic() {
    var v = sel.value;
    if (v === '__all__') qs = ALL.slice();
    else qs = topics[v] ? topics[v].slice() : [];
    i = 0;
    render();
  }

  function render() {
    var panel = document.getElementById('panel');
    var empty = document.getElementById('empty');
    document.getElementById('answerLine').classList.add('hidden');
    document.getElementById('critBox').classList.add('hidden');
    document.getElementById('btnCrit').disabled = true;
    if (!qs.length) {
      panel.classList.add('hidden');
      empty.classList.remove('hidden');
      document.getElementById('progress').textContent = '—';
      return;
    }
    empty.classList.add('hidden');
    panel.classList.remove('hidden');
    var q = qs[i];
    document.getElementById('progress').textContent = 'Q ' + (i+1) + ' / ' + qs.length + ' · #' + q.n + ' (' + q.y + ')';
    document.getElementById('qmeta').textContent = (q.topic||'') + (q.subtopic ? ' · ' + q.subtopic : '');
    document.getElementById('stem').textContent = q.stem || '';
    var ul = document.getElementById('opts');
    ul.innerHTML = '';
    (q.letters || []).forEach(function(L){
      var li = document.createElement('li');
      li.id = 'opt-' + L;
      var lab = document.createElement('span');
      lab.className = 'L';
      lab.textContent = L + '.';
      li.appendChild(lab);
      li.appendChild(document.createTextNode(' ' + (q.options[L] || '')));
      ul.appendChild(li);
    });
  }

  function showAnswer() {
    var q = current();
    if (!q) return;
    var L = q.answer;
    var line = document.getElementById('answerLine');
    line.classList.remove('hidden');
    var txt = (L && q.options[L]) ? (L + '. ' + q.options[L]) : ('Answer: ' + (L || '?'));
    line.textContent = 'Correct: ' + txt;
    (q.letters || []).forEach(function(x){
      var el = document.getElementById('opt-' + x);
      if (el) el.classList.toggle('correct', x === L);
    });
    document.getElementById('btnCrit').disabled = false;
  }

  function showCrit() {
    var q = current();
    if (!q) return;
    var c = document.getElementById('critBox');
    c.textContent = q.critique || '(No critique text)';
    c.classList.remove('hidden');
  }

  sel.addEventListener('change', applyTopic);
  document.getElementById('btnAns').addEventListener('click', showAnswer);
  document.getElementById('btnCrit').addEventListener('click', showCrit);
  document.getElementById('btnPrev').addEventListener('click', function(){
    if (i > 0) { i--; render(); }
  });
  document.getElementById('btnNext').addEventListener('click', function(){
    if (i < qs.length - 1) { i++; render(); }
  });
  document.addEventListener('keydown', function(e){
    if (e.target.matches('select')) return;
    if (e.key === 'ArrowLeft') document.getElementById('btnPrev').click();
    if (e.key === 'ArrowRight') document.getElementById('btnNext').click();
  });

  render();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
