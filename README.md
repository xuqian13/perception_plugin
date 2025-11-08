# 🔍 麦麦感知插件

让麦麦能够感知自身状态、环境、用户和聊天情况的全方位感知系统。

---

## 📝 功能简介

这个插件让麦麦能够：
- 🖥️ 感知设备运行状况（CPU、内存、磁盘）
- 🤖 感知自身状态（能量、疲劳度、工作负载）
- 📅 **感知当前日程并自动提及**（上课、吃饭、娱乐等）
- 👤 感知用户活跃度和情绪倾向
- 💬 感知对话氛围和节奏
- 🌤️ 感知时间、节日、天气
- 🔐 感知安全风险（敏感内容、垃圾信息）

---

## ✨ 核心特性

### 1. **自我状态感知**
- 实时监控麦麦的能量、疲劳度、工作负载
- **获取当前日程信息**（从自主规划插件）
- 提供完整的自我状态数据供其他系统使用

### 2. **设备状态感知**
- CPU使用率、内存使用率
- 磁盘空间、GPU状态
- 系统负载、网络流量

### 3. **会话上下文感知**
- 对话氛围（热烈/活跃/平静/沉默）
- 对话节奏（快速/正常/缓慢）
- 当前话题和话题连贯性

### 4. **用户状态感知**
- 用户活跃度（轻度/中度/高度/极度活跃）
- 消息发送频率和间隔
- 简单的情绪倾向分析

### 5. **环境感知**
- 时间段（早上/中午/晚上/深夜）
- 工作日/周末
- 中国节假日识别
- 天气状况（可选，需要API）

---

## 🚀 快速开始

### 第一次使用

1. **确保依赖安装**
   ```bash
   pip install psutil
   ```

2. **启用插件**
   - 插件默认已启用，无需额外配置

3. **启用日程注入**（重要）
   - **注意**：日程注入功能已迁移到自主规划插件
   - 在 `autonomous_planning_plugin/config.toml` 中配置：
   ```toml
   [autonomous_planning.schedule]
   inject_schedule = true  # 自动在回复中注入当前日程
   ```

4. **重启麦麦**
   - 生效后，麦麦会在对话中自然提到当前在做什么

---

## 🎯 使用示例

### 设备状态查询

麦麦可以通过工具主动查询设备状态：
```
麦麦调用 get_device_status() 工具
→ 获得: CPU 45%, 内存 60%, 磁盘 70%
```

### 用户状态分析

麦麦可以感知用户的活跃度：
```
麦麦感知到：用户最近1小时发了20条消息（高度活跃）
→ 调整回复：更积极参与对话
```

**注意**：日程自动提及功能已迁移到自主规划插件，详见 `autonomous_planning_plugin/README.md`

---

## ⚙️ 配置说明

配置文件：`config.toml`

### 基础配置

```toml
[plugin]
enabled = true  # 是否启用插件

[perception]
cache_ttl = 60  # 缓存有效期（秒），减少重复查询
```

### 自我状态感知

```toml
[perception.self]
enabled = true  # 启用自我状态感知
```

**注意**：日程注入配置已移至 `autonomous_planning_plugin/config.toml`

### 设备状态感知

```toml
[perception.device]
enabled = true  # 启用设备状态感知
```

### 环境感知

```toml
[perception.environment]
enabled = false  # 启用环境感知（时间、节日等）
enable_weather = false  # 启用天气（需要API）
weather_api_key = ""  # 天气API密钥
location = ""  # 位置（如 "Beijing,CN"）
```

### 用户和会话感知

```toml
[perception.user]
enabled = true  # 启用用户状态感知

[perception.context]
enabled = true  # 启用会话上下文感知
```

### 高级感知模块（可选）

```toml
[perception.behavior_pattern]
enabled = true  # 行为模式感知（作息习惯、活跃时段）
history_days = 30

[perception.social_network]
enabled = true  # 社交网络感知（群组角色、影响力）
interaction_threshold_days = 7

[perception.language_style]
enabled = false  # 语言风格感知（会增加性能开销）
history_window = 30

[perception.event_sequence]
enabled = true  # 事件序列感知（生日、纪念日）
auto_detect = true

[perception.security]
enabled = true  # 安全感知（敏感内容检测）
sensitivity = "medium"  # low / medium / high

[perception.plugin_status]
enabled = true  # 插件系统感知（查看插件状态）
```

---

## 🔧 工作原理

### 日程注入流程

```
1. 用户发送消息
   ↓
2. 感知插件拦截 ON_LLM_BEFORE_GENERATE 事件
   ↓
3. 从自主规划插件获取当前日程
   - 检查 time_window（时间窗口）
   - 找到当前时间段的活动
   ↓
4. 构建日程提示（自然语气）
   例如："这会儿正吃午饭（随便吃点食堂的）"
   ↓
5. 注入到LLM的prompt开头
   ↓
6. LLM生成回复时会自然提到当前活动
```

### 缓存机制（性能优化）

```
每次查询感知信息时：
1. 检查缓存是否有效（60秒内）
2. 有效 → 直接返回缓存
3. 过期 → 重新查询并更新缓存

日程查询也有缓存（60秒TTL）
→ 减少90%+的重复数据库查询
```

### 自动记录

