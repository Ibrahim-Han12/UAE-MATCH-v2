# UAE Match 文档中心

> 面向阿联酋华人的 AI 红娘 · 严肃婚恋平台
> 最后更新：2026-08-10

## 唯一开发依据（权威）

| 文档 | 说明 |
|---|---|
| [权威规格/UAE_Match_BRD_v2.1.docx](权威规格/UAE_Match_BRD_v2.1.docx) | **业务需求（权威源）** |
| [权威规格/UAE_Match_PRD_v1.1.docx](权威规格/UAE_Match_PRD_v1.1.docx) | **产品需求（权威源）** |
| `../CLAUDE.md` | BRD v2.1 的工程提炼与铁律（项目根目录） |

## 已评审基线（HLD）

| 文档 | 说明 |
|---|---|
| [hld-current-state.md](hld-current-state.md) | 现状架构评估 + 对照 PRD v1.1 的差距分析 |
| [hld-m2-design.md](hld-m2-design.md) | **M2 概要设计**（含 2026-08-10 决策基线） |
| [open-questions.md](open-questions.md) | 待决问题与裁决记录（裁决号 DEC-xxx） |
| [glossary.md](glossary.md) | **术语与编号约定**（约定层）——动手前必读 |

## M2 开工顺序（hld-current-state §7）

```
①模型抽象层+计量(BR-209) → ②三层记忆(BR-202, 建在 Postgres)
→ ③账户/状态机/EID闸(BR-001, BR-107) → ④深访三层架构(BR-201)
→ ⑤推荐信流水线(BR-301) → ⑥Stripe AED 订阅(BR-501, BR-503)
```

## 目录结构

```
docs/
├── README.md              本文件
├── 权威规格/              BRD/PRD 权威源（docx）
├── hld-current-state.md   现状评估
├── hld-m2-design.md       M2 概要设计（基线）
├── open-questions.md      待决问题
└── archive/               ⚠️ v1.0 代码历史快照，勿作开发依据（见其 README）
```

## 术语

BRD/PRD=业务/产品需求 ｜ HLD/LLD=概要/详细设计 ｜ PDPL=UAE 个人数据保护法 ｜ EID=阿联酋身份证 ｜ 小缘=AI 红娘 ｜ S0–S7=用户状态机（PRD 2.2） ｜ P1–P3=冷启动三阶段（BRD §8.2） ｜ L1–L4=小缘能力分层 ｜ DEC-xxx=裁决号 ｜ BR-XYY=业务需求编号

> ⚠️ 编号易混淆：`S`、`L`、字母族（A/B/C/D/E/G）、圈码在本项目历史上曾各有 2–4 种含义。**唯一权威是 [glossary.md](glossary.md) §2**，新增编号前必查。
