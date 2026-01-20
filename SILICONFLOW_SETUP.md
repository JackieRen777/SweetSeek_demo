# SiliconFlow DeepSeek R1 配置指南

## 📋 配置步骤

### 1. 获取 API Key

1. 访问 [SiliconFlow 官网](https://cloud.siliconflow.cn/)
2. 注册/登录账号
3. 点击右上角"充值"，充值金额（建议先充 ¥10-20 测试）
4. 进入"API 密钥"页面
5. 点击"创建新密钥"
6. 复制生成的 API Key（格式：`sk-xxxxxxxxxxxxx`）

### 2. 修改配置文件

打开项目根目录的 `.env` 文件，找到这几行：

```bash
DEEPSEEK_API_KEY=your_siliconflow_api_key_here
DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
DEEPSEEK_MODEL=deepseek-ai/DeepSeek-R1
```

将 `your_siliconflow_api_key_here` 替换为你的实际 API Key：

```bash
DEEPSEEK_API_KEY=sk-你从SiliconFlow复制的密钥
DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
DEEPSEEK_MODEL=deepseek-ai/DeepSeek-R1
```

### 3. 重启服务器

```bash
# 停止当前服务器（如果正在运行）
# 按 Ctrl+C

# 启动服务器
python3 app.py
```

### 4. 测试

访问 http://localhost:5001，问一个复杂问题测试：

**测试问题示例**：
```
为什么阿斯巴甜在高温下会分解？请从化学结构角度解释，
并说明这对食品加工有什么影响。
```

## 🔄 切换回 DeepSeek 官方

如果想切换回 DeepSeek 官方 API（更便宜），修改 `.env`：

```bash
DEEPSEEK_API_KEY=sk-704c636beab2487d92571132926e4a5b
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-reasoner
```

## 💰 价格对比

| 平台 | 输入价格 | 输出价格 | 优势 |
|------|---------|---------|------|
| DeepSeek 官方 | ¥2/百万tokens | ¥8/百万tokens | 最便宜 |
| SiliconFlow | ¥4/百万tokens | ¥16/百万tokens | 国内快、支付方便 |

## 📊 成本估算

假设每天 100 次问答，平均每次：
- 输入：1000 tokens（问题+检索到的文献）
- 输出：500 tokens（回答）

**每天成本**：
- DeepSeek 官方：约 ¥0.6/天 = ¥18/月
- SiliconFlow：约 ¥1.2/天 = ¥36/月

## ⚠️ 注意事项

1. **R1 模型响应较慢**
   - 因为有"思考"过程
   - 通常需要 5-15 秒
   - 适合复杂问题，不适合简单查询

2. **API Key 安全**
   - 不要将 `.env` 文件提交到 Git
   - 已在 `.gitignore` 中排除

3. **余额监控**
   - 定期检查 SiliconFlow 账户余额
   - 设置余额预警

## 🆚 R1 vs Chat 对比

### 使用 R1 的场景：
- ✅ 复杂科学问题
- ✅ 需要深度推理
- ✅ 机制解释
- ✅ 对比分析

### 使用 Chat 的场景：
- ✅ 简单事实查询
- ✅ 快速问答
- ✅ 信息提取
- ✅ 文献总结

## 🔧 高级：混合模式

如果想根据问题复杂度自动选择模型，可以联系开发者实现混合模式。

## 📞 支持

- SiliconFlow 文档：https://docs.siliconflow.cn/
- DeepSeek 文档：https://platform.deepseek.com/docs
