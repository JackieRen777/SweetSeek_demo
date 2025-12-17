# Design Document

## Overview

本设计文档描述了PDF文献元数据提取和优化显示功能的技术实现方案。该功能将改进SweetSeek系统的参考文献显示，通过提取和展示结构化的文献元数据，提供更专业和用户友好的引用体验。

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Browser)                    │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  Reference Panel │◄────────│  Hover Tooltip Component│  │
│  │  - ref_1 format  │         │  - Title, Authors, DOI  │  │
│  └────────┬─────────┘         └─────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────┘
            │ API Call
            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (Flask)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              app.py (API Endpoints)                   │  │
│  │  - /api/ask: Enhanced with metadata                  │  │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                  │
│  ┌────────▼─────────────────────────────────────────────┐  │
│  │         persistent_storage.py (RAG System)            │  │
│  │  - Metadata extraction during indexing                │  │
│  │  - Metadata retrieval during query                    │  │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                  │
│  ┌────────▼─────────────────────────────────────────────┐  │
│  │       pdf_metadata_extractor.py (New Module)          │  │
│  │  - Extract metadata from PDF                          │  │
│  │  - Parse journal, year, title, authors, DOI          │  │
│  └────────┬─────────────────────────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  metadata.json   │         │  storage/ (Vector Index)│  │
│  │  - File metadata │         │  - Document embeddings  │  │
│  └──────────────────┘         └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. PDF Metadata Extractor Module

**文件**: `pdf_metadata_extractor.py`

**职责**: 从PDF文件中提取元数据

**接口**:
```python
class PDFMetadataExtractor:
    def extract_metadata(self, pdf_path: str) -> dict:
        """
        从PDF文件提取元数据
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            {
                'journal': str,
                'year': str,
                'title': str,
                'authors': List[str],
                'doi': str,
                'filename': str
            }
        """
        pass
    
    def extract_from_pdf_metadata(self, pdf_path: str) -> dict:
        """从PDF元数据字段提取"""
        pass
    
    def extract_from_first_page(self, pdf_path: str) -> dict:
        """从PDF第一页文本提取"""
        pass
```

**提取策略**:
1. 优先从PDF元数据字段提取（使用pypdf库）
2. 如果元数据不完整，从第一页文本解析
3. 使用正则表达式匹配DOI、年份等模式
4. 对于期刊名，尝试从文件名或文本中识别常见期刊

### 2. Metadata Storage Manager

**文件**: `metadata_storage.py`

**职责**: 管理元数据的持久化存储

**接口**:
```python
class MetadataStorage:
    def __init__(self, storage_path: str = "./storage/metadata.json"):
        pass
    
    def save_metadata(self, file_path: str, metadata: dict) -> None:
        """保存文件的元数据"""
        pass
    
    def get_metadata(self, file_path: str) -> Optional[dict]:
        """获取文件的元数据"""
        pass
    
    def get_all_metadata(self) -> dict:
        """获取所有文件的元数据"""
        pass
    
    def update_metadata(self, file_path: str, metadata: dict) -> None:
        """更新文件的元数据"""
        pass
```

**存储格式**:
```json
{
    "food_research_data/papers/nutrients-12-03408_1.pdf": {
        "journal": "Nutrients",
        "year": "2020",
        "title": "Effects of Sweeteners on Health",
        "authors": ["Smith, J.", "Johnson, A.", "Williams, B."],
        "doi": "10.3390/nu12113408",
        "last_modified": "2024-01-15T10:30:00",
        "filename": "nutrients-12-03408_1.pdf"
    }
}
```

### 3. Enhanced RAG System

**修改文件**: `persistent_storage.py`

**新增功能**:
- 在索引构建时提取并存储元数据
- 在查询时返回元数据信息

