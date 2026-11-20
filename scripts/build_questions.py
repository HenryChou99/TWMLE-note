#!/usr/bin/env python3
"""Build 考古題 pages (docs/<科目>/<科別>考古題.md) from data/<slug>/*.txt.

Data format:
  ## 大標題          -> H2 section (numbered by order of appearance)
  ### 小標題         -> H3 subsection
  @115-2#58|A [〔標籤〕]
  @三/115-2#75|C       (跨卷科別：卷別前綴 三/四/五/六 = 醫學（三）…（六）)
  題幹 (one or more lines)
  A. ...
  B. ...
  C. ...
  D. ...
  > 解析 (one or more lines)

Usage: python3 scripts/build_questions.py            # build all
       python3 scripts/build_questions.py rehab      # build one
"""
import re, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent

# exam label -> 考選部 exam code
EXAM_CODES = {
    "110-1": "110020", "110-2": "110080", "111-1": "111020", "111-2": "111080",
    "112-1": "112020", "112-2": "112080", "113-1": "113020", "113-2": "113070",
    "114-1": "114020", "114-2": "114070", "115-1": "115020", "115-2": "115070",
}
# 考選部 subject code (s=) per paper; changed format from 114 年起
SUBJECT = {
    "醫學（三）": {**{e: "11" for e in EXAM_CODES}, "114-1": "0103", "114-2": "0101", "115-1": "0103", "115-2": "0101"},
    "醫學（四）": {**{e: "22" for e in EXAM_CODES}, "114-1": "0104", "114-2": "0102", "115-1": "0104", "115-2": "0102"},
    "醫學（五）": {**{e: "33" for e in EXAM_CODES}, "114-1": "0105", "114-2": "0103", "115-1": "0105", "115-2": "0103"},
    "醫學（六）": {**{e: "44" for e in EXAM_CODES}, "114-1": "0106", "114-2": "0104", "115-1": "0106", "115-2": "0104"},
}

SPECIALTIES = {
    "neuro": dict(name="神經內科", paper="醫學（四）", folder="醫學四", core=range(44, 59),
                  skip={("110-1", 44)},
                  scope="每卷第 44–58 題（110 年第 1 次為第 45–58 題），另收錄第 74–78 題中與神經科相關的影像/臨床實例題"),
    "rehab": dict(name="復健科", paper="醫學（六）", folder="醫學六", core=range(58, 72),
                  scope="每卷第 58–71 題，另收錄第 72–77 題中與復健相關的影像/臨床實例題"),
    "anes": dict(name="麻醉科", paper="醫學（六）", folder="醫學六", core=range(1, 10),
                 scope="每卷第 1–9 題（含重症醫學），另收錄第 75–77 題中與呼吸道/急救相關的臨床實例題"),
    "oph": dict(name="眼科", paper="醫學（六）", folder="醫學六", core=range(10, 19),
                scope="每卷第 10–18 題，另收錄第 72–77 題中與眼科相關的影像/臨床實例題"),
    "uro": dict(name="泌尿科", paper="醫學（五）", folder="醫學五", core=range(64, 72),
                scope="每卷第 64–71 題，另收錄第 72–77 題中與泌尿相關的影像/臨床實例題"),
    "rad": dict(name="放射科", paper="醫學（三）～（六）", folder="放射科",
                core={"三": range(74, 76), "四": range(74, 76), "五": range(72, 75), "六": range(72, 75)},
                scope="各卷影像醫學題：醫學（三）、（四）第 74–75 題，醫學（五）、（六）第 72–74 題；另收錄醫學（四）113 年第 2 次 #76"),
    "ortho": dict(name="骨科", paper="醫學（五）", folder="醫學五", core=range(56, 64),
                  scope="每卷第 56–63 題（110 年第 2 次另含第 53–55 題組），另收錄第 72–77 題中與骨科相關的影像/臨床實例題；第十二章足踝重建於 110–115 年未出題"),
}


PAPER = {"三": "醫學（三）", "四": "醫學（四）", "五": "醫學（五）", "六": "醫學（六）"}


def pdf(spec, label, t="Q", paper=None):
    s = SUBJECT[PAPER[paper] if paper else spec["paper"]][label]
    return (f"https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx"
            f"?t={t}&code={EXAM_CODES[label]}&c=302&s={s}&q=1")


