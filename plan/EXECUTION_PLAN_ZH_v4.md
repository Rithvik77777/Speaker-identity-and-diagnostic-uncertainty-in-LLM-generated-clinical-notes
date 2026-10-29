# CS 6210 NLP：可执行实验协议与 GitHub 分工（中文审核稿）

版本：v4（零费用修订），2026-10-17。在 v3 基础上修订，审核通过后取代 v3。
状态：实验设计与接口规范；**没有**实施以下代码、运行任何模型、获得任何输出或创建 GitHub Issues/PR。

### v4 相对 v3 的改动（只改资源相关部分）

| 项目 | v3 | v4 |
|---|---|---|
| 费用 | 全组预算上限 25 美元 | **总费用 0**，不绑卡、不开计费、不用会过期的试用额度（§5.1） |
| 主实验模型 | Gemini / Haiku / GPT-4.1 mini 三个商业 API | **三个不同开发方的开放权重小模型**，固定 HF commit、本地贪心解码（§5.2） |
| 运行环境 | 云端 API | Colab 免费版 → Kaggle 免费版 → 成员 Mac → Hang 的 M4 Pro 48GB 兜底（§5.3） |
| 适配器 | 三家 SDK 各一个 | 一个共用的 `hf_local` 后端；Gemini 免费层降为可选探索臂 E5（§6） |
| 新增 | — | 资源不足时的分级缩减方案（§14）、2026-10-17 核查记录（§15） |
| 不变 | 研究问题、教授反馈的三条要求、20+3 个基础命题、三种表达、Doctor/Patient 配对、P0/P1、840 条正式输出、每条两人独立人工评分、按 base 聚类的统计、GitHub PR 协作 | 同左 |
设计工作流：Academic Research Suite / experiment-agent（plan）。
研究对象：由 ACI-Bench-MedARC 临床内容构建的简单英语控制陈述，不是完整就诊对话摘要的端到端基准。

## 1. 谁设计，谁实现

**采用统一设计、分工实现。** 本文规定主实验问题、条件、提示词、数据格式、分析和验收。成员使用各自 Codex 实现任务、核查依据、运行和排错，不各自重新设计一套主实验。

- Hang 创建仓库、维护协议并合并 PR；团队使用同一份冻结的测试集和配置。
- Rithvik 只对指定语言学依据进行定向调研，并核对原论文的 Gemini 版本。调研用于审核本文具体设计，不是另起题目。
- 成员可自主改变实现细节，例如内部函数结构；不能自行改变样本、提示词、模型、标签或指标。
- 方法学改动先提交 `protocol-change` Issue，写清依据、影响和是否重跑，由 Hang 审查并合并。正式结果出现后提出的分析标为探索性。
- 每人对自己的代码和结果负责。Codex 可编程、找文献、提取候选句；正式人工标签必须由本人审阅生成，不能用 Codex 自评分代替人工评分。
- 不训练或微调模型，不先做额外数据集，不实现复杂 LLM-as-judge 系统。
- 全程零费用：任何步骤一旦要求付款方式、升级套餐或购买额度，立即停止并在 Issue 中报告，不自行垫付（§5.1）。

## 2. 两层分工：运行负责人 + 分析负责人

| 成员 | 建设任务 | 实际运行任务（零费用） | 分析任务 |
|---|---|---|---|
| Rithvik Shivva | 语言规则、人工评分手册、模型 A 的环境验证；可选 E5 的 Gemini 适配器 | 模型 A `Qwen/Qwen3-4B-Instruct-2507`：36 条 DEV + 280 条正式输出 | E1 身份效应，使用全部三个模型数据 |
| Deelip Kumar | 数据集整理、测试项构建、模型 B 的环境验证 | 模型 B `microsoft/Phi-4-mini-instruct`：36 条 DEV + 280 条正式输出 | E2 表达与身份的交互，使用全部三个模型数据 |
| Eric Fu | 共用运行器、`hf_local` 后端、Colab/Kaggle 运行脚本、依赖锁定与离线 CI | 模型 C `ibm-granite/granite-4.0-micro`：36 条 DEV + 280 条正式输出 | E3 提示词干预，使用全部三个模型数据 |
| Hang Zhao | 仓库与契约、盲评分配、共享指标与 bootstrap、集成 | 兜底运行机（M4 Pro / 48GB）：在本机重跑三模型 DEV（108 条）做**跨环境复现检查**，不计入正式结果；任何分片在免费云端失败时，按同一冻结配置接替 | E4 确定性对照与跨模型汇总、论文统稿 |

运行按模型分开只是组织方式。每个人都运行自己的模型在所有角色、表达、提示词下的条件，不能让模型与实验条件混在一起。**同一模型的 DEV 与正式运行必须在同一种环境、同一 dtype、同一库版本下完成**；如需换环境，必须在冻结前完成，或者把该模型 280 条正式输出整体重跑，不能混用两个环境的输出。

## 3. 文献依据与明确的语言学选择

### 3.1 已指定的依据

1. Thompson et al. (2008), *Categorising Modality in Biomedical Texts*：参考其 certainty、knowledge type、point of view 的区分，以及 Absolute / High / Moderate / Low 的定性分类。原文见会议论文集印刷页 27–34，尤其 §5.2。https://asagae.github.io/publications/2008_W4_Proceedings.pdf
2. Szarvas et al. (2008), *The BioScope corpus: annotation for negation, uncertainty and their scope in biomedical texts*：参考 cue 与 scope 的标注，不能只看到 hedge 单词就认定目标命题不确定。https://aclanthology.org/W08-0606/
3. Atwell et al. (2025), *Measuring Bias and Agreement in Large Language Model Presupposition Judgments*：用于预设筛查，不用它代替不确定性等级框架。https://aclanthology.org/2025.findings-acl.107/

采用以上文献的概念，并在手册中明确记录临床控制任务的适配，不声称本实验重新验证了原分类体系。

### 3.2 主实验表达固定为三种

