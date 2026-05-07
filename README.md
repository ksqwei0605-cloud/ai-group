# AI 群聊辩论室

多智能体辩论协作系统 — 用户在终端发起一个问题，5 个 AI Agent（各绑定不同国产大模型 + 不同人设）互相讨论、争辩、纠错，最终输出一份打磨过的**执行计划（Plan）**，你可以将这份 Plan 直接交给 Claude Code 去执行。

## 效果预览

```
👤 主持人: 百万级用户的web应用怎么加实时通知功能？

🔵 [架构师·扶摇] DeepSeek-v4-pro
   核心矛盾：高并发长连接 vs 资源成本。推荐自建WebSocket +
   Redis Pub/Sub + 连接收敛。单节点5万连接，20台覆盖百万在线...

🟢 [研究员·通明] Kimi-k2.6
   Redis Pub/Sub在百万级Topic下会触发广播风暴！建议改用Redis
   Streams或Centrifugo。另外你评估过消息体大小的QPS吗？@架构师

🟡 [拆解者·析微] GLM-5.1
   我采纳研究员的修正，落地为以下执行步骤：
   Step 1: 容量规划与基准测试...
   Step 2: Redis Streams消费者组搭建...

🔴 [挑战者·破壁] DeepSeek-v4-pro
   "单节点5万连接"从哪来的？是空载心跳还是4KB单播？
   Redis Streams的XCLAIM延迟你们测过吗？
   你们的成本模型完全是盲猜...

...（多轮辩论）...

🟣 [裁决者·衡道] Doubao-seed-2.0-pro
   ## 最终执行计划
   ### 技术方案：Centrifugo + Redis Streams + 混合推送分层
   ### 执行步骤：
   Step 1: 签署《通知分级合约》...
   Step 2: 基准压测与容量规划...
   ...
```

## 工作原理

```
你发一个问题
    │
    ▼
Phase 1 — 结构化发言（Round 1~4）
    Round 1: [架构师]    — 提出方案框架和技术路线
    Round 2: [研究员]    — 补充行业背景 + 替代方案
    Round 3: [拆解者]    — 拆成可执行的具体步骤
    Round 4: [挑战者]    — 集中挑刺 + 追问边界
    │
    ▼
Phase 2 — 自由辩论（Round 5+）
    允许 @角色 插话，PriorityQueue 调度
    持续辩论直到收敛或用户 /stop
    │
    ▼
[裁决者]    — 综合各方观点，输出结构化最终 Plan
    │
    ▼
保存至 debates/ 目录（JSON）
```

## 角色与模型

| 角色 | 人设 | 默认模型 | 核心职责 |
|------|------|----------|----------|
| **架构师·扶摇** | 15年全栈架构师，信奉"简单即美" | DeepSeek-v4-pro | 提出方案框架，说明 trade-off |
| **研究员·通明** | 博学的技术研究者，熟知业界实践 | Kimi-k2.6 | 补充背景、替代方案、边界条件 |
| **拆解者·析微** | 务实的工程执行专家 | GLM-5.1 | 把方案拆成可执行的编号步骤 |
| **挑战者·破壁** | 挑剔的技术审计官，不交朋友只找漏洞 | DeepSeek-v4-pro | 挑刺、追问、压力测试 |
| **裁决者·衡道** | 公正的技术仲裁者 | Doubao-seed-2.0-pro | 收敛分歧，输出结构化最终 Plan |

> 架构师和挑战者使用同一模型（DeepSeek-v4-pro）但 system prompt 完全不同，产生真实的技术对抗。

## 目录结构

```
ai-groupchat/
├── main.py              # 入口，交互式 CLI
├── test_run.py          # 非交互测试脚本（自动跑一轮）
├── orchestrator.py      # 辩论引擎 — 发言调度、质量检测、@ 机制、终止判断
├── agent.py             # Agent 类 — 封装 OpenAI 兼容 API 调用
├── context_manager.py   # 对话历史管理 + JSON 持久化
├── file_handler.py      # 本地文件读取（支持 40+ 文本格式和 PDF）
├── ui.py                # Rich 终端界面
├── config.yaml          # Agent 配置（模型名、API Key、Base URL）
├── prompts/             # 每个角色的 system prompt
│   ├── architect.txt
│   ├── researcher.txt
│   ├── decomposer.txt
│   ├── challenger.txt
│   └── arbiter.txt
├── debates/             # 每次辩论的 JSON 记录（运行时自动生成）
└── README.md
```

## 环境要求

- **Python 3.9+**
- **Windows** / macOS / Linux 均可

### 依赖

```
openai >= 1.0        # 统一的 API 客户端（所有国产模型都兼容 OpenAI 格式）
rich >= 13.0         # 终端美化
PyYAML >= 6.0        # 配置文件解析
```

### 安装

```bash
# 1. 克隆或进入项目目录
cd D:\AI_Tools\ai-groupchat

# 2. 安装依赖
pip install openai rich pyyaml
```

## 配置

编辑 `config.yaml`，修改每个 Agent 的 API 配置：

