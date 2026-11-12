# TWMLE Note

台灣醫師國考二階考古題筆記（GitHub Pages 網站）。

- 網站：https://henrychou99.github.io/TWMLE-note/
- 題目原始資料：`data/<科別>/*.txt`（純文字，方便修改）
- 網站：MkDocs Material（`mkdocs.yml`、`docs/`）；考古題頁由 `python3 scripts/build_rehab.py` 產生 `docs/醫學六/復健科考古題.md`

## data 格式

```
## 大標題（= 一個網頁）
### 小標題
@115-2#58|A 〔影像題〕
題幹
A. ...
B. ...
C. ...
D. ...
> 解析
```

`115-2#58` = 115 年第二次醫師二階、醫學（六）第 58 題。答案已依考選部更正答案修正。