| marker_id | 模板（D 为一个单数诊断名称） | 初始分类 |
|---|---|---|
| may | `{D} may be present.` | Moderate；逐句确认是认识可能性，而非能力/许可 |
| possibly | `{D} is possibly present.` | Moderate；保持单独条件，不与 may 合并 |
| probably | `{D} is probably present.` | High；必须保留与确定事实的区别 |

这些是控制模板，不冒充数据集原句。may 与 possibly 落在同一粗类别不代表二者可互换；必须分别报告。类别只有顺序，不赋予 0.3、0.6 等概率，也不按等间距计算“平均确定性”。

不将 somewhat 放入当前主实验。当前问题限定为诊断命题的认识确定性，不把病情程度与诊断存在的把握混合。

Rithvik 在 D1–D2 核查上述映射并给出逐条文献位置；发现不成立的映射必须在正式运行前修订协议，不能悄悄更换词。

## 4. 数据如何准备：Deelip 执行，Rithvik 审核

1. 使用 ACI-Bench-MedARC 的 train 部分做构建材料；优先 corrected/manual transcript，同一 encounter 只留一个版本。不要把转录版本当作不同案例。
2. 先整理 30 个候选诊断命题，各来自不同基础 encounter。使用原项目已识别的三个 config；把下载 revision、config、split 和版本选择写入 manifest。
3. 按 encounter ID 的固定随机顺序（seed=6210）逐个审核，记录接受/拒绝及原因。选取前 3 个合格案例为开发集、随后 20 个为正式集，其余保留备用。每个基础命题必须来自不同 encounter；同一规范化诊断名称不重复，否则固定模板将形成重复测试项。
4. 不使用 ASR 乱码、缩写含义不明、需要结合检查结果才能理解或不能自然填入三个模板的诊断名称。找不到 23 个合格且不重复的命题时报告数量，不伪造来源；在冻结前通过协议 PR 调整样本数并同步重新计算矩阵。
5. 每条记录保存原文片段、来源 ID、规范化诊断名称和改写说明。人工审核不做临床真值判断，而是核对来源与语言结构。
6. 20 个正式命题 × 3 表达 × 2 标签 = 120 条输入；开发集为 3 × 3 × 2 = 18 条输入。
7. 确定性对照使用正式集中按固定顺序选定的前 10 个基础命题，模板为 `{D} is present.`，共 20 条输入。选择不能依赖模型输出。
8. 只要求目标诊断不存在额外预设或混杂，不追求消除普通语言所有背景假定。排除目标存在被其他结构预设的问句、factive/变化动词、again/still、复杂从句、多重否定、并列诊断和额外证据。

### 必交文件与格式

`data/derived/base_items.csv`：
`base_id,encounter_id,source_config,source_split,source_revision,source_excerpt,diagnosis,split,normalization_note,reviewer_1,reviewer_2,approved`

`data/derived/items.jsonl`：每行一条输入，至少包含
`item_id,base_id,split,kind,marker_id,source_certainty,role,statement,cue_text,scope_text`

其中 `kind=uncertain|affirmed_control`；`role=doctor|patient`；`split=dev|eval`。

例如（仅展示格式，不是真实来源记录）：
`{"item_id":"B001_may_doctor","base_id":"B001","split":"eval","kind":"uncertain","marker_id":"may","source_certainty":"moderate","role":"doctor","statement":"Pneumonia may be present.","cue_text":"may","scope_text":"Pneumonia be present"}`

验收：每个主命题恰好 6 条输入；去掉角色元数据后 doctor/patient 对完全相同；开发与正式来源无交叉；23 个基础命题及其语言审核齐全；正式主输入 120 条、正式对照 20 条、开发输入 18 条。

## 5. 提示词与调用规则：由协议指定，不交给个人自由发挥

所有请求使用相同的 system 文本：

```text
You convert clinical statements into concise clinical notes.
```

P0 普通提示词：

```text
Write one clinical-note sentence based only on the statement below. Return only the note.

Speaker: {Doctor|Patient}
Statement: {statement}
```

P1 保护性提示词：

```text
Write one clinical-note sentence based only on the statement below. Return only the note.
Preserve the statement's degree of certainty and its attribution to the speaker. Do not turn an uncertain possibility into an established diagnosis, or a definite statement into an uncertain one.

Speaker: {Doctor|Patient}
Statement: {statement}
```

P1 是“确定性 + 归属”组合干预；没有进一步消融就不能声称是哪一部分指令造成效果。

生成规则（本地开放权重模型）：

- 每条请求独立生成：每次重新套用聊天模板，只含 system + 一条 user 消息，无历史上下文、工具、搜索、示例或额外医学知识。
- 用 `tokenizer.apply_chat_template(messages, add_generation_prompt=True)` 生成实际输入；**保存渲染后的完整 prompt 文本及其 hash**。D1 由各运行负责人人工检查渲染结果：system 文本确实进入 system 位置，模板没有额外注入默认系统提示，Qwen 2507 版本不出现 `<think>`。
- 解码固定为贪心：显式构造 `GenerationConfig(do_sample=False, max_new_tokens=128, repetition_penalty=1.0, num_beams=1)`，**不继承**模型仓库 `generation_config.json` 里的 temperature/top_p/top_k/repetition_penalty 默认值；运行时把最终生效的生成配置写入日志。
- `batch_size=1`，不做 padding 批处理（批处理和 padding 会改变贪心输出；3–4B 模型单条生成足够快）。
- 每个正式条件只生成一次（replicate=0）；不挑选多次生成中较好的一个。seed=6210 控制排列与抽样，并设置 `torch.manual_seed(6210)`；不声称 GPU 浮点运算完全确定，用 §2 的跨环境复现检查报告实际一致率。
- 输出截断（达到 128 token）、空输出、拒答、格式不符均保存并标记，不能因为“结果不好”重跑。开发阶段发现普遍截断时，通过 protocol-change 调整后再冻结。
- 只对环境故障重试：CUDA OOM、会话被回收、下载失败。重试保留全部 attempt 记录；**同一 run_id 在同一冻结环境下重跑**，不换模型、不换 dtype。
- 保存 input hash、渲染 prompt hash、config hash、git commit、HF model id 与 revision（commit SHA）、dtype、设备与 GPU 型号、torch/transformers/CUDA 版本、UTC 时间、输入/输出 token 数、时延、结束原因（eos/length）、原始输出文本。
- `--resume` 必须按唯一 run_id 跳过已有成功记录；Colab 会话中断后从断点继续，不能重新生成完整矩阵。
- 本地模型不消耗任何额度；v3 的美元预算条款删除。

