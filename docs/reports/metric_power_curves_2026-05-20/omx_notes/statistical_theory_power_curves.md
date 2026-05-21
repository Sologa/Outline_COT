**Repo Alignment**
Evidence:
- 目前 blind-eval 主路徑直接產出 `Structural Distance`，並保存 6 個 judge 維度分數；judge message 也是從這 6 維 prompt 建出來的，[scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:36) [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py:574)。
- 本地 `LLM-as-a-Judge` 是 upstream repo-defined `6D judge`，每維是 `0-10` 且允許 `0.5`，不是 paper wording 常被口語化理解的 5D 版，[prompts/meow_llm_judge_6d_source_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/meow_llm_judge_6d_source_user.txt:44) [docs/guides/meow_evaluation_assets.md](/Users/xjp/Desktop/Outline_COT/docs/guides/meow_evaluation_assets.md:62)。
- `Reference reward` / `pair rewards` 在 repo 文件裡被明確標成 auxiliary，不應放進主要 detectable-difference 曲線，除非之後明確啟用 section-ref family，[docs/guides/meow_evaluation_assets.md](/Users/xjp/Desktop/Outline_COT/docs/guides/meow_evaluation_assets.md:53)。
- 相鄰 benchmark 已有 agreement / similarity surfaces：`raw_agreement`、`Cohen's kappa`、`Krippendorff alpha nominal`、shape distance、title/lexical/role similarity，[scripts/benchmark100_manual_outline_audit.py](/Users/xjp/Desktop/Outline_COT/scripts/benchmark100_manual_outline_audit.py:534) [scripts/benchmark100_agent_outline_protocol_v1.py](/Users/xjp/Desktop/Outline_COT/scripts/benchmark100_agent_outline_protocol_v1.py:872) [scripts/benchmark100_sr_survey_shape_test.py](/Users/xjp/Desktop/Outline_COT/scripts/benchmark100_sr_survey_shape_test.py:56) [scripts/benchmark100_review_outline_homogeneity.py](/Users/xjp/Desktop/Outline_COT/scripts/benchmark100_review_outline_homogeneity.py:137)。

Inference:
- 主報告的 primary curves 應以 `Structural Distance` 與 `judge average` 為核心。
- 6 個 judge dimensions 適合做 secondary ordinal sensitivity。
- `ref_reward`、agreement、similarity、correlation 類應列為 future / adjacent families，不進 primary family 除非評估 inventory 之後改動。

**Statistical Theory Section**
令每篇 paper 都同時被兩個 system / condition 評分。對任一 metric，先把方向統一成「越大越好」的 paired improvement：
- higher-is-better metric：\(D_i=M_{i,A}-M_{i,B}\)
- lower-is-better metric（如 Structural Distance）：\(D_i=M_{i,B}-M_{i,A}\)

因此 \(D_i>0\) 一律代表 A 優於 B。主要 estimand 是 paired mean improvement \(\Delta=\mathbb E[D_i]\)；輔助報告 paired median shift 與 standardized effect \(d_z=\Delta/\sigma_D\)，其中 \(\sigma_D^2=\mathrm{Var}(D_i)\)。

對 paired continuous / bounded-continuous outcomes，主分析可用 paired t 的 power model，並以 permutation / bootstrap 做 small-\(N\) robustness。精確 paired-t power 可寫成
\[
T=\frac{\bar D}{s_D/\sqrt N},\quad \nu=N-1,\quad \lambda=\sqrt N\,d_z,
\]
\[
\text{Power}=P\!\left(|T_{\nu,\lambda}|>t_{1-\alpha/2,\nu}\right).
\]
報告中的 closed-form curve 建議用常見近似：
\[
\Delta_{\min}(N)\approx \frac{(z_{1-\alpha/2}+z_{1-\beta})\sigma_D}{\sqrt N},
\]
\[
d_{z,\min}(N)\approx \frac{z_{1-\alpha/2}+z_{1-\beta}}{\sqrt N},
\]
\[
N_{\min}(\Delta)\approx \left(\frac{(z_{1-\alpha/2}+z_{1-\beta})\sigma_D}{|\Delta|}\right)^2
= \left(\frac{z_{1-\alpha/2}+z_{1-\beta}}{|d_z|}\right)^2.
\]
在本報告設定下，\(\alpha=0.05\) two-sided，所以 \(z_{1-\alpha/2}=1.96\)。power \(=0.8\) 時常數是 \(1.96+0.842=2.802\)；power \(=0.9\) 時常數是 \(1.96+1.282=3.242\)。因此 standardized detectable-difference curve 可直接寫成
\[
d_{z,\min}(N)\approx \frac{2.802}{\sqrt N}\quad(\text{80\% power}),
\qquad
d_{z,\min}(N)\approx \frac{3.242}{\sqrt N}\quad(\text{90\% power}).
\]

對應的標準化情境可直接畫成一組 \(N_{\min}(d_z)\) 曲線。建議至少畫：
- \(d_z\in\{0.20,0.35,0.50,0.80,1.20,1.60\}\)
- 其近似所需 \(N\) 在 80% power 下約為 \(\{197,65,32,13,6,4\}\)
- 在 90% power 下約為 \(\{263,86,43,17,8,5\}\)

