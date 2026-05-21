# PDF-Derived Brainstorming Deep Research Prompt Pipelines

> 來源：[`docs/skills/brainstorming_deep_research_report.pdf`](/Users/xjp/Desktop/Outline_COT/docs/skills/brainstorming_deep_research_report.pdf)
>
> 整理原則：
> 1. 本檔中的 prompt 內容只整理自 PDF 附錄 A 與附錄 B。
> 2. 不使用 `research-ideation` 或其他現有 skill 來改寫 prompt。
> 3. 我新增的只有版面、按鍵、標題與導覽，沒有新增 prompt 內容。
> 4. 本檔是 `PDF-derived`，不是 `current-skill-derived`。
>
> 覆核補充：
> 1. `prompt 文字來源` 與 `現有 skill 是否支撐相同流程` 是兩件不同的事。
> 2. 下方 prompt 文字仍然只來自 PDF。
> 3. 但我已先對照現有 skill，確認這些 pipeline 大部分不是憑空寫的，而是能對應到真實存在的 skill 能力。
> 4. 這種對照只代表「workflow 有對應 skill 支撐」，不代表「prompt 原文逐字來自那些 skill」。

| Pipeline 區段 | Prompt 文字來源 | 已覆核的現有 skill 對應 | 覆核結論 |
|---|---|---|---|
| A1-A3 研究與研究計畫 | PDF | `research`、`research-deep`、`research-lookup`、`literature-review` | 有明確對應能力 |
| A4-A5 結構化發想與高新穎度回合 | PDF | `scientific-brainstorming` 及其 `brainstorming_methods.md` | 有明確對應能力 |
| A6 hostile critique | PDF | `scientific-critical-thinking`、`peer-review` | 有明確對應能力 |
| A7 packaging | PDF | `skill-creator`、`writing-skills` | 有部分對應能力 |
| A8 Automatic Survey Generation 專用轉譯 | PDF | 無明確同名現有 skill | 視為 PDF 場景化延伸 |
| B1 condensed one-shot | PDF | 無單一同名 skill；是 PDF 對前述流程的濃縮 | 視為 PDF 壓縮版，不是現有 skill 原文 |

