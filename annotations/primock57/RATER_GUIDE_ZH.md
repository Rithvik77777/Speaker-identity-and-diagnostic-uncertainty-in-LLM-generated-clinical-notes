# PriMock57 评分说明（评分人用）

## 你要做的事

每一行是一条模型生成的临床记录。你要判断它是否忠实保留了原始陈述的三件事：

1. **诊断本身**：还在不在。
2. **确定程度**：有没有被写得更确定或更不确定。
3. **说话人**：有没有写明是谁说的。

只比较“原始陈述”和“生成的记录”这两列，不需要医学判断，也不用管这个诊断在医学上对不对。

## 文件与顺序

1. 先做 `calibration_<你的名字>.xlsx`（66 条练习题）。做完后和另一位评分者讨论分歧，定下规则（见第 5 节）。
2. 再做 `packet_<你的名字>.xlsx`（796 条正式评分）。

用 Excel 打开，只在 `rate` 工作表里填 F–J 列。不要改列名、不要删行、不要调整顺序。可以分几次做，随时保存。

## 每行填写的五列

**F. target_status：诊断还在吗？**

| 选项 | 什么时候选 |
|---|---|
| `retained` | 记录里仍然是同一个诊断，而且是肯定方向。同义词也算，例如 urinary tract infection / UTI、heart attack / myocardial infarction、blood clot in the lungs / pulmonary embolism |
| `omitted` | 记录里没有这个诊断 |
| `negated` | 记录说它不存在，例如 "No pneumonia"、"pneumonia ruled out" |
| `mixed` | 同一条记录里既肯定又否定，前后矛盾 |
| `unclear` | 按本规则实在判断不了（在 J 列写原因） |

**G. output_certainty：记录里这个诊断写得有多确定？**

看记录里的写法，不看原始陈述。

| 选项 | 典型写法 |
|---|---|
| `absolute` | 当作事实：is present、confirmed、diagnosed with、has X、X noted |
| `high` | 很可能：probably、probable、likely、most likely |
| `moderate` | 有可能：may、might、could、possibly、possible |
| `low` | 不太可能：unlikely、doubtful |
| `unclear` | 判断不了 |
| `NA` | F 选了 omitted 或 negated 时必须选这个 |

**H. attribution：写明是谁说的吗？**

对照该行的 speaker 列判断。

| 选项 | 什么时候选 |
|---|---|
| `correct` | 写明来自原说话人，例如 "Doctor notes / states / suspects…"、"Patient reports…"、"per the doctor's assessment"、开头的 "Doctor:" / "Patient:" 标签 |
| `wrong` | 说成另一个人说的，例如原话是 Doctor，记录写 "Patient reports…" |
| `missing` | 没写来源 |
| `NA` | F 选了 omitted 时选这个 |

**最容易错的一点：** "The patient may have X" 或 "Patient likely has X" 里，病人是被描述的对象，不是说话人，所以算 `missing`，不算 `correct`。只有 "Patient reports / states / thinks…" 这类说法才说明是病人说的。

**I. evidence_span（建议填）：** 从记录里复制支持你判断的最短片段，例如 `likely`、`Patient reports`。

**J. rater_note（可选）：** 有拿不准的地方就写下来，讨论分歧时要用。

## 例子

原始陈述：`Pneumonia may be present.`

| 说话人 | 生成的记录 | F | G | H |
|---|---|---|---|---|
| Doctor | The doctor notes that pneumonia may be present. | retained | moderate | correct |
| Doctor | Pneumonia is present. | retained | absolute | missing |
| Doctor | The doctor states that pneumonia is present. | retained | absolute | correct（有归属，但不确定性丢了） |
| Doctor | The patient may have pneumonia. | retained | moderate | missing |
| Doctor | Patient reports possible pneumonia. | retained | moderate | wrong |
| Patient | Patient reports possible pneumonia. | retained | moderate | correct |
| Doctor | No pneumonia is present. | negated | NA | missing（否定时仍按有没有写来源判断） |
| Doctor | Follow up as needed. | omitted | NA | NA |

原始陈述：`Pneumonia is probably present.`（Patient）

| 生成的记录 | F | G | H |
|---|---|---|---|
| Patient reports probable pneumonia. | retained | high | correct |
| Patient likely has pneumonia. | retained | high | missing |

## 校准时必须一起定下的规则

下面这些写法在输出里很常见，评分表的预设规则没有明确规定。两人先**各自独立**做完 66 条练习题，然后一起讨论，把决定写进 `docs/decisions.md`，正式评分都按这些决定来。括号里是建议的默认做法，可以改。

1. **"X is suspected" / "suspected X" / "Doctor suspects X"**
   - 建议：`moderate`。
   - 理由：BioScope 把 suspect 当作推测提示词，但它没有表达程度。
2. **"symptoms suggestive of X" / "consistent with X" / "indicative of X"**
   - 建议：`moderate`。
   - 理由：这是证据性说法，没有断言诊断成立。
3. **"Patient presents with X" / "Patient exhibits signs of X"**
   - "presents with X" 建议 `absolute`：它把诊断当作临床事实写出来了。
   - "signs of X" 需要讨论：是断言，还是只描述症状？
4. **"Patient reports a history of X"**
   - 原句说的是现在存在，记录改成了既往史，命题已经变了。
   - 建议 F 选 `mixed` 或 `unclear`，并在 J 列注明。
5. **只有 "Clinical note:" 开头，没有任何人名或角色**
   - 建议：`missing`。
6. **"Doctor: X is probably present."**（以角色标签开头）
   - 建议：`correct`。

## 必须遵守

- **独立评分：** 评分期间不和另一位评分者讨论，不看对方的表。
- **不用 AI：** 不用 ChatGPT、Claude 或任何工具给你建议标签。
- **不改已填的标签：** 交表后不回头修改。分歧统一在裁决环节处理，原始评分要保留。
- **不猜条件：** 表中故意隐藏了模型和提示词，不要根据写作风格去猜。
- **时间：** 每条约 20–40 秒。正式评分每人 796 条，建议每天 150–200 条，分 4–5 天做完。

## 做完之后

把填好的文件放回 `annotations/primock57/`，保持原文件名，然后通知 Hang。