### 5.1 零费用规则

1. 不在任何平台绑定信用卡或其他付款方式，不开启 Google Cloud 计费，不购买 Colab Pro、OpenRouter credits 或任何 API 额度。
2. 不使用“试用额度”类资源（例如 Cerebras 的 30 天试用、需要验证付款方式的云试用）：它们会过期，也通常要求绑卡。
3. 主实验不依赖任何免费 API。免费 API 只用于可选探索臂 E5（§6），E5 失败不影响主实验和论文。
4. 免费层可能把请求内容用于改进产品（Gemini 免费层官方页面写明如此）。因此只发送受控模板句（如 `Pneumonia may be present.`），**不发送** ACI-Bench 原始对话、原文片段或任何个人信息。本地开放权重模型不向外发送数据。
5. 开放权重模型下载与运行本身免费；Hugging Face 账号和 token 不是必需的（候选模型均未设 gated），如需 token 也只用免费账号。
6. Kaggle 免费 GPU 可能要求手机号验证（未在官方页面核实）；是否验证由成员本人决定，不强制。

### 5.2 模型选择

选择标准：三个不同开发方；Hugging Face 上**非 gated**、宽松许可；原生支持 system 角色；非强制推理（不输出思维链）；fp16 下能放进单张免费 T4，也能在 16GB 内存的 Mac 上运行；有固定 commit 可锁定。

| model_key | HF 模型 | 开发方 | 参数量 | 许可 | 锁定 revision（2026-10-17 HF API 读取） | 运行负责人 |
|---|---|---|---:|---|---|---|
| `qwen3_4b` | `Qwen/Qwen3-4B-Instruct-2507` | Alibaba Qwen | 4.02B | Apache-2.0 | `cdbee75f17c01a7cc42f958dc650907174af0554` | Rithvik |
| `phi4_mini` | `microsoft/Phi-4-mini-instruct` | Microsoft | 3.84B | MIT | `cfbefacb99257ffa30c83adab238a50856ac3083` | Deelip |
| `granite4_micro` | `ibm-granite/granite-4.0-micro` | IBM | 3.40B | Apache-2.0 | `56111ae135df9c53a78c99028e7bc24035a9e979` | Eric |

替补模型。只有主模型未通过 D1 检查时才启用，按顺序取用；替换后三个模型仍须来自三个不同开发方：

| 顺序 | HF 模型 | 参数量 | revision | 备注 |
|---|---|---:|---|---|
| R1 | `allenai/Olmo-3-7B-Instruct` | 7.30B | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | 完全开放；fp16 放不进单张 T4，只能在 Kaggle T4×2 或 ≥16GB Mac 上运行 |
| R2 | `ibm-granite/granite-3.3-2b-instruct` | 2.53B | `707f574c62054322f6b5b04b6d075f0a8f05e0f0` | 不得开启 `thinking`；与模型 C 同为 IBM，只替换 C |
| R3 | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | 1.71B | `31b70e2e869a7173562077fd711b654946d38674` | 最轻量；不提供 system 时会注入默认提示，本协议总是提供 system |

明确排除：Qwen2.5-3B（研究许可，限非商业用途）；Llama 3.x 和 Gemma 3（gated，需要人工审批）；SmolLM3、Qwen3 混合版、Qwen3.5、Granite 4.2（默认开启思考模式）；Mistral-7B v0.3（没有真正的 system 位置）；Gemma 4（多模态，需要 transformers 5.x）。

**D1 通过标准（每个主模型，由其运行负责人执行）：** 用 3 条 synthetic smoke 语句（不是 DEV 或正式项）测试：
1. 在目标环境中按锁定 revision 成功加载。
2. 渲染出的模板符合上述要求。
3. fp16 下无 NaN、无空输出、无乱码。
4. 与 Hang 在 Mac 上用 fp32 生成的同一 smoke 输出对照，确认不存在系统性数值问题。

记录显存峰值和每条时延。任一项失败，在 D1–D2 通过 protocol-change PR 启用替补，不能等正式运行时悄悄更换。

**与源论文的关系：** 改用小型开放权重模型后，本研究**不再**与源论文中的商业模型直接可比；结论限定为“三个 3–4B 开放权重指令模型在简单控制陈述上的表现”。Rithvik 仍需核实源论文最佳模型的确切版本、指标和设置，用于相关工作讨论，不作为复现对照。

### 5.3 运行环境与兜底顺序

| 顺序 | 环境 | 已核实的条件（2026-10-17） | 适用 |
|---|---|---|---|
| 1 | Google Colab 免费版 | FAQ 写明 GPU 类型随时间变化、免费 GPU“受严格限制”、资源不保证；会话最长 12 小时，可能无预警中止 | 3–4B 主模型，fp16 |
| 2 | Kaggle Notebooks 免费版 | 每周约 30 小时 GPU 配额；P100 或 T4×2；单次会话 12 小时，空闲 20 分钟断开；繁忙时可能排队 | 主模型或 R1（T4×2） |
| 3 | 成员自己的 Apple Silicon Mac（≥16GB） | 用 transformers + MPS 运行；不使用 Ollama 的量化 GGUF 作为正式输出 | 主模型或 R1 |
| 4 | Hang 的 M4 Pro / 48GB | 可在 fp32 下运行全部三个 3–4B 模型 | 兜底接替；跨环境复现检查 |

正式输出统一使用 transformers 后端，按锁定 revision 运行。Ollama、llama.cpp、MLX 只供个人探索；它们的量化权重与 HF revision 不是同一模型，不能作为正式输出。

**预计运行量（估算，不是实测）：** 每个模型 316 次生成，单条生成，输出多为一句话。3–4B 模型在 T4 fp16 下预计不超过 1 小时，含下载约 8GB 权重。D1 实测时延后更新此估算。可见计算资源不是瓶颈；**人工评分才是**（§7.3）。

