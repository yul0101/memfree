# TECH-DEBT — 技术债务追踪（冷层）
# 格式: - [P1/P2/P3] title | identified: DATE | impact: High/Med/Low | status: open/acknowledged/resolved
# 用途: 追踪架构债务，指导未来重构优先级

---

## 待解决

- [P1] **Gateway shutdown 根因未明** | identified: 2026-04-19
  impact: High | status: open
  描述: Gateway频繁shutdown，需清旧会话恢复。根因可能是会话缓存泄漏或token超时。
  修复方向: 记录复现步骤，排查session管理代码

- [P1] **Hermes agent 连通性故障** | identified: 2026-04-20
  impact: High | status: open
  描述: Hermes agent当前无法正常通信，影响日常开发效率
  修复方向: 检查agent启动日志和网络配置

- [P1] **Replit MCP 手动启动模式** | identified: 2026-04-20
  impact: High | status: open
  描述: Replit MCP需要手动启动ngrok tunnel和Replit extension bridge，无法自动化
  修复方向: 研究Replit MCP自动化连接方案，或探索替代远程开发方案

- [P2] **embedding模型选择** | identified: 2026-04-20
  impact: Med | status: open
  描述: 当前使用deepseek-chat做向量embedding，对中文长文本优化不够
  修复方向: 考虑切换到text-embedding-3-small或BGE模型

- [P2] **BGM无版权音乐资源** | identified: 2026-04-20
  impact: Med | status: open
  描述: 产品需要古典乐器风格无版权BGM，尚未找到合适资源
  修复方向: 调研Free Music Archive、Musopen等平台

- [P2] **hot.md 格式与agent-memory doctor 兼容性** | identified: 2026-04-20
  impact: Med | status: acknowledged
  描述: 早期hot.md使用table格式，与agent-memory doctor校验不兼容，后已修复为标准模板
  修复方向: 无需修复，已解决

- [P3] **openclaw.json 多版本备份混乱** | identified: 2026-04-20
  impact: Low | status: acknowledged
  描述: openclaw.json有.bak.1~.bak.4多个备份，来源和时效不明确
  修复方向: 定期清理旧备份，统一备份命名规则

- [P3] **agent-memory-kit Python API未探索** | identified: 2026-04-20
  impact: Low | status: open
  描述: agent-memory-kit提供了lesson_engine/memory_bridge等模块，但CLI外的Python集成未探索
  修复方向: 如需更精细的记忆控制，后续研究storage/subconscious模块

---

## 已解决

- [resolved] **LanceDB tier配置丢失** | identified: 2026-04-20 → resolved: 2026-04-20
  impact: High
  描述: 配置被覆盖导致tier参数丢失
  修复: 已确认配置完整（系grep嵌套对象格式误报），确认tier参数均在openclaw.json中

- [resolved] **pip3找不到agent-memory-kit** | identified: 2026-04-20
  impact: Med
  描述: 直接pip安装失败
  修复: 改用 `pip3 install git+https://github.com/NovasPlace/agent-memory-kit.git@main`

- [resolved] **hot.md table格式不兼容** | identified: 2026-04-20
  impact: Med
  描述: 初版hot.md使用markdown table，与agent-memory doctor校验冲突
  修复: 改用 `@[hot]`、`## Context` 等agent-memory-kit标准模板

---

## 重构路线图

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 解决P1: Gateway shutdown + Hermes连通性 | 当前 |
| Phase 2 | 完善温层: MCP自动化 + Mem0 Facts增强 | 1周内 |
| Phase 3 | 优化embedding模型 + 探索agent-memory-kit Python API | 2周内 |
| Phase 4 | 产品BGM资源落地 + 技术债务清理 | 灵活 |