```yaml
agents:
  architect:
    name: "架构师·扶摇"
    role: architect
    model: deepseek-v4-pro          # 你的模型名
    api_base: https://api.deepseek.com   # API 地址
    api_key: sk-xxxxxxxxxxxx         # API Key
    color: cyan
    priority: 3
    temperature: 0.8

  # ... 其余 4 个 Agent 同理
```

### 国产模型 API 信息速查

| 厂商 | Base URL | 获取 Key |
|------|----------|----------|
| DeepSeek | `https://api.deepseek.com` | [platform.deepseek.com](https://platform.deepseek.com) |
| Kimi（月之暗面）| `https://api.moonshot.cn/v1` | [platform.moonshot.cn](https://platform.moonshot.cn) |
| GLM（智谱）| `https://open.bigmodel.cn/api/paas/v4` | [open.bigmodel.cn](https://open.bigmodel.cn) |
| Ark（火山引擎）| `https://ark.cn-beijing.volces.com/api/v3` | [console.volcengine.com/ark](https://console.volcengine.com/ark) |

> **Ark 注意**：火山引擎需要在控制台创建推理接入点，用 `ep-xxxxxxxxxxxx` 作为 model 名。

## 使用方法

### 交互模式

```bash
python main.py
```

1. 终端打印横幅和已配置的 Agent 列表
2. 输入你的问题，回车
3. 5 个 Agent 依次发言，实时查看辩论过程
4. 辩论中随时输入：
   - `/stop` — 当前轮结束后触发裁决者总结
   - `/skip` — 跳过当前发言者
   - `/file <路径>` — 上传本地文件，内容注入群聊上下文，所有 Agent 可见
   - 直接打字 — 以主持人身份插入消息
5. 裁决者输出最终计划后，辩论结束
6. JSON 记录自动保存到 `debates/` 目录

### 上传文件

支持在辩论前或辩论中上传本地文件，内容会作为共享参考资料注入对话，所有 Agent 都能看到并基于文件内容讨论。

**辩论前上传：**
```bash
>>> /file D:\docs\需求文档.md
  ✓ 已上传: 需求文档.md
>>> /file D:\docs\压测报告.txt
  ✓ 已上传: 压测报告.txt
>>> 请分析这些文档并给出技术方案
```

**同行简写（路径 + 问题写在同一行）：**
```bash
>>> /file D:\docs\需求.md 分析这份需求文档
  ✓ 已上传: 需求.md
```

**辩论中上传：**
```bash
🔵 [架构师] ...正在发言...
>>> /file D:\docs\补充材料.txt
  ✓ 已上传文件到群聊: 补充材料.txt
```

支持的文件类型：`.txt` `.md` `.py` `.js` `.json` `.yaml` `.html` `.sql` 等 40+ 种文本格式，以及 PDF（需 `pip install PyPDF2`）。单文件限制 500KB。

### 测试模式（无需交互）

```bash
python test_run.py
```

test_run.py 中硬编码了一个测试问题，自动跑完整轮辩论，适合验证配置是否正确。

## 辩论规则（内置于 system prompt）

为防止 AI 互相吹捧、无意义附和，每个 Agent 的 system prompt 中包含铁律：

1. **禁止无脑附和** — "我同意XX"后面必须有具体补充或转折
2. **禁止为否定而否定** — 每个反对意见必须附带具体技术理由
3. **每轮发言必须推进讨论** — 不能重复前面说过的内容
4. **发言简洁有力** — 控制在 400 字以内
5. **@ 机制** — 用 `@架构师` 等格式定向追问

## 低质量发言检测

Orchestrator 层会自动检测：
- 以"我同意""你说得对""有道理"开头且无转折词 → 标记为低质量
- 要求该 Agent 重新生成（最多一次）
- 同一 Agent 连续 2 次低质量 → 跳过本轮

## 自定义

### 更换角色

1. 编辑 `config.yaml` 中对应 Agent 的 `model`、`api_base`、`api_key`
2. 编辑 `prompts/<role>.txt` 调整人设和辩论风格

### 增减角色

1. 在 `config.yaml` 中新增或删除 agent 条目
2. 在 `prompts/` 中新增或删除对应的 prompt 文件
3. 修改 `config.yaml` 中 `debate.phase1_order` 和 `debate.free_debate_order`

### 调整辩论轮次

```yaml
debate:
  max_rounds: 10        # 自由辩论最大轮数
  low_quality_threshold: 2  # 连续低质量发言跳过阈值
```

## 常见问题

**Q: 为什么某个 Agent 不说话？**
A: 检查对应 API Key 是否正确、Base URL 是否匹配、模型名是否存在。运行 `python test_run.py` 可以看到详细错误。

**Q: 终端中文显示乱码？**
A: Windows 终端默认编码是 GBK。项目已内置 UTF-8 修复，如果还有问题，在终端执行 `chcp 65001`。

**Q: 如何只使用 4 个模型（不用裁决者）？**
A: 将 `config.yaml` 中 `arbiter` 部分删除，并调整 `phase1_order`。辩论会在自由辩论耗尽轮次后自动结束。

**Q: 一个 DeepSeek Key 能给架构师和挑战者共用吗？**
A: 可以。它们是同一个 API Key 的两个独立调用。

## License

MIT