**修改点**:
```python
class PersistentRAGSystem:
    def __init__(self, ...):
        self.metadata_storage = MetadataStorage()
        self.metadata_extractor = PDFMetadataExtractor()
    
    def _build_new_index(self) -> bool:
        # 在构建索引时提取元数据
        for document in documents:
            if document.metadata.get('file_path', '').endswith('.pdf'):
                metadata = self.metadata_extractor.extract_metadata(
                    document.metadata['file_path']
                )
                self.metadata_storage.save_metadata(
                    document.metadata['file_path'],
                    metadata
                )
```

### 4. Enhanced API Response

**修改文件**: `app.py`

**修改 `/api/ask` 端点**:
```python
@app.route('/api/ask', methods=['POST'])
def api_ask():
    # ... 现有代码 ...
    
    # 增强references数据结构
    references = []
    for idx, node in enumerate(nodes, 1):
        file_path = node.metadata.get('file_path', '')
        
        # 获取元数据
        metadata = rag_system.metadata_storage.get_metadata(file_path)
        
        if metadata:
            references.append({
                'ref_id': f'ref_{idx}',
                'journal': metadata.get('journal', 'Unknown'),
                'year': metadata.get('year', 'N/A'),
                'title': metadata.get('title', 'Unknown Title'),
                'authors': metadata.get('authors', []),
                'doi': metadata.get('doi', 'Not Available'),
                'filename': node.metadata.get('file_name', ''),
                'score': float(node.score) if hasattr(node, 'score') else 0.0,
                'content': node.text[:200] + '...'
            })
```

### 5. Frontend Reference Component

**修改文件**: `static/main.js`

**新增函数**:
```javascript
function displayReferences(references) {
    const referencesList = document.getElementById('referencesList');
    
    if (references.length === 0) {
        // ... 现有代码 ...
        return;
    }
    
    referencesList.innerHTML = references.map((ref, index) => `
        <div class="reference-item-compact" data-ref-id="${ref.ref_id}">
            <div class="ref-identifier" 
                 onmouseenter="showRefTooltip(event, ${index})"
                 onmouseleave="hideRefTooltip()">
                [${ref.ref_id}: ${ref.journal} ${ref.year}]
            </div>
            <div class="ref-tooltip" id="tooltip-${index}" style="display: none;">
                <div class="tooltip-content">
                    <h4>${ref.title}</h4>
                    <p><strong>Authors:</strong> ${formatAuthors(ref.authors)}</p>
                    <p><strong>Year:</strong> ${ref.year}</p>
                    <p><strong>DOI:</strong> 
                        ${ref.doi !== 'Not Available' 
                            ? `<a href="https://doi.org/${ref.doi}" target="_blank">${ref.doi}</a>`
                            : 'Not Available'}
                    </p>
                </div>
            </div>
        </div>
    `).join('');
}

function formatAuthors(authors) {
    if (!authors || authors.length === 0) return 'Unknown';
    if (authors.length <= 3) return authors.join(', ');
    return authors.slice(0, 3).join(', ') + ' et al.';
}

function showRefTooltip(event, index) {
    const tooltip = document.getElementById(`tooltip-${index}`);
    tooltip.style.display = 'block';
    tooltip.style.opacity = '0';
    setTimeout(() => {
        tooltip.style.opacity = '1';
    }, 10);
}

function hideRefTooltip() {
    document.querySelectorAll('.ref-tooltip').forEach(tooltip => {
        tooltip.style.opacity = '0';
        setTimeout(() => {
            tooltip.style.display = 'none';
        }, 200);
    });
}
```

### 6. CSS Styling

**修改文件**: `static/style.css`

**新增样式**:
```css
/* 简洁的参考文献显示 */
.reference-item-compact {
    position: relative;
    margin-bottom: 0.75rem;
}

.ref-identifier {
    display: inline-block;
    color: var(--primary-color);
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.5rem 1rem;
    background: var(--gray-50);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
}

.ref-identifier:hover {
    background: var(--primary-color);
    color: var(--white);
    transform: translateX(4px);
}

/* Tooltip样式 */
.ref-tooltip {
    position: absolute;
    left: 100%;
    top: 0;
    margin-left: 1rem;
    background: var(--white);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--shadow-lg);
    z-index: 1000;
    min-width: 400px;
    max-width: 500px;
    transition: opacity 0.2s ease-in-out;
}

.tooltip-content h4 {
    color: var(--text-color);
    font-size: 1rem;
    margin-bottom: 1rem;
    line-height: 1.4;
}

.tooltip-content p {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
    line-height: 1.5;
}

.tooltip-content a {
    color: var(--primary-color);
    text-decoration: none;
}

.tooltip-content a:hover {
    text-decoration: underline;
}
```