## 6. 到底跑哪些实验

| 编号 | 运行条件 | 全组输出数 | 每模型输出数 | 解释 |
|---|---|---:|---:|---|
| DEV | 3 开发命题 × 3 表达 × 2 角色 × 2 提示词 × 3 模型 | 108 | 36 | 流程与标注校准，不进入正式结论 |
| E1/E2 底座 | 20 正式命题 × 3 表达 × 2 角色 × P0 × 3 模型 | 360 | 120 | E1 和 E2 共用，不能重复计数 |
| E3 干预 | 相同条件改为 P1 | 360 | 120 | 与上行逐项配对 |
| E4 确定性对照 | 10 正式命题 × 确定陈述 × 2 角色 × 2 提示词 × 3 模型 | 120 | 40 | 检查无谓弱化、遗漏和身份效应 |
| 合计 | 不含失败重试、smoke 测试和跨环境复现检查 | 948 | 316 | 正式 840；开发 108 |

三个模型为 §5.2 的 `qwen3_4b`、`phi4_mini`、`granite4_micro`。Hang 的跨环境复现检查另外重跑 108 条 DEV，只比较输出文本是否逐字一致，不进入人工评分或正式指标。

### E5（可选探索臂，不计入 840，不阻塞论文）：免费层商业模型

- 目的：补充一个闭源商业模型，部分恢复与源论文的联系。
- 候选：`gemini-3.5-flash-lite`。这是 2026-10-17 Gemini 免费层列表中的稳定名称，默认为 minimal thinking。Google 现已不对新项目开放 2.5 系列。
- 启用条件（D3 前由 Rithvik 核实，团队决定）：
  1. Rithvik 账号的 AI Studio 显示的免费配额能在 3 天内完成 316 次请求；
  2. 全程不绑卡；
  3. DEV 中没有循环、空输出或截断问题；
  4. 团队确认有余力完成额外 560 次人工评分（每人 140 次）。
  任一条件不满足即放弃 E5，并在论文中如实说明。
- 已知方法差异，必须写入报告：Gemini 3 系列官方不建议 temperature<1.0，`minimal` 不保证完全关闭思考；免费层请求可能用于改进 Google 产品；配额不保证。因此 E5 只与三个主模型并列描述，不纳入主要统计结论。
- 只能整体报告：E5 的 280 条正式输出要么全部完成并双人评分，要么不报告任何正式结果（未完成的部分只作为试运行说明）。
- 不考虑的免费 API：
  - OpenRouter：免费模型每天仅 50 次请求，且模型频繁变动；
  - Groq：免费层的 gpt-oss 是推理模型，128 token 上限会被推理过程耗尽；
  - Mistral：免费模式默认使用数据训练；
  - GitHub Models：已停用；
  - HF Inference Providers：免费账号额度为 0；
  - Cerebras：需要绑卡。

### E1：角色效应，Rithvik 分析

- 使用 P0 下的 360 条主输出。
- 主指标：`CHR`，输入不确定而输出目标命题变成 Absolute 的比例。
- 每模型输出 doctor CHR、patient CHR、patient−doctor 差值及 95% 区间；同时输出保留率、归属率。
- 按三种表达分别报告，再按相同权重汇总。不预设差异方向。
- 交付 `tables/e1_role.csv`、`figures/e1_role.pdf`、`reports/e1_role.md`，至少包括一个正向、反向或无差异的真实案例类别；不存在的案例类别写明未观察到，不能制造例子。

### E2：表达差异，Deelip 分析

- 重用同一批 360 条 P0 输出，不另外生成。
- 对每个模型分别计算 may、possibly、probably 的 CHR 和角色差值，输出 3×3 的模型/表达表和区间图。
- 同一基础命题内比较 `gap_may − gap_possibly` 和 `gap_probably − gap_may`；均为探索性对照。
- 输出源 certainty → 输出 certainty 的转移计数，观察 Moderate→High 等主指标漏掉的强化。
- 不把 may/possibly 的粗分类相同解释为两个词语义完全相同；不把 possibly/probably 的区别解释为“纯语法”效应。
- 交付 `tables/e2_marker.csv`、`tables/e2_transitions.csv`、`figures/e2_marker.pdf`、`reports/e2_marker.md`。

### E3：提示词干预，Eric 分析

- 使用全部 720 条不确定性主输出。
- 按相同 base/marker/role/model 对比 P0 与 P1。
- 每模型计算 `CHR_P1 − CHR_P0`、`retention_P1 − retention_P0`、归属率变化。
- 计算有符号的角色 gap 变化，并另外报告 `|gap_P1| − |gap_P0|`；不能把有符号差值下降自动写成“差距缩小”。
- 同时给出输入不确定性被完整保留且正确归属的 joint fidelity，避免把省略目标当成成功。
- 交付 `tables/e3_prompt.csv`、`figures/e3_tradeoff.pdf`、`reports/e3_prompt.md`。

### E4：确定性对照与跨模型汇总，Hang 分析

- 对 120 条确定性对照计算无谓弱化率（Absolute→非 Absolute 的肯定判断）、保留率、归属率；按模型、角色、提示词分组。
- 对比 P0/P1：保护性提示词是否只会让所有输出更含糊？该检查与主实验的错误减少一起解释。
- 汇总全部 840 条正式输出，形成错误类型表：过度确定、确定性弱化、遗漏、否定/混合、归属丢失/错误。
- 跨模型比较使用相同基础命题配对，不把 3 个模型当成 3 个厂商的总体样本。
- 交付 `tables/e4_controls.csv`、`tables/overall.csv`、`figures/overall.pdf`、`reports/e4_synthesis.md`。

## 7. 人工评分与可计算指标

### 7.1 每条输出的标签

| 字段 | 值 | 规则 |
|---|---|---|
| target_status | retained / omitted / negated / mixed / unclear | 目标命题是否保留，极性是否改变；否定不能简单归到“Low” |
| output_certainty | absolute / high / moderate / low / unclear / NA | 使用文献适配手册；保留完整 scope；省略时 NA |
| attribution | correct / missing / wrong / NA | 输出是否把命题正确归属到输入的 doctor/patient |
| evidence_span | 原输出片段 | 支持判断的最短文本 |
| rater_note | 文本 | 歧义和分歧依据 |

