---
name: task-retro-confirm
description: After completing a task, consolidate retrospect findings into a single self-contained "待确认事项" HTML page. The page lists candidate points to persist into long-term memory (记忆类) and candidate points to abstract into Skills (Skill类); each item has a checkbox, and checking it expands an editable "可执行提示词" (executable prompt) the user can copy directly. Supports copy-single, copy-all-checked, and generate-confirmation-list. Pure front-end, no external dependencies, works offline. Use this skill whenever a task wraps up and the user wants to capture reusable knowledge or patterns without anything being auto-written — e.g. "复盘一下可以沉淀的点" / "给个待确认清单".
agent_created: true
---

# task-retro-confirm（任务复盘 · 待确认事项生成器）

## 用途

任务完成后，把「可以沉淀进长期记忆的点」和「可以抽象成 Skill 的点」整理成一张**可勾选、勾选即展开可执行提示词**的确认页。本页只做确认，不自动写任何记忆、不自动建 Skill——用户勾完复制、确认后再让 Agent 落地。

核心交互（复用自实战 deliverable，已验证稳定）：
- 候选项分两组：**记忆类**（memory）/ **Skill 类**（skill）
- 勾选任一项 → 展开对应「可执行提示词」文本框（写记忆 / 建 skill 的具体指令）
- 工具栏：**全选 / 清空 / 复制已勾选提示词 / 生成确认清单**
- 「生成确认清单」汇总所有勾选项为一段可直接发给 AI 执行的文本，单条和整段都能一键复制
- 纯前端、零依赖、离线可用（无 CDN、无外链图）

## 何时使用

- 用户说「复盘一下这次能沉淀什么」「给个待确认清单」「把可复用点整理成确认页」等
- 任何较复杂的任务收尾，需要把经验固化为记忆或 Skill，但不想直接动手、要先让用户拍板
- 与 `next-actions-decision-list` 的区别：本 skill 面向「复盘沉淀（记忆/Skill）」，后者面向「下一步行动 / 决策选择」

## 使用流程

1. **梳理候选点**：回顾本次任务，列出若干（通常 3–8 条）候选：
   - 记忆类：可写进用户级 `MEMORY.md` 的通用方法论 / recurring 需求 / 踩坑铁律
   - Skill 类：可抽象成 WorkBuddy skill 的通用流程 / 领域专用流程 / 元流程
   每条包含 `id`（如 M1 / S1）、`type`（`memory` 或 `skill`）、`title`、`why`（为什么值得沉淀）、`prompt`（完整可执行的提示词文本）。

2. **生成确认页（二选一）**：
   - **推荐：用脚本生成**。先写一个 `items.json`（结构见 `references/sample_items.json`），再运行：
     ```bash
     PY="C:/Users/Sxg/.workbuddy/binaries/python/versions/3.13.12/python.exe"
     "$PY" "<skill_dir>/scripts/gen_retro.py" "<items.json绝对路径>" "<输出.html绝对路径>"
     ```
     脚本会把 `references/skeleton.html` 的三个占位符（`__TITLE__` / `__LEAD__` / `__DATA__`）替换为内容，产出自包含 HTML。
   - **或手写**：直接复制 `references/skeleton.html`，把 `const RETRO_DATA = __DATA__;` 处的占位符换成真实 JSON（`{"items":[...]}`），并替换 `__TITLE__` / `__LEAD__`。

3. **交付**：用 `present_files` 预览生成的 HTML。明确告知用户——本页仅用于确认，不会自动写记忆或建 Skill；用户勾完复制、再让你「把勾中的落地」才执行。

## 资源

- `references/skeleton.html` — 自包含 HTML 骨架（含完整 CSS/JS 交互与样式），仅 `__TITLE__` / `__LEAD__` / `__DATA__` 三处占位符，生成时替换。
- `references/sample_items.json` — 一份完整样例（含记忆类 M1–M3、Skill 类 S1–S3），可直接改文案复用，也是格式范本。
- `scripts/gen_retro.py` — 读取 `items.json` → 注入骨架 → 写出自包含 HTML。无第三方依赖（仅标准库）。

## 提示词撰写约定（写进 `prompt` 字段）

- 写记忆类：开头写明「【写入长期记忆】请追加到用户级 MEMORY.md（路径用真实 `.workbuddy` 路径，如 `C:\Users\Sxg\.workbuddy\user-5a696d89-dd2c-4075-9023-9ca1e8cf243b-personal\MEMORY.md`）」，正文用 Markdown 二级标题分段。
- 建 Skill 类：开头写明「【创建 Skill】名称：xxx」，正文给出触发场景、输入参数、流程步骤、交付物。
- 提示词必须**自包含、可直接执行**，用户复制后粘给任意 AI Agent 平台都能照做，不依赖当前对话上下文。
