# -*- coding: utf-8 -*-
"""把 BRD/PRD 的 docx 解成只读纯文本副本，供 grep 对账。以 docx 为准，本产物机器生成。"""
import io, os, re, zipfile

SRC = 'docs/权威规格'
DST = os.path.join(SRC, '_extracted')
FILES = [('UAE_Match_BRD_v2.1.docx', 'UAE_Match_BRD_v2.1.txt'),
         ('UAE_Match_PRD_v1.1.docx', 'UAE_Match_PRD_v1.1.txt')]

HEAD = (u'# 机器生成的纯文本副本 —— 仅供 grep 对账，不可作为权威源\n'
        u'# 权威源：%s（同目录）。二者不一致时一律以 docx 为准。\n'
        u'# 生成方式：scripts/extract_specs.py（解压 word/document.xml 去标签，段落换行）\n'
        u'# 用途：让"BRD 里说…"这类引用可被 grep 三秒验证，而非靠记忆。\n'
        u'# ' + u'=' * 70 + u'\n\n')

os.makedirs(DST, exist_ok=True)
out = io.open(1, 'w', encoding='utf-8', closefd=False)
for src, dst in FILES:
    p = os.path.join(SRC, src)
    x = zipfile.ZipFile(p).read('word/document.xml').decode('utf-8')
    x = re.sub(r'</w:p>', '\n', x)
    x = re.sub(r'<[^>]+>', '', x)
    t = re.sub(r'\n{2,}', '\n', x)
    body = (HEAD % src) + t
    op = os.path.join(DST, dst)
    open(op, 'w', encoding='utf-8', newline='').write(body)
    out.write(u'%s  %d 字符\n' % (op.replace(os.sep, '/'), len(t)))

readme = (u'# 权威规格 · 纯文本副本（_extracted）\n\n'
          u'> **不是权威源。** 权威源是上一级目录的两份 `.docx`；本目录是它们的机器生成纯文本，\n'
          u'> 唯一用途是让 `grep` 能检索权威内容——避免"BRD 里说…"只能靠记忆引用而导致漂移。\n\n'
          u'| 文件 | 来源 |\n|---|---|\n'
          u'| `UAE_Match_BRD_v2.1.txt` | `../UAE_Match_BRD_v2.1.docx` |\n'
          u'| `UAE_Match_PRD_v1.1.txt` | `../UAE_Match_PRD_v1.1.docx` |\n\n'
          u'## 纪律\n\n'
          u'- **只读**：任何内容修改必须改 docx 后重新生成，禁止直接编辑 txt。\n'
          u'- **不一致时以 docx 为准**：格式（表格、批注、样式）在转换中会丢失，正文文字保留。\n'
          u'- **docx 升版后必须重跑**：`python scripts/extract_specs.py`（仓库根目录执行）。\n'
          u'- 引用时仍写权威出处（如 `BRD §8.2`、`PRD 2.2`），不要引用本目录的行号——行号随重新生成而变。\n')
open(os.path.join(DST, 'README.md'), 'w', encoding='utf-8', newline='').write(readme)
out.write(u'%s/README.md\n' % DST.replace(os.sep, '/'))
out.flush()