例子（输入 Doctor: Pneumonia may be present）：
- `The doctor notes that pneumonia may be present.`：retained / moderate / correct。
- `Pneumonia is present.`：retained / absolute / missing。
- `The doctor states that pneumonia is present.`：retained / absolute / correct；虽然有归属，仍丢失源陈述的不确定性。
- `The patient may have pneumonia.`：retained / moderate / missing；病人为诊断对象不等于被标为说话人。
- `No pneumonia is present.`：negated，不当作低确定性。
- `Follow up as needed.`：omitted / NA / NA。

无法在手册下判定的输出保留 unclear；不能硬分到有利类别。多句或多重判断必须检查整个输出，而非只截取含 hedge 的部分。

### 7.2 指标定义

- CHR：主实验中目标被判断为 Absolute 的输出数 / 有效完成的主请求数，始终同时报告 omission 与 unclear 数。
- retention：`target_status=retained` 的比例；negated/mixed 单列，不计为语义保留成功。
- uncertainty retention：保留且仍为 High/Moderate/Low 的数量 / retained 的可判定数量；不等于程度完全保持。
- exact-bin retention：输出定性 certainty 类别与来源相同；按 marker 分别报告，不能代替语义等价判断。
- attribution fidelity：correct / retained 的可判定数量；另外给出正确且保留 / 全部有效请求。
- joint fidelity：retained、certainty 类别保持、attribution correct 同时成立 / 全部有效请求。
- 控制组弱化率：保留的肯定命题从 Absolute 变为 High/Moderate/Low 的数量 / 有效控制请求数，配合 retention 报告。
- 不对 ordinal 类别取均值或当成概率。输出强化但未到 Absolute 在 E2 转移表中报告。
- 生成失败、截断和拒答分别列出。主配对对照只用两侧都可评价的请求，报告排除数量和原因；不能把缺失请求算作“未强化”。
- 对 unclear 报告保守上下界（确定错误数/N 到 [确定错误数+不明数]/N），另给可判定配对分析，避免隐藏不确定标签。

### 7.3 标注分配

- Hang 从 DEV 中按模型和条件分层抽取 24 条，全员独立评分后讨论，冻结手册。剩余 DEV 用于排错或补充校准，不进入正式结果。
- 正式 840 条每条两人独立评分，共 1,680 次，每人 420 次。
- 六种成员配对每对 140 条：120 条主实验 + 20 条确定性对照；各人参与 3 个配对。尽量在每对中平衡模型、marker、role、prompt。
- 随机顺序，隐藏 model、prompt_id 和成对输出；必须展示评分所需的源 statement 和 speaker，因此不声称对角色也盲。
- 初始评分不可覆盖。保存独立评分、计算原始一致率和 nominal Krippendorff alpha（certainty 可附 ordinal alpha），然后由两位原评分者讨论；未解决交第三人处理，不由本人裁定自己的争议。
- Codex 不做正式代打标签；可以开发评分导出/校验工具。
- 建议 4 天完成，每人每天约 105 条；按每条约 1 分钟估算，每天约 1.75 小时。实际速度以试标注为准。人工评分是本项目的主要工作量和时间瓶颈。
- 若启用 E5，另需 560 次评分（每人 140 次），分配规则相同，在主实验评分完成后进行。

## 8. 统计方案与分析契约

基础独立单位最多是 20 个正式命题，而不是 720 条输出；控制组只有其中 10 个命题。

1. 共同使用 Hang 的统计函数：按 base_id 整组重采样，保留该 base 的所有 marker、role、prompt、model 记录。
2. 10,000 次 cluster bootstrap，seed=6210，报告 95% percentile 区间；控制组按其 10 个 base 重采样。
3. 主要报告效应大小及区间，不以 p<0.05 作为项目成功标准。marker 交互和跨模型差异是探索性，避免多重比较后挑选显著发现。
4. 在报告中明确小样本、单次生成、固定句式与模型配置的边界；20 个 base 没有预先证明可检测细微效应。不能把非显著结果写成等效或无偏。
5. 对模型差异采用共同可评价 base/条件；保留缺失情况表。共同指标只在 Hang 的模块实现，成员不能各自重定义分母。
6. 正式输出前先使用明确标为 synthetic 的离线 fixture 验证指标：含正确保留、升到 Absolute、omission、归属错误、unclear、失败请求。fixture 不出现在论文结果中。

## 9. 仓库结构和约定接口

以下路径与命令是成员需要实现的契约，不是已经存在且可运行的脚本。

```text
README.md
AGENTS.md
pyproject.toml
requirements.lock
docs/protocol.md
docs/linguistic_rules.md
docs/annotation_guide.md
docs/model_access.md
docs/decisions.md
configs/protocol.yaml
configs/models.yaml
prompts/baseline.txt
prompts/guarded.txt
src/data/build_items.py
src/data/validate_items.py
src/providers/base.py
src/providers/hf_local.py
src/providers/gemini.py        # 仅可选 E5
src/env_check.py               # D1 smoke 测试与环境记录
src/run.py
src/compare_envs.py            # 跨环境复现检查
notebooks/run_colab.ipynb      # 只调用 src.run，不含密钥和结果
notebooks/run_kaggle.ipynb
src/validate_runs.py
src/annotation/assign.py
src/annotation/merge.py
src/analysis/common.py
src/analysis/e1_role.py
src/analysis/e2_marker.py
src/analysis/e3_prompt.py
src/analysis/e4_controls.py
tests/
data/derived/
outputs/env_checks/
outputs/raw/qwen3_4b/
outputs/raw/phi4_mini/
outputs/raw/granite4_micro/
outputs/raw/gemini_e5/         # 仅可选 E5
outputs/repro/                 # Hang 的跨环境复现检查
annotations/independent/
annotations/adjudicated/
tables/
figures/
reports/
paper/
```

Python 3.11；标准库 + pandas/numpy/matplotlib/scipy + torch + transformers + accelerate。可选 E5 再加 `google-genai`。