## Data Models

### Metadata Model

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class PDFMetadata:
    """PDF文献元数据模型"""
    journal: str
    year: str
    title: str
    authors: List[str]
    doi: str
    filename: str
    file_path: str
    last_modified: datetime
    
    def to_dict(self) -> dict:
        return {
            'journal': self.journal,
            'year': self.year,
            'title': self.title,
            'authors': self.authors,
            'doi': self.doi,
            'filename': self.filename,
            'file_path': self.file_path,
            'last_modified': self.last_modified.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PDFMetadata':
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        return cls(**data)
```

### Reference Display Model

```typescript
interface Reference {
    ref_id: string;          // "ref_1", "ref_2", etc.
    journal: string;         // "Nutrients"
    year: string;            // "2020"
    title: string;           // Full paper title
    authors: string[];       // ["Smith, J.", "Johnson, A."]
    doi: string;             // "10.3390/nu12113408"
    filename: string;        // "nutrients-12-03408_1.pdf"
    score: number;           // Relevance score
    content: string;         // Preview text
}
```

## Error Handling

### 错误处理策略

1. **元数据提取失败**
   - 使用默认值填充缺失字段
   - 记录错误日志但不中断流程
   - 显示"Unknown"或"Not Available"

2. **文件访问错误**
   - 捕获文件不存在异常
   - 返回空元数据对象
   - 在UI中显示文件名作为后备

3. **JSON存储错误**
   - 使用文件锁防止并发写入
   - 备份现有metadata.json
   - 失败时恢复备份

4. **前端显示错误**
   - 使用try-catch包裹tooltip显示逻辑
   - 提供降级显示方案
   - 确保UI不会因单个引用错误而崩溃

## Testing Strategy

### Unit Tests

1. **PDF元数据提取测试**
   - 测试从PDF元数据字段提取
   - 测试从文本内容提取
   - 测试DOI正则匹配
   - 测试年份提取
   - 测试作者列表解析

2. **元数据存储测试**
   - 测试保存和读取
   - 测试更新操作
   - 测试并发访问
   - 测试文件不存在情况

3. **API响应测试**
   - 测试增强的references格式
   - 测试元数据缺失情况
   - 测试多个引用的排序

### Integration Tests

1. **端到端测试**
   - 上传PDF → 提取元数据 → 查询 → 显示引用
   - 测试完整的用户流程

2. **UI交互测试**
   - 测试tooltip显示和隐藏
   - 测试悬停动画效果
   - 测试响应式布局

### Property-Based Tests

暂无需要property-based testing的场景，因为主要是数据提取和UI显示逻辑。

## Performance Considerations

1. **元数据提取性能**
   - 仅在首次索引时提取，后续从缓存读取
   - 使用异步处理避免阻塞
   - 限制PDF读取的页数（仅第一页）

2. **存储性能**
   - 使用JSON文件存储，适合小规模数据
   - 考虑未来迁移到SQLite

3. **前端性能**
   - 使用CSS动画而非JavaScript动画
   - 延迟加载tooltip内容
   - 限制同时显示的tooltip数量

## Security Considerations

1. **文件路径安全**
   - 验证文件路径在允许的目录内
   - 防止路径遍历攻击

2. **DOI链接安全**
   - 验证DOI格式
   - 使用target="_blank"和rel="noopener"

3. **XSS防护**
   - 对元数据内容进行HTML转义
   - 使用textContent而非innerHTML（除非必要）
