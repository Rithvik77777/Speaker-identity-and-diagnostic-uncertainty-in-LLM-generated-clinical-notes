# 可以分发给每个人的 Codex 任务说明（中文，v4 零费用版）

状态：这些都是待实施的任务，不代表本地已经有这些模块，也没有运行过任何模型。仓库建立后，先把 EXECUTION_PLAN_ZH_v4.md（审核通过的英文版）放入 `docs/protocol.md`，再把本文件中对应的段落发给每个人。所有人以同一份协议为准。

## 全员共同指令

> 先阅读仓库里的 AGENTS.md 和 docs/protocol.md。主实验已经统一设计好，请只实现分配给我的任务，不要重新设计主实验。正式数据、提示词、模型、revision、dtype、解码参数和指标的任何变更，都先写成 protocol-change 建议，不直接修改。
>
> 本项目总费用为零：
> - 不要写任何需要付款方式、付费套餐或购买额度的代码或步骤；
> - 发现某个步骤需要付费时，停下来告诉我；
> - 不要替我注册账号、接受条款或绑定任何东西。
>
> 正式生成必须满足以下要求：
> - 使用 transformers，按 configs/models.yaml 中锁定的 HF revision 加载模型；
> - 显式使用贪心解码，不继承模型仓库的 generation_config 默认值；
> - batch_size=1；
> - 保存渲染后的 prompt 和环境信息。
>
> 可以用离线 fixture 和 mock provider 开发与测试，但不能把它们当作真实结果。PR 必须写清运行命令、实际记录数、测试证据和未解决事项。遇到模型或环境问题时，显式记录并提出替补方案，不要偷偷切换。

## Rithvik Shivva

> 我是 Rithvik，负责 I02、I05、模型 A（Qwen/Qwen3-4B-Instruct-2507）的运行和 I10，另有可选的 I15（E5）。
>
> 1. 语言规则与评分手册：在 `docs/linguistic_rules.md` 和 `docs/annotation_guide.md` 中核对协议指定的三篇论文，写出 may/possibly/probably 的分类、作用范围、预设排除、极性和归属的评分规则。不要自行建立数值化的确定性刻度。协助审核 Deelip 的 23 个基础命题及其全部模板变体。
> 2. 核实源论文中最佳模型的确切版本和适用指标；无法核实的标为“待核实”。这只用于相关工作讨论，我们的模型已经不同。
> 3. 环境验证：Eric 的 env_check 合并后，在 Colab 免费 T4 上按锁定 revision 运行模型 A 的 smoke 测试。提交显存峰值、时延、渲染后的模板（确认 system 位置正确、没有 `<think>`）、fp16 是否出现空输出或乱码，并与 Hang 的 Mac fp32 对照结果比较。不合格时提出替补的 protocol-change，不要自己换模型。
> 4. runner 合并后，我只运行模型 A 的 36 条 DEV 和 280 条正式输出。数据冻结前不跑正式矩阵。outputs 写到我的 Google Drive，中断后用 `--resume` 继续。
> 5. 可选 E5：先帮我列出在 AI Studio 中查看 gemini-3.5-flash-lite 免费配额的步骤，由我本人查看并截图。确认无需绑卡、配额足够之后，再实现 `src/providers/gemini.py`：记录 returned model/modelVersion、request ID、thinking token 数，key 只从环境变量读取。D4 团队决定启用之前，不运行 E5 的正式矩阵。
> 6. 正式人工标签完成后，实现 `src/analysis/e1_role.py`：调用 Hang 的公共指标和 bootstrap，分析三个模型 P0 输出中的身份效应，生成 e1_role.csv、e1_role.pdf 和 e1_role.md。不要另外计算一套分母，不要把输出条数当作独立样本数。
>
> 另外请列出需要我本人完成的人工核查与评分清单。最后提交几个小 PR，附测试和可复现命令。

## Deelip Kumar

> 我是 Deelip，负责 I03、I06、模型 B（microsoft/Phi-4-mini-instruct）的运行和 I11。
>
> 1. 数据构建：实现 `src/data/build_items.py` 和 `validate_items.py`，按统一协议从 ACI-Bench-MedARC 整理候选基础命题，并记录来源与改写说明。
>    - 目标是 3 个开发基础命题和 20 个正式基础命题，各来自不同的 encounter，规范化后的命题不重复。
>    - 由三种表达和两种角色生成共 158 条输入：18 条开发、120 条正式主实验、20 条正式确定性对照。
>    - 候选提取可以自动化，但来源和语言可用性需要由我和 Rithvik 人工审核；不得伪造来源或审核状态。
> 2. 环境验证：在可用的免费环境（Colab T4 优先，其次 Kaggle 或我自己的 Mac）上运行模型 B 的 smoke 测试，提交的报告内容与 Rithvik 的相同。Phi-4-mini 原生权重是 bf16，在 T4 上要转成 fp16，请特别检查有没有数值溢出、空输出或乱码。
> 3. runner 合并后，我只运行模型 B 的 36 条 DEV 和 280 条正式输出。DEV 和正式运行必须在同一种环境中完成。
> 4. 最终标签冻结后，实现 `src/analysis/e2_marker.py`：用三个模型的 P0 输出比较 may/possibly/probably 三个条件及其中的角色差异，生成 e2_marker.csv、e2_transitions.csv、e2_marker.pdf 和说明文档。三种表达条件分别保留，不把类别转换成概率；统计调用公共模块。
>
> 提交数据与代码的 PR，说明缺失和被拒绝的候选数量、校验结果，以及需要本人复核的条目。