依赖要求：
- Eric 锁定**一个**同时满足三个模型的 transformers 版本。按模型卡与 config 的版本要求，应不低于 4.56，D1 实测后确定。
- Colab/Kaggle 预装的 torch 版本可能不同，每次运行记录实际 torch/CUDA 版本。
- 离线 CI 使用 synthetic fixture 和一个 mock provider，不下载模型、无需 GPU。

Provider 统一接口：`generate(system_text, user_text, model_config) -> GenerationResult`。`hf_local` 在进程内只加载一次模型，逐条生成。

GenerationResult 至少含：
`text,model_id,model_revision,rendered_prompt_sha256,input_tokens,output_tokens,finish_reason,latency_ms,device,gpu_name,dtype,torch_version,transformers_version,cuda_version,generation_config,raw_response`。
不支持的字段用 null，不能用 0 冒充。E5 的 Gemini 返回值额外保存 `returned_model/modelVersion`、request ID 和 thinking token 数。

每条 run 记录包含：`run_id,item_id,base_id,kind,model_key,model_id,model_revision,marker_id,role,prompt_id,replicate,attempt,status,output_text,usage,request_hash,config_hash,env_hash,git_commit,timestamp_utc`。

`run_id` 由冻结的 item/prompt/model/config 和 replicate=0 确定；attempt 追加记录。`env_hash` 由设备类型、GPU 型号、dtype 和库版本计算；`validate_runs` 检查同一模型的所有正式记录 env_hash 相同。

密钥和数据：
- 主实验不需要任何密钥。
- E5 的 Gemini key 只放在本地环境变量或 Colab Secrets 中，提交 `.env.example`，不提交 `.env`、带输出的 notebook 或带凭据的日志。
- 原始数据是否可随仓库发布，取决于数据集许可。默认提交下载脚本、来源说明和派生项；公开原始全文前先检查许可。

## 10. 每人运行的明确命令

完成实现并合并到同一冻结版本后执行：

```bash
# Deelip：生成并验证数据
python -m src.data.build_items --config configs/protocol.yaml
python -m src.data.validate_items --config configs/protocol.yaml

# Eric：全矩阵离线预览，不加载模型
python -m src.run --model all --split eval --suite all --dry-run

# D1：三人各自在目标环境做 smoke 测试；Hang 在 Mac 上用 fp32 跑三模型 smoke 作对照
python -m src.env_check --model qwen3_4b --out outputs/env_checks/
python -m src.env_check --model phi4_mini --out outputs/env_checks/
python -m src.env_check --model granite4_micro --out outputs/env_checks/

# 三人分别跑自己的开发矩阵：每人 36 条
python -m src.run --model qwen3_4b --split dev --suite main --resume
python -m src.run --model phi4_mini --split dev --suite main --resume
python -m src.run --model granite4_micro --split dev --suite main --resume

# Hang：跨环境复现检查（108 条 DEV，不计入正式结果）
python -m src.run --model all --split dev --suite main --out outputs/repro/ --resume
python -m src.compare_envs --a outputs/raw --b outputs/repro --split dev

# DEV 审核通过、protocol-v1 冻结后：每人 280 条正式生成
python -m src.run --model qwen3_4b --split eval --suite all --resume
python -m src.run --model phi4_mini --split eval --suite all --resume
python -m src.run --model granite4_micro --split eval --suite all --resume

# Hang：合并校验（含同一模型 env_hash 一致）、生成盲评分配
python -m src.validate_runs --split eval --expected 840 --require-single-env
python -m src.annotation.assign --split eval --raters rithvik deelip eric hang --ratings-per-item 2 --seed 6210
python -m src.annotation.merge --require-adjudicated

# 四人分别运行各自分析；都读取同一份最终评分文件
python -m src.analysis.e1_role --config configs/protocol.yaml
python -m src.analysis.e2_marker --config configs/protocol.yaml
python -m src.analysis.e3_prompt --config configs/protocol.yaml
python -m src.analysis.e4_controls --config configs/protocol.yaml
```

各人只执行自己的模型命令。数据和代码的 PR 合并后再运行正式生成。不要各自运行 `--model all` 的正式矩阵：虽然不花钱，但重复的输出会造成版本混乱。在 Colab 上运行时，把 `outputs/` 写到本人的 Google Drive，以便断线后用 `--resume` 继续；完成后把 JSONL 通过 PR 提交，不提交 notebook 的输出单元。

## 11. GitHub Issue / PR 的分工与验收

| Issue | 负责人 | 交付 | 验收 | 依赖 |
|---|---|---|---|---|
| I01 协议与契约 | Hang | protocol、schema、目录、AGENTS 规则、分工 | 人、命令、输入输出、数量全部一致 | 无 |
| I02 语言规则 | Rithvik | 3 条文献核查、3 个模板、评分手册、原论文模型核对 | 每个类别有依据；预设、scope、否定、归属含例子 | I01 |
| I03 数据构建 | Deelip | 原始来源 manifest、23 基础项、158 条输入、生成/校验代码 | dev18 + eval120 + control20；无重复来源/命题；两人审核 | I01；最终依赖 I02 |
| I04 共用运行器与本地后端 | Eric | run.py、`hf_local`、env_check、dry-run、resume、日志、依赖锁定、离线 CI、Colab/Kaggle notebook | offline 矩阵 840；缺失/重复检测；显式贪心配置不继承仓库默认；渲染 prompt 与 env_hash 保存；无需 GPU 和密钥即可跑测试 | I01 |
| I05 模型 A 环境验证 | Rithvik | `qwen3_4b` 的 D1 smoke 报告：环境、显存、时延、模板检查 | 满足 §5.2 的 D1 通过标准；失败时提出替补的 protocol-change | I04 |
| I06 模型 B 环境验证 | Deelip | `phi4_mini` 的同上报告 | 同上 | 同上 |
| I07 模型 C 环境验证 | Eric | `granite4_micro` 的同上报告 | 同上 | 同上 |
| I07b 跨环境复现检查 | Hang | Mac fp32 smoke 对照；108 条 DEV 重跑；逐字一致率报告 | 报告一致率与差异样例，不进入正式指标 | I05–I07 |
| I08 标注与公共统计 | Hang | 分配/合并代码、指标和 bootstrap | 每条2评分、每人420；fixture 验证分母；cluster 保留配对 | I01 |
| I09 冻结与运行 | Rithvik/Deelip/Eric 各自子 Issue | 每人36 DEV +280正式输出、manifest | 同一protocol hash；同一模型同一env_hash；无重复成功记录；缺失有记录且不算成功 | I02–I08 |
| I15 可选 E5 | Rithvik | Gemini 免费配额核查截图/记录、`providers/gemini.py`、DEV 36 条 | 满足 §6 E5 的四个启用条件，否则关闭 Issue 并记录原因 | I04；D3 团队决定 |
| I10 E1 分析 | Rithvik | 指定3个输出文件和可复现命令 | 由共同评分文件重建；无手改数字 | 正式标签冻结 |
| I11 E2 分析 | Deelip | 指定4个输出文件和命令 | 同上；不把60个变体当独立样本 | 正式标签冻结 |
| I12 E3 分析 | Eric | 指定3个输出文件和命令 | 同上；报告遗漏与角色差距绝对值 | 正式标签冻结 |
| I13 E4 与集成 | Hang | 对照、总表、结果检查 | 840可追溯；主分析与敏感性一致记录 | I10–I12 |
| I14 论文与展示 | Hang 统稿，全员审核 | paper、图表、引用、展示、复现说明 | 每个结论对应表/图/案例；所有数字由代码生成 | I13 |

