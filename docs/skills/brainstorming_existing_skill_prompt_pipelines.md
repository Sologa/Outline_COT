# Existing-Skill-Derived Brainstorming Prompt Materials

> 嚴格 provenance 版本。
>
> 來源限制：
> 1. 只允許引用目前本機已存在的 skill 原文。
> 2. 不允許使用 `docs/skills/brainstorming_deep_research_report.pdf` 的 prompt。
> 3. 不允許使用 `research-ideation`。
> 4. 不允許把多個 skill 腦補成一套新的完整 condensed prompt。

> 這份文檔回答的是：
> - 哪些現有 skill 原文真的能提取成 copy-ready prompt
> - 哪些只能提取成 question stems / ideation scaffolds
> - 哪些只能證明方法或 critique 能力存在，但不能嚴格提取成 ChatGPT 可直接貼上的單一 prompt

<style>
:root {
  --ink:#111827; --muted:#4b5563; --line:#d1d5db; --blue:#1d4ed8; --green:#047857; --violet:#7c3aed;
  --bg:#f8fafc; --card:#ffffff;
}
.prompt-wrap {
  max-width: 1120px;
  margin: 0 auto;
  padding: 8px 0 32px;
  color: var(--ink);
}
.prompt-wrap .toolbar {
  display:flex; flex-wrap:wrap; gap:10px; margin:16px 0 18px;
}
.prompt-wrap button {
  appearance:none; border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8;
  padding:10px 14px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:700;
}
.prompt-wrap button.green { background:#ecfdf5; color:#065f46; border-color:#a7f3d0; }
.prompt-wrap button:hover { filter: brightness(0.98); }
.prompt-wrap .grid {
  display:grid; grid-template-columns: 1fr; gap:16px;
}
.prompt-wrap .card {
  background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px 16px 14px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.prompt-wrap .card h3 {
  font-size:18px; margin:0 0 6px 0;
}
.prompt-wrap .meta {
  font-size:13px; color:var(--muted); margin-bottom:10px;
}
.prompt-wrap textarea {
  width:100%; min-height:180px; resize:vertical; box-sizing:border-box;
  border:1px solid #cbd5e1; border-radius:8px; padding:12px;
  font-family:"Noto Sans Mono","DejaVu Sans Mono",monospace; font-size:13px; line-height:1.45;
  white-space:pre; background:#f8fafc; color:#111827;
}
.prompt-wrap .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.prompt-wrap .note {
  border-left:4px solid #f59e0b; background:#fffaf0; padding:12px 14px; border-radius:8px; margin:16px 0 22px;
  color:#78350f;
}
.prompt-wrap .success {
  border-left-color:#10b981; background:#f0fdf4; color:#065f46;
}
</style>

<script>
function copyText(id) {
  const el = document.getElementById(id);
  const text = el.value;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      flash(id);
    });
  } else {
    el.focus();
    el.select();
    document.execCommand('copy');
    flash(id);
  }
}
function flash(id) {
  const btns = document.querySelectorAll('[data-target="'+id+'"]');
  btns.forEach(btn => {
    const old = btn.textContent;
    btn.textContent = 'Copied';
    setTimeout(() => btn.textContent = old, 1200);
  });
}
function copyMany(ids, buttonId, fallbackLabel) {
  const joined = ids.map(id => document.getElementById(id).value).join('\n\n');
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(joined).then(() => {
      const btn = document.getElementById(buttonId);
      btn.textContent = 'Copied';
      setTimeout(() => btn.textContent = fallbackLabel, 1200);
    });
  } else {
    const ta = document.createElement('textarea');
    ta.value = joined;
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    const btn = document.getElementById(buttonId);
    btn.textContent = 'Copied';
    setTimeout(() => btn.textContent = fallbackLabel, 1200);
  }
}
</script>

<div class="prompt-wrap">

<div class="note">
這份檔案是 `current-skill-derived`，不是 `PDF-derived`。
<br>
所有可複製區塊都只來自現有 skill 原文，並保留原本的用途邊界。
</div>

<div class="note success">
嚴格模式下的核心限制：
<br>
- 可以抽 literal prompt template
<br>
- 可以抽 literal question stems
<br>
- 可以整理 method support / critique support
<br>
- 不能合法產生一份完整的 ChatGPT Pro condensed one-shot prompt
</div>