```
消息处理：
- ON_MESSAGE 事件 → 记录用户消息
- 更新用户活跃度、会话上下文

LLM调用：
- ON_LLM_BEFORE_GENERATE → 记录LLM调用次数
- 更新自我工作负载
```

---

## 📂 文件结构

```
perception_plugin/
├── README.md              # 本文档
├── config.toml            # 配置文件
├── plugin.py              # 插件主文件（事件处理器、工具）
├── perception_manager.py  # 感知管理器（统一调度）
└── core/                  # 核心模块
    ├── self_perception.py        # 自我状态感知（含日程获取）
    ├── device_perception.py      # 设备状态感知
    ├── context_perception.py     # 会话上下文感知
    ├── user_perception.py        # 用户状态感知
    ├── environment_perception.py # 环境感知
    ├── behavior_pattern_perception.py  # 行为模式感知
    ├── social_network_perception.py    # 社交网络感知
    ├── language_style_perception.py    # 语言风格感知
    ├── event_sequence_perception.py    # 事件序列感知
    ├── security_perception.py          # 安全感知
    ├── plugin_status_perception.py     # 插件系统感知
    └── tiered_cache.py           # 分层缓存实现
```

---

## 💡 使用建议

### 1. **日程注入功能**（推荐启用）
- 让麦麦的回复更有"生活感"
- 配合自主规划插件使用效果最佳
- 自然提到当前活动，不会刻意强调

### 2. **设备状态监控**
- 了解系统负载，避免过载
- 麦麦可以在CPU/内存高时调整行为

### 3. **用户活跃度分析**
- 识别用户的活跃模式
- 调整回复频率和参与度

### 4. **安全感知**
- 检测敏感内容和垃圾信息
- 建议保持启用

### 5. **性能优化**
- 不常用的模块可以禁用（如 language_style）
- 缓存机制已优化，无需担心性能

---

## 🔧 性能优化

### 已实现的优化

1. **分层缓存系统**
   - 60秒TTL缓存
   - 减少重复查询 90%+

2. **日程查询缓存**
   - 专门为日程查询设计的缓存
   - 每60秒更新一次

3. **按需加载**
   - 未启用的模块不会初始化
   - 节省内存和CPU

4. **异步设计**
   - 所有IO操作使用 async/await
   - 不阻塞主线程

---

## ❓ 常见问题

### Q: 为什么麦麦不提到当前日程？
A: **日程注入功能已迁移到自主规划插件**。请检查：
1. `autonomous_planning_plugin/config.toml` 中 `inject_schedule = true`
2. 自主规划插件是否已生成日程（`/plan list` 查看）
3. 当前时间是否在某个日程的时间窗口内

### Q: 日程信息从哪里来？
A: 从自主规划插件（autonomous_planning_plugin）获取，感知插件只负责查询和提供数据。

### Q: 如何查看当前感知状态？
A: 麦麦可以调用工具查看：
- `get_perception()` - 完整感知状态
- `get_device_status()` - 设备状态
- `get_context_status()` - 会话状态

### Q: 感知插件会影响性能吗？
A: 影响很小：
- 缓存机制减少了90%+的查询
- 设备查询使用 psutil（高性能）
- 异步设计不阻塞

### Q: 如何禁用某些感知模块？
A: 编辑 `config.toml`，设置对应模块的 `enabled = false`

### Q: 天气功能如何使用？
A: 需要配置天气API：
1. 注册 OpenWeatherMap 等服务获取API密钥
2. 在 `config.toml` 中填写 `weather_api_key` 和 `location`
3. 设置 `enable_weather = true`

---

## 📊 数据说明

### SelfStatus（自我状态）

```python
{
  "energy_level": 85.0,              # 能量等级 (0-100)
  "energy_status": "充沛",            # 能量状态
  "workload_level": "正常",           # 工作负载
  "current_activity": "吃午饭",       # 当前活动（来自日程）
  "current_activity_description": "随便吃点食堂的",  # 活动描述
  "next_activity": "上课",            # 下一个活动
  "next_activity_time": "14:00",     # 下一个活动时间
  "overall_status": "良好"            # 整体状态
}
```

### DeviceStatus（设备状态）

```python
{
  "cpu_percent": 45.2,        # CPU使用率
  "memory_percent": 60.8,     # 内存使用率
  "disk_percent": 72.5,       # 磁盘使用率
  "gpu_percent": 30.0,        # GPU使用率（如果有）
  "system_load": [1.2, 1.5, 1.8],  # 1/5/15分钟负载
  "health_status": "良好"      # 健康状态
}
```

### ContextStatus（会话状态）

```python
{
  "atmosphere": "活跃",        # 氛围
  "conversation_pace": "正常", # 节奏
  "current_topics": ["天气", "游戏"],  # 当前话题
  "topic_coherence": 0.75,    # 话题连贯性
  "interaction_pattern": "闲聊"  # 互动模式
}
```

---

## 🔄 版本信息

**当前版本**：2.0.0

**主要特性**：
- ✅ 基础感知模块（5个）
- ✅ 高级感知模块（6个）
- ✅ 日程自动注入
- ✅ 分层缓存优化
- ✅ 自然语气提示

---

## 📞 支持

遇到问题？
1. 检查配置文件格式是否正确
2. 查看日志：`/home/ubuntu/maimai/MaiBot/logs/`
3. 确认依赖已安装：`pip list | grep psutil`

---

**让麦麦拥有感知世界的能力！** 🎉