> PDF 原文對 human in the loop 的建議：
> 「以下 prompts 以『可直接複製貼上』為目標設計。它們不是一次全部丟，而是依序執行。這樣做的理由是讓每一段都能被審查、修改與重跑。」
>
> PDF 原文對單一 prompt 的判斷：
> 「若你暫時不想跑整套 pipeline，可以用下面這個濃縮版。但要知道，濃縮版在新穎度與可控性上通常不如分段版。」

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
.prompt-wrap button.violet { background:#faf5ff; color:#6d28d9; border-color:#ddd6fe; }
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
這份檔案把 PDF 中的兩種 pipeline 放在同一份 Markdown：
<br>
1. 附錄 A：分段 sequential pipeline
<br>
2. 附錄 B：單次 condensed pipeline
</div>

<div class="note success">
就 PDF 本身的建議而言：
<br>
- 如果你是 human in the loop，而且會審查、修改、重跑，每段分開是有必要的。
<br>
- 如果你是因為 ChatGPT Pro 想先用單一 prompt，也可以，但 PDF 明確認為它比較不如分段版。
</div>

<div class="toolbar">
  <button id="copyAllStagedBtn" onclick="copyMany(['a1','a2','a3','a4','a5','a6','a7','a8'], 'copyAllStagedBtn', 'Copy All Staged Prompts')">Copy All Staged Prompts</button>
  <button id="copyCoreStagedBtn" class="green" onclick="copyMany(['a1','a2','a3','a4','a5','a6'], 'copyCoreStagedBtn', 'Copy Core Human-in-the-Loop Prompts')">Copy Core Human-in-the-Loop Prompts</button>
  <button id="copyCondensedBtn" class="violet" data-target="b1" onclick="copyText('b1')">Copy Single Condensed Prompt</button>
</div>

<div class="grid">
  <div class="card">
    <h3>A1 Project instructions</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a1" readonly>本專案的目標不是做教科書式摘要，而是從研究與產品生態中萃取可執行的新方向。
固定工作流如下。
1. 先做 landscape mapping。
2. 再抽 tensions、contradictions、blind spots、failure modes。
3. 再做 structured ideation。
4. 再做 hostile critique。
5. 最後只保留可驗證且值得投入的方向。

每次輸出都必須明確區分：
A. evidence-backed
B. inferred
C. speculative

優先尋找：
A. 可從相鄰領域遷移的機制
B. 彼此矛盾的結論或假設
C. 評測與資料盲點
D. 反覆出現但尚未被清楚命名的模式
E. 需要新 workflow 才能解的瓶頸，而不是單純微調參數就能解的問題</textarea>
    <div class="row"><button data-target="a1" onclick="copyText('a1')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A2 Deep Research：先要計畫，不要立刻開跑</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a2" readonly>/Deepresearch

主題：&lt;&lt;topic&gt;&gt;
目標：不是寫 overview，而是找出能形成新方向的 idea seeds。

請先提出 research plan，不要立刻執行。
計畫必須包含：
1. 核心子領域。
2. 相鄰領域與可遷移領域。
3. 必查項目：contradictions、failure modes、evaluation blind spots、data blind spots、deployment constraints。
4. 來源分層：papers、official docs、products、blogs、benchmarks。
5. 判定「新發想」的標準。
6. 最終輸出 schema：field map、tensions、underexplored combinations、idea seeds、falsification checks。</textarea>
    <div class="row"><button data-target="a2" onclick="copyText('a2')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A3 Deep Research：正式執行</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a3" readonly>依照剛才的計畫執行 deep research。

要求：
1. 先 breadth-first，再 narrow down。
2. 不要一開始就鎖死單一子題。
3. 每個重要 claim 都要能回到來源。
4. 對每個候選方向都區分：
A. 已有共識
B. 有證據但尚未被整合命名
C. 高潛力但推測性強

最後請輸出：
A. field map
B. tensions / contradictions
C. underexplored combinations
D. 10 至 15 個 idea seeds
E. 每個 seed 的 supporting evidence 與 biggest risk</textarea>
    <div class="row"><button data-target="a3" onclick="copyText('a3')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A4 把 research 結果轉成 ideas</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a4" readonly>不要再做摘要。請把目前研究結果轉成發想。

請做三輪：
第一輪：SCAMPER
第二輪：Morphological Analysis
第三輪：Cross-domain transfer

要求：
1. Morphological Analysis 至少選 5 個維度，例如：
problem unit、data source、model family、evaluation regime、deployment constraint
2. Cross-domain transfer 至少從 3 個相鄰領域各借 2 個機制
3. 總共輸出 20 個 idea seeds

每個 idea seed 固定 5 行：
1. 核心概念
2. 它重組了哪些既有元素
3. 為何現在可能可行
4. 最小驗證
5. 最大風險</textarea>
    <div class="row"><button data-target="a4" onclick="copyText('a4')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A5 高新穎度回合</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a5" readonly>現在切到高新穎度模式。

請用 TRIZ + Lateral Thinking + Worst Possible Idea 重新生成一次候選方向，但只保留真的跳脫既有框架的 ideas。

步驟：
1. 先列出這個領域最常見的 5 個隱含假設。
2. 對每個假設做反轉、替換、移位或矛盾化。
3. 產生 10 個高風險高新穎度方向。
4. 每個方向都標記：
A. 它違反了哪個既有假設
B. 它可能解決什麼新問題
C. 它最可能在哪裡失敗</textarea>
    <div class="row"><button data-target="a5" onclick="copyText('a5')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A6 刪掉假創新</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a6" readonly>現在扮演 hostile reviewer + pragmatic PI。

對前面所有 ideas 做四維評估：
A. novelty
B. plausibility
C. evidence support
D. execution cost

請刪掉以下類型：
1. 只是改名
2. 只是參數微調
3. 只是把舊方法搬到新 domain 但沒有新 interaction
4. 只是把多個模組拼在一起但沒有新假設或新 evaluation value

最後只留下 3 至 5 個方向，並為每個方向輸出：
1. 為什麼值得做
2. 30 天內的最小驗證
3. 需要的資料、工具、協作者
4. 最可能失敗的原因
5. 失敗後的 pivot 路徑</textarea>
    <div class="row"><button data-target="a6" onclick="copyText('a6')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A7 把成功流程封裝回去</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a7" readonly>把本次最有效的工作流整理成兩種版本：
1. 給人看的 research brief
2. 給 agent 跑的 workflow brief

workflow brief 必須包含：
A. goal
B. inputs
C. step sequence
D. tool use policy
E. output schema
F. stop conditions
G. failure recovery
H. criteria for novelty vs triviality</textarea>
    <div class="row"><button data-target="a7" onclick="copyText('a7')">Copy</button></div>
  </div>

  <div class="card">
    <h3>A8 面向 Automatic Survey Generation 的專用轉譯</h3>
    <div class="meta">PDF 附錄 A 原文</div>
    <textarea id="a8" readonly>請把上面的 top ideas 改寫成面向 Automatic Survey Generation 的版本。
要求：
1. 每個方向要明確指出它對 survey pipeline 的哪一段有影響。
2. 每個方向至少提出一個可觀察的 research gap mining 訊號。
3. 每個方向要列出最適合納入 OrionVault 的持久化欄位。
4. 最後請輸出一張表：idea、evidence、gap signal、minimum validation、vault fields。</textarea>
    <div class="row"><button data-target="a8" onclick="copyText('a8')">Copy</button></div>
  </div>

  <div class="card">
    <h3>B1 濃縮版總 prompt</h3>
    <div class="meta">PDF 附錄 B 原文；適合 ChatGPT Pro 單次使用</div>
    <textarea id="b1" readonly>你現在不是一般聊天助手，而是一個 research-driven ideation engine。你的任務不是寫 overview，而是從多來源研究中找出具有新穎度、可驗證、可封裝為 agent workflow 的方向。

請依序完成：
1. 定義問題與成功標準。
2. 建立 field map，並列出主要子領域、代表方法、資料、benchmark 與部署情境。
3. 抽取 tensions、contradictions、failure modes、evaluation blind spots、data blind spots。
4. 用 SCAMPER、Morphological Analysis、TRIZ、Lateral Thinking、Worst Possible Idea 生成 ideas。
5. 刪除 trivial ideas，只保留真正值得驗證的 3 至 5 個方向。
6. 為每個方向提供：核心概念、支持證據、為何現在可行、30 天內最小驗證、最大風險、失敗後 pivot。
7. 最後把有效流程輸出成：
A. Project instructions
B. 一組 sequential prompts
C. `AGENTS.md` 摘要
D. `SKILL.md` 摘要

全程請明確區分 evidence-backed、inferred、speculative；並在需要時指出哪些內容只是推測。</textarea>
    <div class="row"><button data-target="b1" onclick="copyText('b1')">Copy</button></div>
  </div>
</div>

</div>
