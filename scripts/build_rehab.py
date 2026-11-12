#!/usr/bin/env python3
"""Build docs/醫學六/復健科考古題.md from data/rehab/*.txt.

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
    img = "（附圖請見原卷）" if "影像" in q["tag"] else ""
    out = [f"**{n}.** {' '.join(q['stem'])}{img}", ""]
    out += [f"{o}  " for o in q["opts"]]
    out += ["", f"<small>{src}{tag}</small>", "", '??? note "答案"', f"    **{q['ans']}**", ""]
    out += [f"    {e}" + ("  " if i < len(q['exp']) - 1 else "") for i, e in enumerate(q["exp"])]
    out += [""]
    return "\n".join(out)

def main():
    sections = parse()
    seen = collections.Counter()
    body = ["# 復健科考古題", "",
            '!!! info "說明"',
            "    110–115 年醫師（二）醫學（六）復健科題目（每卷第 58–71 題，另收錄第 72–77 題中與復健相關的影像/臨床實例題），章節編號對應[復健科重點筆記](復健科.md)。答案已依考選部更正答案修正。",
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
                body.append(render_q(v, n))
    missing = [(e, j) for e in EXAMS for j in range(58, 72) if (e, j) not in seen]
    dup = [k for k, c in seen.items() if c > 1]
    if missing or dup:
        sys.exit(f"missing={missing} dup={dup}")
    out = ROOT / "docs" / "醫學六" / "復健科考古題.md"
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"built {out.relative_to(ROOT)}: {sum(seen.values())} questions")

if __name__ == "__main__":
    main()