## Eric Fu

> 我是 Eric，负责 I04、I07、模型 C（ibm-granite/granite-4.0-micro）的运行和 I12。
>
> 1. 先交一个最小 PR（目标 D1）：`providers/base.py` 的接口、`providers/hf_local.py`、`src/env_check.py` 和 mock provider，让其他人能尽早做 smoke 测试。
>    - `hf_local` 按 revision 加载模型，只加载一次；使用 apply_chat_template 并保存渲染后的 prompt；显式构造贪心的 GenerationConfig（do_sample=False、max_new_tokens=128、repetition_penalty=1.0、num_beams=1）；batch_size=1；设置 torch.manual_seed(6210)。
>    - 记录 dtype、设备、GPU 型号，以及 torch/transformers/CUDA 版本，并计算 env_hash。
>    - dtype 在 CUDA T4 上用 fp16，在 MPS 和 CPU 上从配置中读取。
> 2. 完整运行器：实现 `src/run.py` 和 `validate_runs.py`（含 `--require-single-env`），支持 dry-run、按唯一 run_id 的 resume、追加式 attempt 记录，以及仅对 OOM/会话中断/下载失败的重试。另外提供 `notebooks/run_colab.ipynb` 和 `run_kaggle.ipynb`，只负责安装锁定依赖、挂载 Drive 和调用 `python -m src.run`，不包含密钥和输出。
>    - 锁定一个同时满足三个模型的 transformers 版本（应不低于 4.56，D1 实测后确定）。
>    - CI 默认离线，不下载模型、不需要 GPU。
> 3. 环境验证：运行模型 C 的 smoke 测试，提交与其他人相同的报告。检查 Granite 的聊天模板在提供 system 时不会再额外注入默认系统提示，并确认没有开启 thinking。
> 4. 我只运行模型 C 的 36 条 DEV 和 280 条正式输出。
> 5. 正式标签冻结后，实现 `analysis/e3_prompt.py`：分析三个模型在 P0/P1 下的 CHR、信息保留、归属、joint fidelity，以及角色 gap 绝对值的变化，输出 e3_prompt.csv、e3_tradeoff.pdf 和说明文档。
>
> 测试要覆盖配对、去重、失败请求处理、分母，以及跨环境记录被 validate_runs 拒绝的情况，不编造任何结果。PR 中附上命令、实际记录数和实测时延。

## Hang Zhao

> 我是 Hang，负责 I01、I07b、I08、I13、I14 以及 PR 整合。
>
> 1. 仓库与分工：按统一协议建立目录、schemas、AGENTS 规则、configs/models.yaml（三个主模型和三个替补，含 revision SHA）、提示词和 Issue 分工。与 Eric 约定公共接口，不替三位成员包办他们的模块。
> 2. 跨环境复现检查：在我的 M4 Pro / 48GB 上用 fp32 运行三个模型的 smoke 对照，然后重跑 108 条 DEV；实现 `src/compare_envs.py`，报告逐字一致率和差异样例。这部分不进入正式指标。若某人的免费环境失败，我按同一冻结配置接替该模型的整个分片。
> 3. 标注工具：实现 annotation/assign.py 和 merge.py。
>    - 840 条正式输出各由两人评分；六种成员配对各 140 条，每人 420 条。
>    - 隐藏模型和提示词条件，保留源文本和说话人。
>    - 初始评分不能被最终评分覆盖。
>    - 若启用 E5，按相同规则另外分配 560 次评分。
> 4. 公共统计：实现 analysis/common.py，包括统一指标、原始一致率、Krippendorff alpha，以及按 base_id 的 10000 次 bootstrap。先用包含省略、否定、归属错误、unclear 和失败请求的 synthetic fixture 验证。正式数据按同一个 protocol hash 和 env_hash 整合，缺失与重复都显式报错。
> 5. D4 根据校准评分的实测速度，按 §14 判断是否需要进入 L4 级缩减，并把决定写入 protocol-v1。
> 6. 实现 E4 的确定性对照和跨模型汇总，汇总其他三人的结果，不把模型差异夸大成开发方之间的结论。拿到真实输出后再组织论文主线，检查每个结论都有对应的表、图或案例。
>
> 代码和数据操作都走 PR；我自己的 PR 交给 Eric 审核，语言和数据的变更交给 Rithvik 与 Deelip 交叉审核。准备 D0 至 D19 的检查表和每周会议议程。没有收到真实输出之前，不撰写任何结果结论。
