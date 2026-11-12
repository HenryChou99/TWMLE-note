#!/usr/bin/env python3
"""Build 考古題 pages (docs/<科目>/<科別>考古題.md) from data/<slug>/*.txt.

Data format:
  ## 大標題          -> H2 section (numbered by order of appearance)
  ### 小標題         -> H3 subsection
  @115-2#58|A [〔標籤〕]
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
    "醫學（五）": {**{e: "33" for e in EXAM_CODES}, "114-1": "0105", "114-2": "0103", "115-1": "0105", "115-2": "0103"},
    "醫學（六）": {**{e: "44" for e in EXAM_CODES}, "114-1": "0106", "114-2": "0104", "115-1": "0106", "115-2": "0104"},
}

SPECIALTIES = {
    "rehab": dict(name="復健科", paper="醫學（六）", folder="醫學六", core=range(58, 72),
                  scope="每卷第 58–71 題，另收錄第 72–77 題中與復健相關的影像/臨床實例題"),
    "ortho": dict(name="骨科", paper="醫學（五）", folder="醫學五", core=range(56, 64),
                  scope="每卷第 56–63 題（110 年第 2 次另含第 53–55 題組），另收錄第 72–77 題中與骨科相關的影像/臨床實例題"),
}


def pdf(spec, label, t="Q"):
    s = SUBJECT[spec["paper"]][label]
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
                m = re.match(r"@(\d{3}-\d)#(\d+)\|(\S+)\s*(.*)", line)
                if not m:
                    sys.exit(f"{f.name}: bad header: {line}")
                cur = dict(exam=m[1], no=int(m[2]), ans=m[3], tag=m[4].strip(),
                           stem=[], opts=[], exp=[])
                sections[-1][1].append(("q", cur))
            elif cur is not None and line:
                if line.startswith(">"):
                    cur["exp"].append(line[1:].strip())
                elif re.match(r"^[A-D]\. ", line):
                    cur["opts"].append(line)
                elif cur["opts"]:
                    cur["opts"][-1] += line
                else:
                    cur["stem"].append(line)
    return sections


def render_q(spec, q, n):
    src = f"[{q['exam'].replace('-', '年第')}次 #{q['no']}]({pdf(spec, q['exam'])})"
    tag = f" {q['tag']}" if q["tag"] else ""
    img = "（附圖請見原卷）" if "影像" in q["tag"] else ""
    out = [f"**{n}.** {' '.join(q['stem'])}{img}", ""]
    out += [f"{o}  " for o in q["opts"]]
    out += ["", f"<small>{src}{tag}</small>", "", '??? note "答案"', f"    **{q['ans']}**", ""]
    out += [f"    {e}" + ("  " if i < len(q["exp"]) - 1 else "") for i, e in enumerate(q["exp"])]
    out += [""]
    return "\n".join(out)


def build(slug):
    spec = SPECIALTIES[slug]
    sections = parse(ROOT / "data" / slug)
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
                seen[(v["exam"], v["no"])] += 1
                body.append(render_q(spec, v, n))
    missing = [(e, j) for e in EXAM_CODES for j in spec["core"] if (e, j) not in seen]
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
