#!/usr/bin/env python3
"""Build rehab/*.md pages from data/rehab/*.txt.

Data format:
  ## 大標題          -> new page (section)
  ### 小標題         -> subsection inside page
  @115-2#58|A [〔標籤〕]
  題幹 (one or more lines)
  A. ...
  B. ...
  C. ...
  D. ...
  > 解析 (one or more lines)
"""
import re, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "rehab"
OUT = ROOT / "rehab"

# exam label -> (考選部 code, subject code)
EXAMS = {
    "110-1": ("110020", "44"), "110-2": ("110080", "44"),
    "111-1": ("111020", "44"), "111-2": ("111080", "44"),
    "112-1": ("112020", "44"), "112-2": ("112080", "44"),
    "113-1": ("113020", "44"), "113-2": ("113070", "44"),
    "114-1": ("114020", "0106"), "114-2": ("114070", "0104"),
    "115-1": ("115020", "0106"), "115-2": ("115070", "0104"),
}
def pdf(label, t="Q"):
    code, s = EXAMS[label]
    return f"https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t={t}&code={code}&c=302&s={s}&q=1"

SLUGS = ["neuro", "peripheral", "msk", "pain-modality", "prosthetics",
         "cardiopulm", "peds", "geriatric", "cancer", "function"]

def parse():
    sections = []  # [title, [items]] where item = ("sub", title) | ("q", dict)
    for f in sorted(DATA.glob("*.txt")):
        cur_q = None
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line.startswith("## "):
                sections.append([line[3:].strip(), []]); cur_q = None
            elif line.startswith("### "):
                sections[-1][1].append(("sub", line[4:].strip())); cur_q = None
            elif line.startswith("@"):
                m = re.match(r"@(\d{3}-\d)#(\d+)\|(\S+)\s*(.*)", line)
                if not m: sys.exit(f"bad header: {line}")
                cur_q = dict(exam=m[1], no=int(m[2]), ans=m[3], tag=m[4].strip(),
                             stem=[], opts=[], exp=[])
                sections[-1][1].append(("q", cur_q))
            elif cur_q is not None and line:
                if line.startswith(">"):
                    cur_q["exp"].append(line[1:].strip())
                elif re.match(r"^[A-D]\. ", line):
                    cur_q["opts"].append(line)
                elif cur_q["opts"]:
                    cur_q["opts"][-1] += line
                else:
                    cur_q["stem"].append(line)
    return sections

def render_q(q, n):
    src = f"[{q['exam'].replace('-', '年第')}次 #{q['no']}]({pdf(q['exam'])})"
    tag = f" {q['tag']}" if q["tag"] else ""
    img = "（附圖請見原卷 PDF）" if "影像" in q["tag"] else ""
    lines = [f"**Q{n}.** <small>{src}{tag}</small>", "",
             " ".join(q["stem"]) + img + "  "]
    lines += [o + "  " for o in q["opts"]]
    exp = "<br>".join(md_inline(e) for e in q["exp"])
    lines += ["", f"<details><summary>答案</summary><p><b>{q['ans']}</b><br>{exp}</p></details>", "", "---", ""]
    return "\n".join(lines)

def md_inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s

def main():
    sections = parse()
    assert len(sections) == len(SLUGS), [s[0] for s in sections]
    OUT.mkdir(exist_ok=True)
    seen = collections.Counter()
    toc = []
    for (title, items), slug in zip(sections, SLUGS):
        nq = sum(1 for k, _ in items if k == "q")
        subs = [v for k, v in items if k == "sub"]
        body = ["---", f"title: 復健科 | {title}", "---", "",
                f"# {title}", "", "[← 復健科目錄](./) · [首頁](../)", ""]
        if subs:
            body += [" · ".join(f"[{s}](#{anchor(s)})" for s in subs), ""]
        n = 0
        for k, v in items:
            if k == "sub":
                body += [f"## {v}", ""]
            else:
                n += 1
                seen[(v["exam"], v["no"])] += 1
                body.append(render_q(v, n))
        body += ["[↑ Back to top](#)", ""]
        (OUT / f"{slug}.md").write_text("\n".join(body), encoding="utf-8")
        toc.append((title, slug, nq, subs))
    # coverage check: core rehab block Q58–71 of every paper
    missing = [(e, i) for e in EXAMS for i in range(58, 72) if (e, i) not in seen]
    dup = [k for k, c in seen.items() if c > 1]
    if missing or dup:
        sys.exit(f"missing={missing} dup={dup}")
    total = sum(seen.values())
    write_index(toc, total)
    print(f"built {len(toc)} pages, {total} questions")

def anchor(s):
    # kramdown auto-id: lowercase, drop punctuation except - and _
    a = s.strip().lower()
    a = re.sub(r"[^\w\- ]", "", a)
    return re.sub(r"\s+", "-", a)

def write_index(toc, total):
    rows = "\n".join(
        f"| [{t}]({slug}) | {n} | {'、'.join(subs) if subs else '—'} |" for t, slug, n, subs in toc)
    exams = " · ".join(f"[{e}]({pdf(e)})" for e in EXAMS)
    txt = f"""---
title: 復健科
---

# 復健科

[← 首頁](../)

**範圍**：110–115 年醫師（二）醫學（六），每卷第 58–71 題（復健科區塊），另收錄第 72–77 題中與復健相關的影像/臨床實例題。共 **{total} 題**。
**答案**：考選部標準答案，已依「更正答案」修正（送分、多答案均註明）。點開「答案」看解析。

| 主題 | 題數 | 子題 |
|---|---|---|
{rows}

**原卷 PDF（考選部）**：{exams}

<small>題號標示：「115年第2次 #58」= 115 年第二次醫師二階考試醫學（六）第 58 題。</small>
"""
    (OUT / "index.md").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
