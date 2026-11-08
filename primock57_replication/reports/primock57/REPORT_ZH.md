# PriMock57 复现实验：工作报告（2026-10-28）

**重要提示：** 下文所有实验指标都来自词汇规则的**自动预筛（auto_lexical_v1）**，属于**暂定结果**，不能当作论文结论。正式指标必须来自两人独立的人工评分，评分尚未开始。

## 1. 已完成的工作

| 步骤 | 结果 | 文件 |
|---|---|---|
| 数据 | `sdialog/Primock-57`，固定 revision `4bb215f6`；57 个会诊、7,108 个话轮；该版本只有对话，没有 notes | `data/raw/primock57/` |
| 语料描述 | 话轮、token、转写标记统计；医生/病人的不确定性表达频率，按会诊做聚类 bootstrap | `tables/primock57/corpus_overview.csv`、`cue_by_speaker.csv`、`figures/primock57/cue_by_speaker.pdf` |
| 测试项构建 | 57 个会诊逐个筛查，得到 22 个合格基础命题（2 个 dev、20 个 eval，其中 10 个做确定性对照），共 152 条输入 | `data/primock57_candidates.csv`、`data/derived/primock57/{screening_log.csv,base_items.csv,items.jsonl}` |
| 环境检查 | 三个模型的 smoke 测试都通过：模板正确、没有默认系统提示、没有 `<think>` | `outputs/env_checks/` |
| 生成 | 3 个模型 × 304 条 = **912 条，全部成功**；没有截断；同一环境、同一 commit | `outputs/raw/primock57/` |
| 复现检查 | 同一环境重跑 72 条 DEV，**72/72 逐字一致** | `tables/primock57/repro_dev_same_env.txt` |
| 暂定分析 | 用自动预筛标签跑完 E1–E4 全部表格和图 | `tables/primock57/auto_*.csv`、`figures/primock57/auto_*.pdf` |
| 评分包 | 840 条输出去重后为 796 个评分单元；两人各一份 xlsx，带下拉菜单，顺序各自随机，隐藏模型和提示词 | `annotations/primock57/packet_hang.xlsx`、`packet_rater_b.xlsx` |
| 合并与重算 | 一致率（原始一致率、Cohen's κ、Krippendorff α）→ 分歧表 → 裁决 → 人工标签 → 重算全部表格；整个流程已用 synthetic 数据测试通过 | `src/annotation/merge.py` |
| 论文段落（英文） | 数据、语料分析、测试项构建、评分、结果、局限 | `paper/primock57_sections.md` |

## 2. 暂定发现（待人工评分确认）

1. **不确定陈述很少被写成确定事实。** P0 下的 CHR：Qwen 0.8%、Granite 1.7%、Phi 7.5%；P1 下分别降到 0%、0%、0.8%。被“写实”的输出多数是 "Patient presents with X" 或 "exhibits signs of X" 这类说法，需要人工判断它们算不算断言。
2. **身份标签对确定性的影响很小。** 三个模型中病人减医生的 CHR 差都在 ±5 个百分点以内，区间都碰到 0。以 20 个 base 的样本量，无法排除小效应。
3. **最明显的身份效应在归属上。** Granite 在 P0 下给 61.7% 的病人陈述加了 "Patient reports…"，医生陈述却 0% 注明来源（差 +61.7 [48.3, 75.0]）；P1 下差距仍有 +63.3。医生的推测变成了 note 本身的口吻，病人的推测则被标为病人的报告。
4. **程度信息被压平。** Qwen 在 P0 下几乎把 may、possibly、probably 全部写成 "X is suspected"，"probably" 与 "may" 之间的区别消失了；P1 下 120/120 条保留了原来的确定性等级。
5. **P1 主要改善了归属。** 正确归属率提高：Qwen +98.3 个百分点、Granite +37.5、Phi +39.2。Phi 在 P1 下常写 "Patient likely has X"（60 条中 28 条）：不确定性保留了，但病人成了被描述的对象而不是说话人，说法来源丢失。
6. **确定性对照：** Phi 在 P1 下把 3/10 条病人确定陈述写成了 "suspected"，医生标签的对照为 0/10。这可能是保护性提示词引起的、针对病人的过度弱化，样本很小，需要人工确认。
7. **语料层面：** 真实会诊里病人用不确定性表达的频率不低于医生（maybe、I think、probably、not sure 都是病人更多）。但模板中的 "possibly" 在整个语料里只出现了 4 次。

## 3. 与协议 v4 的偏差（需写入 `docs/decisions.md`）