`judge average` 可以近似 continuous，因為它是 6 個半分制維度的平均，粒度比單一維度更細；但單一 judge dimension 本身仍是 bounded ordinal outcome，應做 ordinal sensitivity。對這些單維分數，建議主報告只把 raw paired difference 當 effect size 呈現，推論則用 Wilcoxon signed-rank 或 exact sign / permutation；如果 ties 很多，sign test 比 signed-rank 更穩健。`judge average` 與 `Structural Distance` 才是最適合放進 primary paired continuous curves 的 endpoints。

\(N=4\) 幾乎不能支持強意義的 two-sided significance。理由有兩層：
- 若使用 exact paired sign / sign-flip randomization，只有 \(2^4=16\) 個 sign patterns，最小可達 two-sided \(p\) 值是 \(2/16=0.125\)，所以根本不可能達到 \(\alpha=0.05\)。
- 就算用 paired t，df \(=3\) 的 two-sided 5% critical value 約是 \(t_{0.975,3}=3.182\)，所以至少要 \(|\bar D|>1.59\,s_D\) 才可能顯著；這已經是極大的 observed standardized effect。連 optimistic normal approximation 也要求 \(d_{z,\min}(4)\approx1.40\) 才有 80% power、\(1.62\) 才有 90% power，而 exact small-\(N\) inference 只會更嚴格。

小樣本時，paired bootstrap / permutation 應視為主 robustness path，而不是附屬檢查。建議：
- \(N\le 20\)、bounded metric、ordinal metric、ties 多時，用 paper-level sign-flip permutation 求 \(p\) 值。
- 同時用 paired bootstrap 對 \(\Delta\)、median shift、\(d_z\) 建 CI。
- 若要直接畫 small-\(N\) detectable-difference curves，最穩妥的是從 pilot paired differences 的 empirical distribution 出發，用 Monte Carlo 求在不同 \(N,\Delta\) 下的 rejection rate，而不是只靠 Gaussian 閉式近似。

獨立 two-sample 公式只作次要參考。若每組各有 \(n\) 篇 paper、總共 \(2n\) 篇，equal-variance 近似為
\[
n_{\min,\text{per arm}}(\Delta)\approx 2\left(\frac{(z_{1-\alpha/2}+z_{1-\beta})\sigma}{|\Delta|}\right)^2
=2\left(\frac{z_{1-\alpha/2}+z_{1-\beta}}{|d|}\right)^2.
\]
本題不應把它當 primary design，因為 paired design 的目的正是利用同 paper 配對來縮小 \(\sigma_D\)。

建議的 raw-score 曲線情境如下。raw curves 都必須搭配一個 assumed 或 pilot-based \(\sigma_D\)，因為 \(d_z=\Delta/\sigma_D\)：
- `[0,1]` bounded metrics：畫 \(\Delta\in\{0.02,0.05,0.10,0.15\}\)，並做 \(\sigma_D\in\{0.10,0.15,0.20\}\) sensitivity。
- `[1,10]` 或本地實際 `0-10` judge-like metrics：畫 \(\Delta\in\{0.25,0.50,0.75,1.00\}\)。由於 prompt 允許 `0.5` 分，`0.5` 與 `1.0` 是最自然的 raw scenarios。
- distance metrics，尤其 `Structural Distance`：畫 \(\Delta\in\{0.03,0.05,0.08,0.12\}\)，方向定義成「baseline distance 減 candidate distance」，並做 \(\sigma_D\in\{0.08,0.12,0.18\}\) sensitivity。

**Recommendation Matrix**
| Metric family | Repo role | Paired estimand | Preferred test / curve |
| --- | --- | --- | --- |
| `Structural Distance`, `judge average` | Primary active | mean paired improvement \(\Delta\), \(d_z\) | Paired t for planning; sign-flip permutation + bootstrap for robustness; plot both raw \(\Delta\) and \(d_z\) curves |
| 6 個 ordinal judge dimensions | Active secondary | median / mean paired shift | Wilcoxon signed-rank; exact sign/permutation if ties heavy; raw half-point shift curves as sensitivity |
| Binary / pass-fail / win-loss | Future | discordance gap \(\delta=p_{10}-p_{01}\) | McNemar or exact sign; curve parameterized by \((\delta,q)\), \(q=p_{10}+p_{01}\) |
| Count-derived metrics | Future | mean count diff or log-rate ratio | Paired Poisson / NB if modelable; otherwise paired permutation on count differences |
| Precision / Recall / F1 / ratio metrics | Future or auxiliary | paper-wise raw diff, logit diff, or log ratio | Paired permutation / bootstrap; avoid naive normal theory on pooled ratios alone |
| Agreement / correlation metrics | Adjacent benchmark | \(\Delta \kappa\), \(\Delta \alpha\), \(\Delta \operatorname{atanh}(r)\) | Paired bootstrap preferred; Williams/Steiger only when dependent-correlation assumptions are satisfied |
| Composite / aggregate metrics | Optional | weighted signed standardized composite \(C_i=\sum_k w_k D_{ik}/s_{D,k}\) | Pre-specify weights and direction; one primary composite at \(\alpha=.05\), otherwise Holm-adjust across confirmatory endpoints |

對 multiple comparisons，最保守且最清楚的預設是：
- 若只有一個 confirmatory endpoint，就維持 \(\alpha=0.05\)。
- 若同時把 `Structural Distance` 與 `judge average` 視為 co-primary，將它們當成 2-endpoint family 用 Holm。
- 6 個 judge dimensions 作為 secondary family，報 Holm-adjusted \(p\) 值或 simultaneous bootstrap CIs。
- `ref_reward`、agreement、similarity、correlation 類暫不納入主要 family，除非後續 metric inventory 明確升格。