<div class="toolbar">
  <button id="copyAllLiteralBtn" onclick="copyMany(['research_template','research_example','research_deep_template','research_deep_example','sb_context_questions','sb_divergent_stems','sb_connection_prompts','sb_critical_questions','sb_safe_ideas_prompts'], 'copyAllLiteralBtn', 'Copy All Literal Skill Prompts')">Copy All Literal Skill Prompts</button>
  <button id="copyResearchOnlyBtn" class="green" onclick="copyMany(['research_template','research_example','research_deep_template','research_deep_example'], 'copyResearchOnlyBtn', 'Copy Literal Research Templates')">Copy Literal Research Templates</button>
  <button id="copyBrainstormOnlyBtn" class="green" onclick="copyMany(['sb_context_questions','sb_divergent_stems','sb_connection_prompts','sb_critical_questions','sb_safe_ideas_prompts'], 'copyBrainstormOnlyBtn', 'Copy Brainstorming Stems')">Copy Brainstorming Stems</button>
</div>

## 1. 可直接複製的 Literal Prompt Templates

這一區只收 skill 中明示的 prompt template 或 one-shot example。

<div class="grid">
  <div class="card">
    <h3>Research Skill · Prompt Template</h3>
    <div class="meta">
      來源 skill：`research`<br>
      來源檔案：[research/SKILL.md](/Users/xjp/.codex/skills/research/SKILL.md)<br>
      提取方式：literal template<br>
      適用性：`Direct prompt`<br>
      是否適合直接貼進 ChatGPT Pro：有條件適合；需先替換 `{topic}`、`{YYYY-MM-DD}`、`{step1_output}`、`{time_range}`
    </div>
    <textarea id="research_template" readonly>## Task
Research topic: {topic}
Current date: {YYYY-MM-DD}

Based on the following initial framework, supplement latest items and recommended research fields.

## Existing Framework
{step1_output}

## Goals
1. Verify if existing items are missing important objects
2. Supplement items based on missing objects
3. Continue searching for {topic} related items within {time_range} and supplement
4. Supplement new fields

## Output Requirements
Return structured results directly (do not write files):

### Supplementary Items
- item_name: Brief explanation (why it should be added)
...

### Recommended Supplementary Fields
- field_name: Field description (why this dimension is needed)
...