代码 owner：
- Rithvik：`configs/models.yaml` 中 `qwen3_4b` 一项、可选的 `providers/gemini.py`、`analysis/e1_role.py`。
- Deelip：`data/*`、`configs/models.yaml` 中 `phi4_mini` 一项、`analysis/e2_marker.py`。
- Eric：运行器、`providers/hf_local.py`、`env_check.py`、notebook、依赖、`granite4_micro` 一项、E3。
- Hang：schema、`compare_envs.py`、标注、公共分析、E4 和论文集成。

分支例：`rithvik/linguistics-qwen`、`deelip/dataset-phi`、`eric/runner-hf-local`、`hang/eval-integration`。尽量拆成小 PR，先接口再实现，再数据/结果。PR 描述必须有 Issue、修改内容、命令、输出数量、测试证据和未解决问题。

Hang 合并其他成员 PR，自己的 PR 由 Eric 审查。语言/数据由 Rithvik 与 Deelip 交叉审查。正式数据生成从共同 tag `protocol-v1` 执行；之后修复必须另行记录版本及重跑范围。

## 12. 最快可行时间线：D0 为仓库可用且成员开始工作的当天

前提：
- 四人每天可投入约 1.5–2.5 小时，标注阶段可能更多；周末也按工作日计。
- 至少一种免费环境可用。最坏情况由 Hang 的 Mac 兜底，所以计算资源不会阻塞进度。
- 以交付依赖推进，不为了等周会停工。

以下日期假设 **D0 = 2026-10-19（周一）**。若仓库晚于这天建好，所有日期顺延。

| 时间 | Rithvik | Deelip | Eric | Hang | 检查节点 |
|---|---|---|---|---|---|
| D0 10/19 | 读协议、接 I02/I05；在 AI Studio 查看免费配额（E5） | 接 I03/I06 | 接 I04/I07；先交接口、`hf_local` 和 `env_check` 的最小 PR | 建仓库/Issues、合并契约；启动会 | 所有人确认免费环境可用，且没有绑卡 |
| D1–D2 10/20–21 | 规则手册、审核数据；D2 跑模型 A smoke | 23 个基础项、构建器；D2 跑模型 B smoke | runner、CI、notebook；D2 跑模型 C smoke | 标注/指标模块；Mac fp32 smoke 对照；审 PR | D2 结束时确定三个模型（必要时启用替补） |
| D3 10/22 | 跑模型 A 的 36 条 DEV | 跑模型 B 的 36 条 DEV | 跑模型 C 的 36 条 DEV | 重跑 108 条 DEV 做复现检查；抽取 24 条校准样本 | DEV 齐全 |
| D4 10/23 | 校准评分 | 同左 | 同左 | 同左；30 分钟校准会；决定 E5 是否启用 | 冻结评分手册、tag `protocol-v1` |
| D5 10/24 | 跑模型 A 的 280 条正式生成 | 跑模型 B 的 280 条 | 跑模型 C 的 280 条 | 校验 840 条、发标注包 | 正式 840 条输出齐全 |
| D6 10/25 | 缓冲：处理 Colab 中断或接替 | 同左 | 同左 | 必要时接替运行 | — |
| D6–D9 10/25–28 | 每天约 105 条评分 | 同左 | 同左 | 同左并处理分配问题 | 1680 次独立评分完成 |
| D10 10/29 | 分歧处理 | 同左 | 同左 | 主持分歧流程 | 标签冻结 |
| D11–D12 10/30–31 | E1 | E2 | E3 | E4、复现性附表 | 实验结果包完整 |
| D13–D17 11/1–5 | 方法、证据、相关工作 | 数据与标注说明 | 运行配置与复现说明 | 根据真实结果写完整论文 | 论文初稿 |
| D18–D19 11/6–7 | 交叉审稿、排练 | 同左 | 复现检查、排练 | 统稿、展示和提交包 | **首版完整论文** |
| 11/8–11/30 | 缓冲、按反馈修改；若启用 E5，其评分安排在 10/30–11/2，与分析并行，不阻塞 E1–E4 | | | | 11/30 是最终截止，不是目标 |

若每天可用时间更少，按实际工时顺延，不牺牲独立标注。即使整体延后 2 周，首版论文也在 11/21 前完成，离 11/30 仍有缓冲。

周会：
- D0（10/19）开启动会，之后每 7 天一次、每次 45 分钟（10/26、11/2、11/9……），直到提交。
- D4 校准会 30 分钟；D10 结果讨论可另开 20 分钟短会。
- 每天在 Issue 更新“已交付文件 / 阻塞 / 下一步”，有阻塞当天提出。