def parse(data_dir):
    sections = []  # [title, [("sub", title) | ("q", dict)]]
    for f in sorted(data_dir.glob("*.txt")):
        cur = None
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line.startswith("## "):
                sections.append([line[3:].strip(), []]); cur = None
            elif line.startswith("### "):
                sections[-1][1].append(("sub", line[4:].strip())); cur = None
            elif line.startswith("@"):
                m = re.match(r"@(?:([三四五六])/)?(\d{3}-\d)#(\d+)\|(\S+)\s*(.*)", line)
                if not m:
                    sys.exit(f"{f.name}: bad header: {line}")
                cur = dict(paper=m[1], exam=m[2], no=int(m[3]), ans=m[4], tag=m[5].strip(),
                           stem=[], opts=[], exp=[])
                sections[-1][1].append(("q", cur))
            elif cur is not None and line:
                if line.startswith("!fig "):
                    cur.setdefault("figs", []).extend(int(x) for x in line[5:].split())
                elif line.startswith(">"):
                    cur["exp"].append(line[1:].strip())
                elif re.match(r"^[A-D]\. ", line):
                    cur["opts"].append(line)
                elif cur["opts"]:
                    cur["opts"][-1] += line
                else:
                    cur["stem"].append(line)
    return sections


FIGS = {}


def load_figs(data_dir):
    """figures.tsv: id, Commons file name, author, license, caption"""
    FIGS.clear()
    f = data_dir / "figures.tsv"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                i, name, author, lic, cap = line.split("\t")
                FIGS[int(i)] = (name, author, lic, cap)


def fig_html(i, width=480):
    import html, urllib.parse
    name, author, lic, cap = FIGS[i]
    q = urllib.parse.quote(name.replace(" ", "_"))
    return (f'<figure><a href="https://commons.wikimedia.org/wiki/File:{q}" target="_blank" rel="noopener">'
            f'<img src="https://commons.wikimedia.org/wiki/Special:FilePath/{q}?width={width}" alt="{html.escape(cap)}" loading="lazy"></a>'
            f'<figcaption>{html.escape(cap)}<br><small>{html.escape(author)} · {lic} · Wikimedia Commons</small></figcaption></figure>')


def render_q(spec, q, n):
    pp = f" 醫學{q['paper']}" if q["paper"] else ""
    src = f"[{q['exam'].replace('-', '年第')}次{pp} #{q['no']}]({pdf(spec, q['exam'], paper=q['paper'])})"
    tag = f" {q['tag']}" if q["tag"] else ""
    img = "（附圖請見原卷）" if "影像" in q["tag"] else ""
    out = [f"**{n}.** {' '.join(q['stem'])}{img}", ""]
    out += [f"{o}  " for o in q["opts"]]
    out += ["", f"<small>{src}{tag}</small>", "", '??? note "答案"', f"    **{q['ans']}**", ""]
    kind = lambda e: "list" if re.match(r"^(- |\d+\. )", e) else ("table" if e.startswith("|") else "text")
    prev = None
    for i, e in enumerate(q["exp"]):
        k = kind(e)
        if prev is not None and k != prev and (k != "text" or prev != "text"):
            out.append("")  # blank line so lists/tables render as blocks
        brk = "  " if k == "text" and i < len(q["exp"]) - 1 else ""
        out.append(f"    {e}{brk}")
        prev = k
    if q.get("figs"):
        out += ["", "    <div class=\"rad-gallery rad-ref\"><p>參考影像（非原題附圖，示範典型表現）</p>"]
        out += [f"    {fig_html(i)}" for i in q["figs"]]
        out += ["    </div>"]
    out += [""]
    return "\n".join(out)


def build(slug):
    spec = SPECIALTIES[slug]
    sections = parse(ROOT / "data" / slug)
    load_figs(ROOT / "data" / slug)
    seen = collections.Counter()
    body = [f"# {spec['name']}考古題", "",
            '!!! info "說明"',
            f"    110–115 年醫師（二）{spec['paper']}{spec['name']}題目（{spec['scope']}），"
            f"章節編號對應[{spec['name']}重點筆記]({spec['name']}.md)。答案已依考選部更正答案修正。",
            ""]
    for i, (title, items) in enumerate(sections, 1):
        body += [f"## {title}", ""]
        sub, n = 0, 0
        for k, v in items:
            if k == "sub":
                sub += 1
                body += [f"### {i}.{sub} {re.sub(r'^\d+\.\s*', '', v)}", ""]
            else:
                n += 1
                seen[(v["paper"], v["exam"], v["no"])] += 1
                body.append(render_q(spec, v, n))
    core = spec["core"] if isinstance(spec["core"], dict) else {None: spec["core"]}
    missing = [(pp, e, j) for pp, rng in core.items() for e in EXAM_CODES for j in rng
               if (pp, e, j) not in seen and (e, j) not in spec.get("skip", ())]
    dup = [k for k, c in seen.items() if c > 1]
    if missing or dup:
        sys.exit(f"{slug}: missing={missing} dup={dup}")
    out = ROOT / "docs" / spec["folder"] / f"{spec['name']}考古題.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"built {out.relative_to(ROOT)}: {sum(seen.values())} questions")


if __name__ == "__main__":
    for slug in (sys.argv[1:] or SPECIALTIES):
        build(slug)
