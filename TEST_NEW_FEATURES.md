# 🧪 新功能测试指南

## 测试查询扩展

```bash
# 测试查询扩展器
python3 query_expander.py
```

**预期输出**：
```
原始查询: 阿斯巴甜对健康的影响
匹配概念: ['阿斯巴甜']
扩展术语: ['aspartame', 'APM', '天冬酰苯丙氨酸甲酯']...
```

---

## 测试证据分级

```bash
# 测试证据分级器
python3 evidence_ranker.py
```

**预期输出**：
```
文献分级结果：

1. Test paper 1
   期刊: Nature (2023)
   证据等级: Level 1 - 高质量证据
   研究类型: rct
   综合评分: 4.35/5.0
```

---

## 测试完整API

```bash
# 启动服务器
python3 app.py

# 在另一个终端测试
curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "阿斯巴甜对健康有什么影响？"}'
```

**检查点**：
1. 控制台应显示：`[查询扩展] 匹配概念: ['阿斯巴甜']`
2. 控制台应显示：`[证据分级] 对 X 篇文献进行分级...`
3. 返回的references应包含：
   - `evidence_level`: 1-5
   - `evidence_label`: "高质量证据"等
   - `study_type`: "rct", "animal"等
   - `final_score`: 综合评分

---

## 测试不同查询

### 测试1：同义词扩展
```bash
curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "stevia的甜度如何？"}'
```

**预期**：
- 应该检索到包含"甜菊糖"、"stevioside"的文献
- 控制台显示扩展术语

### 测试2：证据分级
```bash
curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "糖醇的代谢机制"}'
```

**预期**：
- 高质量文献（Nature、Science）排在前面
- 每篇文献都有evidence_level标签
- 按final_score排序

---

## 验证优化效果

### 对比测试

**优化前**：
- 只检索"阿斯巴甜"
- 只按相关度排序
- 可能遗漏"aspartame"的文献

**优化后**：
- 检索"阿斯巴甜" + "aspartame" + "APM"
- 按相关度 + 证据质量排序
- 高质量文献优先显示

---

## 故障排除

### 问题1：ImportError

```bash
# 确保在项目根目录
pwd  # 应该显示 .../FCN_SweetSeek

# 确保文件存在
ls query_expander.py evidence_ranker.py
```

### 问题2：服务器启动失败

```bash
# 检查端口占用
lsof -i :5001

# 重启服务器
pkill -f "python.*app.py"
python3 app.py
```

### 问题3：查询扩展不工作

**检查控制台输出**：
```
[查询扩展] 原始: xxx
[查询扩展] 匹配概念: [...]
```

如果没有显示，检查：
1. query_expander是否正确导入
2. 查询是否包含已知术语

---

## 性能测试

```bash
# 测试响应时间
time curl -X POST http://localhost:5001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "甜味剂对健康的影响"}'
```

**预期**：
- 查询扩展：<0.1秒
- 证据分级：<0.5秒
- 总响应时间：5-10秒（主要是LLM生成）

---

## 下一步

测试通过后：
1. 更新前端显示证据等级标签
2. 添加更多甜味剂同义词
3. 优化评分权重
4. 收集用户反馈

---

**测试时间**：2024-12-17  
**版本**：v3.0
