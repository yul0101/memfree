# DECISIONS — 架构决策日志（冷层）
# 格式: ## DATE | Decision Title | Status: Accepted/Superseded/Rejected
# 用途: 记录重大架构决策及其上下文，供未来追溯

---

## 2026-04-20 | 记忆三层六区分层架构

**状态**: Accepted
**决策者**: Yul
**背景**: 原有一层记忆架构导致 context 膨胀、算力浪费

**方案A — Mem0商业化**: 接入Mem0 API，依赖外部服务
**方案B — 自建三层六区**: 热(零成本)/温(轻量检索)/冷(结构化)分层
**选择**: 方案B，理由：零外部依赖，完全自控

**核心参数**:
- LanceDB tier.coreImportanceThreshold: 0.8
- LanceDB tier.peripheralAgeDays: 30
- LanceDB retrieval.candidatePoolSize: 5
- LanceDB retrieval.minScore: 0.55

**后果**: context 占用降低，回忆精度提升，运维复杂度略增

---

## 2026-04-20 | 接入阿里千问+智谱模型

**状态**: Accepted
**决策者**: Yul
**背景**: deepseek单一模型依赖风险，Gemini偶发性问题

**选择**: 5级fallback策略
1. deepseek/deepseek-chat
2. openrouter/google/gemini-2.5-pro
3. openrouter/qwen/qwen3-235b-a22b
4. qwen/qwen3.5-plus
5. zai/glm-5.1

**后果**: 成本增加约15%，但可用性显著提升

---

## 2026-04-20 | agent-memory-kit 优于 MemoryAgent

**状态**: Accepted
**决策者**: Yul
**背景**: GitHub调研发现两个方案，需选择其一

**对比**:
- MemoryAgent: 4层记忆SDK，需自定义集成代码，不适合当前scope
- agent-memory-kit: Python CLI，开箱即用，支持hot/warm/archive，自动Ebbinghaus遗忘

**选择**: agent-memory-kit，理由：集成成本低，开箱即用

**后果**: 记忆系统与OpenClaw解耦，通过CLI调用

---

## 2026-04-20 | MCP Servers: Replit + Lovable

**状态**: Accepted
**决策者**: Yul
**背景**: 需要打通远程开发工具（Replit）和低代码平台（Lovable）

**配置**:
- Replit MCP: WebSocket bridge via ngrok（需手动启动bridge）
- Lovable MCP: 本地分析，project-path=/Users/yul/WorkBuddy

**限制**: Replit MCP需要ngrok tunnel和Replit extension协同工作，当前为手动模式
**待办**: 探索Replit MCP自动化连接方案

---

## 2026-04-19 | Gateway shutdown 根因分析

**状态**: Open — P1
**背景**: Gateway频繁shutdown，清旧会话后可恢复

**假设**:
1. 会话缓存泄漏
2. token认证超时
3. 并发连接数超限

**验证方案**: 清SESSION-STATE.md后重启验证
**待办**: 记录复现步骤，找出根因
