# AI功能实现指南

## 概述

本指南说明已实现的AI功能架构和使用方法。

## 核心架构

### 1. 模型选择
- **全部使用 GPT-4o-mini**：成本低（比GPT-3.5便宜62.5%）、速度快、性能好
- **降级策略**：如果GPT-4o-mini不可用，自动降级到GPT-3.5-turbo

### 2. 匹配推荐架构

```
用户资料 → Embedding模型 → 向量数据库 → 相似度搜索 → Top 5 → GPT-4o-mini生成推荐语
         (text-embedding-3-small)    (HNSW索引)      (向量搜索)
```

**技术栈**：
- Embedding模型：`text-embedding-3-small`（成本极低）
- 向量数据库：SQLite（当前）/ PostgreSQL + pgvector（生产环境推荐）
- 搜索算法：余弦相似度（当前）/ HNSW索引（PostgreSQL）

**工作流程**：
1. **SQL硬过滤**：年龄、身高、城市、性别（WHERE语句）
2. **向量搜索**：从硬过滤结果中找出Top 5相似用户
3. **AI生成推荐语**：GPT-4o-mini为每个候选人生成个性化推荐语

### 3. 长期记忆（滚动摘要）

- **存储位置**：`user_ai_memory` 表
- **机制**：每次对话结束后，自动压缩为500-800 tokens的摘要
- **Prompt**："这是旧的记忆 + 刚才的新对话。请把它们合并成一份新的用户档案，保留关键事实，去除寒暄废话。"
- **使用**：下次对话时，只把摘要塞给AI，不传全量历史

### 4. VIP主动询问

**触发机制**：
- **事件驱动（高优先级）**：
  - 用户刚匹配成功（24小时内）→ 询问进展
  - 聊天热度下降（3-7天没操作）→ 主动关心
- **兜底时间（低优先级）**：
  - 每周二、周五晚上8点
  - 用户3天没有任何操作

**防打扰机制**：
- 如果用户正在活跃聊天（1小时内有消息），不打扰
- 如果用户正在App里跟别人聊得火热，AI闭嘴

### 5. System Prompt调教

**AI红娘"小缘"的性格**：
- 温暖、专业、不死板
- 会用但不滥用emoji（每3-5句话1-2个）
- 懂得欲擒故纵（引导话题，不直接给答案）
- 能够分析用户情感状态，给出专业建议

**Few-Shot示例**：
- 教会AI如何回答（好的回答 vs 不好的回答）
- 防止AI说出"作为AI语言模型..."这种话

**性格适配**：
- 根据用户偏好调整对话风格（活泼幽默/温柔知性/干练直接）

## 数据库表

### user_embeddings
存储用户向量嵌入
- `user_id`: 用户ID（唯一）
- `embedding_vector`: 向量数据（JSON格式，1536维）
- `source_text`: 用于向量化的原始文本
- `dimension`: 向量维度（1536）

### user_ai_memory
存储滚动摘要
- `user_id`: 用户ID（唯一）
- `summary_text`: 滚动摘要（500-800 tokens）
- `token_count`: 摘要的token数量
- `last_updated_at`: 最后更新时间

## API端点

### 1. AI对话
- `POST /api/v1/ai-chat/send-message`: 发送消息给AI红娘
- `GET /api/v1/ai-chat/history`: 获取对话历史
- `POST /api/v1/ai-chat/start-registration`: 开始注册引导
- `POST /api/v1/ai-chat/complete-registration`: 完成注册引导（自动创建向量嵌入）

### 2. 匹配推荐
- `POST /api/v1/match/recommend`: 获取AI匹配推荐
  - 流程：SQL硬过滤 → 向量搜索 → GPT生成推荐语

### 3. 其他
- `GET /api/v1/ai-chat/token-usage`: Token使用情况
- `GET /api/v1/ai-chat/recommendation-quota`: 推荐额度

## 定时任务

### VIP主动关怀
- **文件**：`app/core/cron_jobs.py`
- **执行时间**：每周二、周五晚上8点
- **启动方式**：
  ```bash
  python -m app.core.cron_jobs
  ```
  或集成到主服务中（后台线程）

## 数据向量化

### 混合拼接策略

**包含字段**（软匹配）：
- 昵称、性别、职业、学历、国籍、所在国家
- 自我介绍（bio）
- 兴趣爱好、价值观、生活方式、性格特点
- 择偶标准、其他偏好

**排除字段**（硬过滤，用SQL）：
- 年龄、身高、城市（这些用WHERE语句筛选）

### 自动向量化

- **触发时机**：用户完成注册引导时
- **更新时机**：用户更新资料时（需要手动调用）

## 部署注意事项

### 1. 数据库迁移

运行迁移脚本创建新表：
```bash
python migrate_add_ai_tables.py
```

### 2. PostgreSQL + pgvector（生产环境推荐）

当前使用SQLite，但生产环境建议切换到PostgreSQL：

1. **安装pgvector扩展**：
   ```sql
   CREATE EXTENSION vector;
   ```

2. **修改表结构**：
   ```sql
   ALTER TABLE user_embeddings 
   ALTER COLUMN embedding_vector TYPE vector(1536);
   ```

3. **创建HNSW索引**：
   ```sql
   CREATE INDEX ON user_embeddings 
   USING hnsw (embedding_vector vector_cosine_ops);
   ```

### 3. 定时任务

**方式1：独立进程**
```bash
python -m app.core.cron_jobs
```

**方式2：集成到主服务**
在主服务启动时，后台线程运行定时任务

### 4. 依赖安装

```bash
pip install -r requirements.txt
```

新增依赖：
- `schedule>=1.2.0`（定时任务）
- `numpy>=1.24.0`（向量计算）

## 成本优化

### 当前配置
- **全部使用GPT-4o-mini**：$0.15/百万input tokens, $0.60/百万output tokens
- **Embedding使用text-embedding-3-small**：成本极低

### 月度成本估算（1000普通用户 + 100 VIP用户）
- 日常咨询：$75-90
- 注册引导：$9-12
- VIP关怀：$19-23
- 匹配推荐：$100-120
- 信息提取：$9-12
- **总计：约$212-257/月**（在$500预算内）

## 下一步优化

1. **切换到PostgreSQL + pgvector**：支持HNSW索引，提升搜索性能
2. **优化向量搜索**：当前是内存计算，大数据量时需要优化
3. **缓存机制**：缓存常用用户的向量，减少重复计算
4. **批量处理**：批量更新用户向量嵌入

## 测试建议

1. **测试向量化**：完成注册后，检查`user_embeddings`表是否有数据
2. **测试匹配推荐**：调用`/api/v1/match/recommend`，检查返回结果
3. **测试长期记忆**：多次对话后，检查`user_ai_memory`表是否有摘要
4. **测试VIP关怀**：手动触发定时任务，检查是否生成关怀消息