## 13. 范围与验收边界

- 项目成功是完成可复核的配对实验，不要求必须出现显著身份差异。
- 20个基础命题是受工时约束的探索性样本，不是经过power分析证明足够。若扩大，必须在正式运行前决定样本量，或把后续扩展作为单独版本完整报告，不能根据初步显著性随意停采。
- 主结果冻结后，才考虑自然对话、外部数据集、重复采样或更大样本。每项补充有新Issue，不能阻塞首篇完整论文。
- 当前短句实验只支持简单控制陈述中的身份敏感性；完整就诊摘要的泛化留作后续或明确局限。
- 论文以实验产物为基础。每个实验owner提交方法、表图、案例和结论边界；Hang重组论证并统稿，不需要替别人重写代码或补做未交实验。
- 结论只适用于三个 3–4B 开放权重指令模型，在固定 revision 与贪心解码下的表现；不外推到商业大模型或其他解码设置。E5 若完成，只作为单一闭源模型的探索性补充。

## 14. 资源不足时的分级缩减方案

原则：
- 缩减只能因为**资源**（算力、模型可用性、人工工时），不能因为看到了结果。
- 每一级都要在相应节点之前，通过 `protocol-change` PR 决定并记录。
- 缩减的优先顺序是：**先缩减模型数量，最后才动设计本身**。20 个基础命题、三种表达、Doctor/Patient 配对、P0/P1、确定性对照，以及每条两人独立评分，在任何一级都不删减。

| 级别 | 触发条件 | 处理 | 正式输出 / 人工评分 | 决定时点 |
|---|---|---|---|---|
| L0 完整方案 | 三个主模型都通过 D1，四人工时正常 | 按本协议执行；E5 视条件决定 | 840 / 1,680（每人 420） | — |
| L1 换环境 | Colab 分不到 GPU、会话反复中断、fp16 出现数值问题 | 按 §5.3 的顺序换到 Kaggle → 成员 Mac → Hang 的 Mac；模型和配置不变，在新环境整体重跑该模型 | 不变 | 该模型开始正式运行之前 |
| L2 换模型 | 某个主模型未通过 D1 检查（加载失败、模板问题、普遍空输出或乱码） | 按 R1 → R2 → R3 的顺序启用替补，保持三个不同开发方 | 不变 | D2 结束前 |
| L3 放弃 E5 | Gemini 免费配额不足、需要绑卡、DEV 不合格，或团队没有余力评分 | 不运行或不报告 E5 | 不变 | D4 |
| L4 减为两个模型 | D4 校准时实测评分速度显示，四人在 D6–D9 内无法完成 1,680 次评分（例如每条明显超过 1.5 分钟，或有成员工时受限） | 三个模型仍全部生成（不花钱）；**事先按 A → B → C 的顺序**确定先评分 A、B，C 若后续有时间则整体评分并报告，否则只说明已生成但未评分 | 先评 560 / 1,120（每人 280） | D4，冻结时写入 protocol-v1 |
| L5 最小可报告版本 | 只有一个模型能完成双人评分 | 只报告单模型的 E1–E4；E4 的跨模型部分改写为局限说明 | 280 / 560 | D4 或评分中途，须写明原因 |

不允许的缩减：
- 只评 P0、不评 P1；
- 删掉确定性对照；
- 把双人评分改为单人评分；
- 用 Codex/LLM 代替人工评分；
- 按模型或条件挑选“有效果”的部分评分；
- 减少基础命题个数。

如果确实需要改动上述任何一项，必须作为新协议版本，完整说明影响。

## 15. 资源核查记录（2026-10-17）

以下信息来自官方页面或 Hugging Face API 的当日读取。账号层面的实际额度**没有**核实，D0–D1 由各成员在自己的账号中确认，并截图存入 `docs/model_access.md`。

| 资源 | 当日核查结果 | 对本项目的结论 |
|---|---|---|
| Hugging Face 模型仓库 | §5.2 的 3 个主模型和 3 个替补均为非 gated；许可为 Apache-2.0 或 MIT；revision SHA 与参数量已从 HF API 读取 | 主实验方案 |
| Google Colab 免费版 | FAQ：GPU 类型随时间变化，免费 GPU 受严格限制；资源与限额不保证；会话最长 12 小时，可能无预警终止 | 首选，但不能依赖 |
| Kaggle Notebooks | 每周约 30 小时 GPU；P100 或 T4×2；会话 12 小时，空闲 20 分钟断开；可能排队。手机号验证要求未在官方文档中核实 | 第二选择 |
| Gemini API 免费层 | 无需绑卡；免费层内容会用于改进产品；各模型的 RPM/RPD 只在 AI Studio 显示，且“不保证”；新项目无法使用 2.5 系列；Gemini 3 不建议 temperature<1.0，minimal thinking 不保证关闭思考 | 只作为可选 E5 |
| Groq 免费版 | gpt-oss-120b/20b 每天 1K 请求；Llama 3.x 模型已于 2026-08-16 下线；preview 模型可能随时下线 | 不采用（推理模型，且模型频繁变动） |
| OpenRouter `:free` | 未购买额度时每天共 50 次请求；部分免费模型标注了到期日 | 不采用 |
| GitHub Models | 2026-07-30 已完全停用 | 不可用 |
| HF Inference Providers | 免费账号每月额度为 $0 | 不可用 |
| Cerebras | 需验证付款方式；试用额度 30 天过期 | 违反零费用规则 |
| Mistral 免费模式 | 无需绑卡，但默认使用数据训练；具体限额未核实 | 不采用 |

各页面的 URL 写入 `docs/model_access.md`：
- `ai.google.dev/gemini-api/docs/pricing`、`/rate-limits`、`/thinking`
- `console.groq.com/docs/rate-limits`
- `openrouter.ai/docs/api/reference/limits`
- `docs.github.com/en/github-models`
- `huggingface.co/docs/inference-providers/pricing`
- `research.google.com/colaboratory/faq.html`
- `kaggle.com/docs/notebooks`、`kaggle.com/docs/efficient-gpu-usage`
- `huggingface.co/api/models/<id>`
