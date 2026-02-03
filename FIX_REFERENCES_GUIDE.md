# 修复参考文献显示问题 - 操作指南

## 问题描述
参考文献显示为 "ref_1: Unknown N/A" 而不是实际的期刊名和年份。

## 根本原因
向量数据库存储的是**绝对路径**，而元数据数据库存储的是**相对路径**，导致路径不匹配，无法获取元数据。

## 解决方案
将向量数据库中的所有绝对路径转换为相对路径。

---

## 服务器操作步骤

### 方法一：使用自动化脚本（推荐）

1. **SSH连接到服务器**
   ```bash
   ssh root@8.137.32.247
   # 输入密码
   ```

2. **进入项目目录**
   ```bash
   cd /www/wwwroot/FCN_SweetSeek
   ```

3. **拉取最新代码**
   ```bash
   git pull origin RenJiaqi
   ```

4. **运行修复脚本**
   ```bash
   python3 fix_vector_db_paths.py
   ```
   
   预期输出：
   ```
   向量数据库中的文档数量: 3292
   开始修复路径格式...
   示例 1:
     原路径: /www/wwwroot/FCN_SweetSeek/sweet_related_paper/papers/xxx.pdf
     新路径: sweet_related_paper/papers/xxx.pdf
   ...
   ✅ 成功修复 3292 个文档的路径格式
   ```

5. **重启Flask应用**
   ```bash
   pkill -f "python3 app.py"
   sleep 2
   nohup python3 app.py > logs/app.log 2>&1 &
   ```

6. **验证服务运行**
   ```bash
   ps aux | grep app.py
   curl http://localhost:5001/api/health
   ```

### 方法二：一键执行脚本

```bash
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
bash fix_references_on_server.sh
```

---

## 本地测试验证

修复完成后，在浏览器中测试：

1. **访问网站**
   ```
   http://sweetseek.top
   ```

2. **清除浏览器缓存**
   - Mac: `Cmd + Shift + R`
   - Windows: `Ctrl + Shift + R`

3. **提问测试**
   输入问题，例如："甜味剂有哪些类型？"

4. **检查参考文献**
   参考文献应该显示为：
   ```
   ref_1: Nutrients 2023
   标题: Steviol Glycosides from Stevia rebaudiana...
   作者: Adriana Monserrath Orellana-Paucar
   DOI: 10.3390/molecules28031258
   ```
   
   而不是：
   ```
   ref_1: Unknown N/A
   ```

---

## 技术细节

### 修复前的路径格式
- **向量数据库**: `/www/wwwroot/FCN_SweetSeek/sweet_related_paper/papers/xxx.pdf`
- **元数据数据库**: `sweet_related_paper/papers/xxx.pdf`
- **结果**: 路径不匹配 → 找不到元数据 → 显示 "Unknown N/A"

### 修复后的路径格式
- **向量数据库**: `sweet_related_paper/papers/xxx.pdf`
- **元数据数据库**: `sweet_related_paper/papers/xxx.pdf`
- **结果**: 路径匹配 ✅ → 成功获取元数据 → 显示期刊名和年份

### 修复的文件
- `fix_vector_db_paths.py` - 路径修复脚本
- `fix_references_on_server.sh` - 服务器自动化脚本

---

## 故障排查

### 如果修复后仍显示 "Unknown N/A"

1. **检查向量数据库路径**
   ```bash
   python3 -c "
   import chromadb
   client = chromadb.PersistentClient(path='./chroma_db')
   collection = client.get_collection('sweetseek_papers')
   results = collection.get(limit=3, include=['metadatas'])
   for meta in results['metadatas']:
       print(meta.get('file_path', 'NO PATH'))
   "
   ```
   
   应该显示相对路径，如：`sweet_related_paper/papers/xxx.pdf`

2. **检查元数据数据库**
   ```bash
   python3 -c "
   import json
   data = json.load(open('chroma_db/metadata.json'))
   print('元数据数量:', len(data))
   print('示例路径:', list(data.keys())[0])
   "
   ```

3. **检查Flask日志**
   ```bash
   tail -f logs/sweetseek.log
   ```
   
   查找类似的日志：
   ```
   [调试] 原始路径: sweet_related_paper/papers/xxx.pdf
   [调试] ✅ 找到元数据: Steviol Glycosides from Stevia...
   ```

4. **清除浏览器缓存**
   确保使用 `Cmd+Shift+R` 强制刷新

---

## 预期结果

修复成功后，参考文献将显示完整信息：
- ✅ 期刊名称（如 "Nutrients", "Science", "Diabetes Care"）
- ✅ 发表年份（如 "2023", "2024"）
- ✅ 文章标题
- ✅ 作者列表
- ✅ DOI编号

---

## 联系信息

如有问题，请检查：
1. 服务器日志：`/www/wwwroot/FCN_SweetSeek/logs/sweetseek.log`
2. Flask应用状态：`ps aux | grep app.py`
3. 健康检查：`curl http://localhost:5001/api/health`