1. **只有 22 个合格 base，不是 23 个。** 按协议报告缺口、保留 20 个 eval，dev 减为 2 个（每个模型 24 条 DEV，而不是 36 条）。
2. **base 由 Claude 筛选**，协议要求的两人人工审核还没做（`base_items.csv` 的 `approved=pending_human_review`）。审核后如果有改动，重新构建并重跑即可：三个模型合计纯生成时间约 11 分钟。
3. **运行环境是 Mac MPS fp32**，不是 T4 fp16。同一模型内部的比较不受影响；与 ACI-Bench 主实验的跨数据集比较存在 dtype 差异。
4. **需要立刻告诉队友的 bug：** transformers 4.57 会把模型仓库里的采样默认值（Qwen 是 `do_sample=True, temperature=0.7`）合并回显式设置的贪心配置。如果 ACI-Bench 的运行器只是把 `GenerationConfig` 传给 `generate()`，Qwen 实际上是在随机采样。修复方法见 `src/providers/hf_local.py`：同时覆盖 `model.generation_config`。

## 4. 你接下来要做的

1. **评分：** 你和另一位评分者各打开自己的 xlsx 独立评分，第二份文件可以改名为对方的名字。每人 796 条，估计每条 20–40 秒，即每人 4.5–9 小时。规则见 xlsx 里的 `guide` 页。
   - 评分期间不要讨论，不要用 LLM 打标签。
   - 如果时间不够，按协议 §14 要在评分开始前决定缩减范围，例如先评 P0 和对照，并写入 decisions。不能看了结果再决定。
2. 两份都填完后运行：
   ```bash
   .venv/bin/python -m src.annotation.merge --raters hang <对方名字>
   ```
   讨论 `disagreements.csv`，填写 `*_final` 列，存为 `adjudicated.csv`，然后运行：
   ```bash
   .venv/bin/python -m src.annotation.merge --raters hang <对方名字> --adjudicated annotations/primock57/adjudicated.csv
   .venv/bin/python -m src.analysis.primock57_analysis --labels annotations/primock57/human_labels_eval.csv
   ```
3. 用人工结果替换论文段落中的 **[PROVISIONAL-AUTO]** 和 **[HUMAN: …]** 占位，并与 ACI-Bench 主实验逐模型对照。

---

## 5. 人工评分结果（2026-10-29 更新，取代第 2 节的暂定结果）

- **评分：** 两位评分人分别评完 796 个评分单元，12 条分歧（1.5%）已讨论裁决，得到 840 条输出的最终标签：`annotations/primock57/human_labels_eval.csv`。
- **信度：** 采用 60 条盲测核验的结果。用的是 B 最初交回的版本，后来修改过的版本不用于信度计算。B 与 A 的一致率：
  - certainty：96.7%，κ = 0.93
  - attribution：100%，κ = 1.00
  - target_status：100%（60 条全是 retained，κ 无定义）

  B 的正式表在和 A 对比后修订过，所以论文不把 796 条上的一致率当作独立信度，这一点已在方法部分说明。
- **主要结果**（全部为人工标签，95% 聚类 bootstrap 区间）：
  1. **诊断保留率 100%，过度确定很少。** P0 下 CHR：Qwen 0.8%、Granite 1.7%、Phi 4.2%；P1 下降到 0%、0%、0.8%。
  2. **E1 确定性：** 身份标签对确定性没有可检测的影响。病人减医生的 CHR 差为 +1.7、+3.3、−1.7，区间都包含 0。
  3. **E1 归属：** Granite 在 P0 下给 61.7% 的病人陈述注明了来源，医生陈述为 0%（差 +61.7 [48.3, 75.0]）。P1 下差距仍有 +63.3。
  4. **E2：** Qwen 在 P0 下把 114/120 条写成 "suspected"，确定性等级的精确保留率只有 67.5%。P1 下 120 条全部保留了原等级。
  5. **E3：** P1 主要改善了归属，正确归属率提高：Qwen +98.3、Phi +44.2、Granite +37.5 个百分点。
  6. **E4：** Phi 在 P1 下弱化了 3/10 条病人确定陈述，医生陈述为 0/10。样本太小，只能作描述。
  7. **人工 vs 自动规则：** 两者整体一致率约 99%，但自动规则的错误是系统性的，集中在以下几类说法上：
     - "suspected"（188 条，自动规则判不出等级）；
     - "signs of"（5 条，被误判为 absolute）；
     - "as suggested by the doctor"（6 条，漏判归属）；
     - "history of"（3 条，没识别出时间变化）。
- **论文段落：** `paper/primock57_sections.md` 已全部换成人工结果。只剩一处 **[ACI-BENCH]** 占位，等 ACI-Bench 主实验的结果出来后，逐模型做对照。
