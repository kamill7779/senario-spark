# 架构概览

SenarioSpark 的 MVP 架构围绕短剧视频理解和即时互动触发展开：

```text
视频输入
  -> AI 理解服务
  -> 结构化内容数据
  -> Go 后端存储与分发
  -> 移动端高光互动渲染
  -> 用户互动事件回流
```

Python AI 服务负责模型驱动的视频理解。Go 后端负责产品 API、持久化、分发和稳定性。前端负责视频播放、内容工作台和低门槛互动渲染。

生产环境中，AI 分析链路采用确定性工作流控制，不做成一个全流程大 Agent。只有高光识别与证据反查阶段使用受控的 `Highlight Extraction Agent`，由它读取剧本、片段、ASR 和关键帧证据，最终输出可入库的精准高光结构。

llm-wiki 风格图谱和向量索引不拆成新服务，作为同一个 Python `understanding-service` 内的低频增强 pipeline，一次生成，多次查询和分发。

v1 核心分析链路、图谱增强模块、数据模型和真实片段示例见 [核心分析架构与数据结构 v1](./core-analysis-data-structures.md)。