### Sources
- [Source1](url1)
- [Source2](url2)</textarea>
    <div class="row"><button data-target="research_template" onclick="copyText('research_template')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Research Skill · One-shot Example</h3>
    <div class="meta">
      來源 skill：`research`<br>
      來源檔案：[research/SKILL.md](/Users/xjp/.codex/skills/research/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Direct prompt`<br>
      是否適合直接貼進 ChatGPT Pro：可直接當範例改寫；原始主題是 `AI Coding History`
    </div>
    <textarea id="research_example" readonly>## Task
Research topic: AI Coding History
Current date: 2025-12-30

Based on the following initial framework, supplement latest items and recommended research fields.

## Existing Framework
### Items List
1. GitHub Copilot: Developed by Microsoft/GitHub, first mainstream AI coding assistant
2. Cursor: AI-first IDE, based on VSCode
...

### Field Framework
- Basic Info: name, release_date, company
- Technical Features: underlying_model, context_window
...

## Goals
1. Verify if existing items are missing important objects
2. Supplement items based on missing objects
3. Continue searching for AI Coding History related items within since 2024 and supplement
4. Supplement new fields

## Output Requirements
Return structured results directly (do not write files):

### Supplementary Items
- item_name: Brief explanation (why it should be added)
...

### Recommended Supplementary Fields
- field_name: Field description (why this dimension is needed)
...

### Sources
- [Source1](url1)
- [Source2](url2)</textarea>
    <div class="row"><button data-target="research_example" onclick="copyText('research_example')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Research Deep · Prompt Template</h3>
    <div class="meta">
      來源 skill：`research-deep`<br>
      來源檔案：[research-deep/SKILL.md](/Users/xjp/.codex/skills/research-deep/SKILL.md)<br>
      提取方式：literal template<br>
      適用性：`Direct prompt`<br>
      是否適合直接貼進 ChatGPT Pro：有條件適合；需先替換 `{item_related_info}`、`{fields_path}`、`{output_path}`
    </div>
    <textarea id="research_deep_template" readonly>## Task
Research {item_related_info}, output structured JSON to {output_path}

## Field Definitions
Read {fields_path} to get all field definitions

## Output Requirements
1. Output JSON according to fields defined in fields.yaml
2. Mark uncertain field values with [uncertain]
3. Add uncertain array at the end of JSON, listing all uncertain field names
4. All field values must be in English

## Output Path
{output_path}

## Validation
After completing JSON output, run validation script to ensure complete field coverage:
python $HOME/.codex/skills/research/validate_json.py -f {fields_path} -j {output_path}
Task is complete only after validation passes.</textarea>
    <div class="row"><button data-target="research_deep_template" onclick="copyText('research_deep_template')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Research Deep · One-shot Example</h3>
    <div class="meta">
      來源 skill：`research-deep`<br>
      來源檔案：[research-deep/SKILL.md](/Users/xjp/.codex/skills/research-deep/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Direct prompt`<br>
      是否適合直接貼進 ChatGPT Pro：可直接當範例改寫；原始項目是 `GitHub Copilot`
    </div>
    <textarea id="research_deep_example" readonly>## Task
Research name: GitHub Copilot
category: International Product
description: Developed by Microsoft/GitHub, first mainstream AI coding assistant, ~40% market share, output structured JSON to /home/weizhena/AIcoding/aicoding-history/results/GitHub_Copilot.json

## Field Definitions
Read /home/weizhena/AIcoding/aicoding-history/fields.yaml to get all field definitions

## Output Requirements
1. Output JSON according to fields defined in fields.yaml
2. Mark uncertain field values with [uncertain]
3. Add uncertain array at the end of JSON, listing all uncertain field names
4. All field values must be in English

## Output Path
/home/weizhena/AIcoding/aicoding-history/results/GitHub_Copilot.json

## Validation
After completing JSON output, run validation script to ensure complete field coverage:
python $HOME/.codex/skills/research/validate_json.py -f /home/weizhena/AIcoding/aicoding-history/fields.yaml -j /home/weizhena/AIcoding/aicoding-history/results/GitHub_Copilot.json
Task is complete only after validation passes.</textarea>
    <div class="row"><button data-target="research_deep_example" onclick="copyText('research_deep_example')">Copy</button></div>
  </div>
</div>

## 2. 可直接複製的 Question Stems / Ideation Scaffolds

這一區只整理 `scientific-brainstorming` 已經明示的問題句、提示句、與對話支架，不把它們重寫成新的 sequential pipeline。

<div class="grid">
  <div class="card">
    <h3>Scientific Brainstorming · Context Questions</h3>
    <div class="meta">
      來源 skill：`scientific-brainstorming`<br>
      來源檔案：[scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Question stems only`<br>
      是否適合直接貼進 ChatGPT Pro：適合；但它是一組開場問題，不是完整 workflow
    </div>
    <textarea id="sb_context_questions" readonly>"What aspect of your research are you most excited about right now?"
"What problem keeps you up at night?"
"What assumptions are you making that might be worth questioning?"
"Are there any unexpected findings that don't fit your current model?"</textarea>
    <div class="row"><button data-target="sb_context_questions" onclick="copyText('sb_context_questions')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Scientific Brainstorming · Divergent Stems</h3>
    <div class="meta">
      來源 skill：`scientific-brainstorming`<br>
      來源檔案：[scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Question stems only`<br>
      是否適合直接貼進 ChatGPT Pro：適合；但它是一組發散支架，不是完整 prompt
    </div>
    <textarea id="sb_divergent_stems" readonly>"How might concepts from [field X] apply to your problem?"
"What if the opposite were true?"
"What if you had unlimited resources/time/data?"
"What if you could measure anything?"
"What if you had to solve this with 1800s technology?"
"What becomes possible with CRISPR/AI/quantum computing/etc.?"
"What's the most radical approach imaginable?"</textarea>
    <div class="row"><button data-target="sb_divergent_stems" onclick="copyText('sb_divergent_stems')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Scientific Brainstorming · Connection Prompts</h3>
    <div class="meta">
      來源 skill：`scientific-brainstorming`<br>
      來源檔案：[scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Question stems only`<br>
      是否適合直接貼進 ChatGPT Pro：適合；但它只覆蓋 connection-making
    </div>
    <textarea id="sb_connection_prompts" readonly>"I notice several ideas involve [theme]—what if we combined them?"
"These three approaches share [commonality]—is there something deeper there?"
"What's the most unexpected connection you're seeing?"</textarea>
    <div class="row"><button data-target="sb_connection_prompts" onclick="copyText('sb_connection_prompts')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Scientific Brainstorming · Critical Questions</h3>
    <div class="meta">
      來源 skill：`scientific-brainstorming`<br>
      來源檔案：[scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Question stems only`<br>
      是否適合直接貼進 ChatGPT Pro：適合；但它只是 critique 問句，不是完整批判流程
    </div>
    <textarea id="sb_critical_questions" readonly>"What would it take to actually test this?"
"What's the first small experiment to run?"
"What existing data or tools could be leveraged?"
"Who else would need to be involved?"
"What's the biggest obstacle, and how might it be overcome?"</textarea>
    <div class="row"><button data-target="sb_critical_questions" onclick="copyText('sb_critical_questions')">Copy</button></div>
  </div>

  <div class="card">
    <h3>Scientific Brainstorming · When Ideas Are Too Safe</h3>
    <div class="meta">
      來源 skill：`scientific-brainstorming`<br>
      來源檔案：[scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md)<br>
      提取方式：literal excerpt<br>
      適用性：`Question stems only`<br>
      是否適合直接貼進 ChatGPT Pro：適合；但它是局部介入用的支架
    </div>
    <textarea id="sb_safe_ideas_prompts" readonly>"What's an idea so bold it makes you nervous?"
Play devil's advocate to the conservative approach
Ask about failed or abandoned approaches and why they might actually work
Propose intentionally provocative "what ifs"</textarea>
    <div class="row"><button data-target="sb_safe_ideas_prompts" onclick="copyText('sb_safe_ideas_prompts')">Copy</button></div>
  </div>
</div>

## 3. 方法與批判層的 Explicit Support Map

這一區只說明現有 skill 的明示支持範圍，不提供假的 copy 按鈕。

| 類型 | 來源 skill | 來源檔案 | 原文明示支持 | 適用性 |
|---|---|---|---|---|
| Method support | `scientific-brainstorming` | [scientific-brainstorming/SKILL.md](/Users/xjp/.codex/skills/scientific-brainstorming/SKILL.md) | 明示可用 `SCAMPER`、`Six Thinking Hats`、`Morphological analysis`、`TRIZ`、`Biomimicry` | `Method support only` |
| Method inventory | `scientific-brainstorming` | [brainstorming_methods.md](/Users/xjp/.codex/skills/scientific-brainstorming/references/brainstorming_methods.md) | 明示各方法的問題句、用法、科學應用與 `Selecting a Method` | `Method support only` |
| Critique support | `scientific-critical-thinking` | [scientific-critical-thinking/SKILL.md](/Users/xjp/.codex/skills/scientific-critical-thinking/SKILL.md) | 明示 methodology critique、bias review、statistical review checklist、evidence quality assessment | `Method support only` |
| Formal review support | `peer-review` | [peer-review/SKILL.md](/Users/xjp/.codex/skills/peer-review/SKILL.md) | 明示 stage-based manuscript review、initial assessment、methods/results/discussion checks | `Method support only` |
| Research breadth support | `research-lookup` | [research-lookup/SKILL.md](/Users/xjp/.codex/skills/research-lookup/SKILL.md) | 明示 current research lookup、literature verification、background research、citation sources | `Method support only` |
| Review workflow support | `literature-review` | [literature-review/SKILL.md](/Users/xjp/.codex/skills/literature-review/SKILL.md) | 明示 planning、scope、search strategy、gap identification、review workflow | `Method support only` |

## 4. 不能嚴格提取的部分

在「只用 skill 原文明示」規則下，以下內容不能合法整理成 copy-ready single prompt：

- 一份完整的 ChatGPT Pro condensed one-shot brainstorming prompt
- 一份完整的跨 skill sequential pipeline prompt
- `Automatic Survey Generation` 或 `OrionVault` 專用場景化 prompt
- 一份把 research、ideation、critique、packaging 串成單次交互的 literal prompt

原因不是能力不存在，而是現有 skill 原文沒有把這些東西寫成可直接複製的單一 prompt。

若要產出上述內容，必須切換到較寬鬆的規格：
- 允許最小拼接
- 允許把多個 skill 的 literal 區塊重新編排
- 但那會是另一份文檔，不是這一份 strict provenance 版本

</div>
