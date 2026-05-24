# Metric Power Lookup Table

這份表用於快速估算：在 paired paper-level comparison 中，給定 N 篇 survey/review paper，兩個方法在某個 metric 上要差多少才值得談「顯著」或「有足夠 power」。

## 定義

- 對每篇 paper 計算 paired difference：`d_i = metric(A, i) - metric(B, i)`。
- `mean_diff = mean(d_i)`。
- `s_d = sd(d_i)`，也就是 paired differences 的 sample SD。不要用單一模型分數的 SD 代替。
- `d_z = mean_diff / s_d`，是 paired standardized effect。
- raw gap 與 standardized gap 的換算：`Delta_raw = d_z * s_d`。
- `Structural Distance` 是 lower-is-better；judge scores 是 higher-is-better。power 查表看絕對差距 `abs(Delta_raw)`，方向另外解讀。

## 公式

單一 planned paired comparison，雙尾 `alpha = 0.05`：

```text
Observed significance threshold:
  abs(d_z) >= t_(0.975, N-1) / sqrt(N)

80% power planning threshold, small-sample t-adjusted approximation:
  abs(d_z)_min ~= (t_(0.975, N-1) + z_0.80) / sqrt(N)

90% power planning threshold, small-sample t-adjusted approximation:
  abs(d_z)_min ~= (t_(0.975, N-1) + z_0.90) / sqrt(N)

Large-N approximation used in the main report:
  abs(d_z)_min ~= (z_0.975 + z_power) / sqrt(N)
  z_0.975 = 1.9600
  z_0.80  = 0.8416
  z_0.90  = 1.2816

Raw metric gap:
  abs(Delta_raw)_min = abs(d_z)_min * s_d

Large-N required N for a target raw gap:
  N ~= ((z_0.975 + z_power) * s_d / abs(Delta_raw))^2
```

## N=21/22 快速答案

| N papers | observed p<.05 only: min abs(d_z) | 80% power: min abs(d_z) | 90% power: min abs(d_z) |
|---:|---:|---:|---:|
| 21 | 0.455 | 0.639 | 0.735 |
| 22 | 0.443 | 0.623 | 0.717 |

解讀：如果 N 只有 21 或 22，我會把「有用」的門檻抓在 `abs(d_z) ~= 0.62-0.64` 以上。也就是 raw gap 至少約等於 `0.62-0.64 * s_d`。

## N=21/22 raw gap 範例

| paired SD `s_d` | N=21, 80% power raw gap | N=22, 80% power raw gap | 適用直覺 |
|---:|---:|---:|---|
| 0.05 | 0.032 | 0.031 | Structural Distance 這類 0-1 scale metric 的 paired SD 例子 |
| 0.10 | 0.064 | 0.062 | Structural Distance 這類 0-1 scale metric 的 paired SD 例子 |
| 0.50 | 0.319 | 0.311 | LLM judge average / dimension score 的 paired SD 例子 |
| 1.00 | 0.639 | 0.623 | LLM judge average / dimension score 的 paired SD 例子 |
| 1.50 | 0.958 | 0.934 | LLM judge average / dimension score 的 paired SD 例子 |

## Compact lookup

| N papers | observed p<.05 only abs(d_z) | 80% power abs(d_z), t-adjusted | 90% power abs(d_z), t-adjusted | 80% power abs(d_z), large-N z |
|---:|---:|---:|---:|---:|
| 4 | 1.579 | 2.000 | 2.220 | 1.401 |
| 10 | 0.715 | 0.981 | 1.121 | 0.886 |
| 15 | 0.554 | 0.771 | 0.885 | 0.723 |
| 20 | 0.468 | 0.656 | 0.755 | 0.626 |
| 21 | 0.455 | 0.639 | 0.735 | 0.611 |
| 22 | 0.443 | 0.623 | 0.717 | 0.597 |
| 25 | 0.413 | 0.581 | 0.669 | 0.560 |
| 30 | 0.373 | 0.527 | 0.607 | 0.511 |
| 32 | 0.361 | 0.509 | 0.587 | 0.495 |
| 40 | 0.320 | 0.453 | 0.522 | 0.443 |
| 50 | 0.284 | 0.403 | 0.465 | 0.396 |
| 75 | 0.230 | 0.327 | 0.378 | 0.323 |
| 100 | 0.198 | 0.283 | 0.327 | 0.280 |
| 150 | 0.161 | 0.230 | 0.266 | 0.229 |
| 200 | 0.139 | 0.199 | 0.230 | 0.198 |

完整 N=4..200 查表見同資料夾的 `power_lookup_by_N.csv`。

## 使用規則

- 若只是描述現有結果是否 p<.05，看 `observed p<.05 only`。
- 若要說實驗設計「夠力」或結果有穩定意義，優先看 `80% power`；重要結論可看 `90% power`。
- 若同時測多個 metric 或多個 judge dimension，這張表是單一 planned comparison 的門檻；Holm/FDR/Bonferroni 會提高實際需要的差距。
- N 很小時 permutation/bootstrap sensitivity 應該一起報；這張表不替代 paired differences 的分布檢查。
