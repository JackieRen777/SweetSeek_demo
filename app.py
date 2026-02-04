#!/usr/bin/env python3
"""
SweetSeek - Flask Backend
AI-powered research Q&A system
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
import time
from datetime import datetime
from persistent_storage import rag_system
from query_expander import SweetnessQueryExpander
from evidence_ranker import EvidenceRanker
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import traceback
import sys

# NOTE: 文件中的函数多数通过 Flask 的 @app.route 装饰器在运行时被调用。
# 静态分析工具（如 vulture）会将这些运行时注册的路由误判为未使用，
# 所以请在复核 vulture 输出时忽略此文件中的路由标记。

# 加载环境变量
load_dotenv()

# ============================================================
# 日志配置
# ============================================================

def setup_logging():
    """配置应用日志"""
    os.makedirs('logs', exist_ok=True)
    
    logger = logging.getLogger('sweetseek')
    logger.setLevel(logging.INFO)
    
    # 文件处理器（自动轮转，最大 10MB，保留 5 个备份）
    file_handler = RotatingFileHandler(
        'logs/sweetseek.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

app_logger = setup_logging()

# ============================================================
# 装饰器：错误处理和性能监控
# ============================================================

def handle_api_errors(f):
    """统一的 API 错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            app_logger.error(f"API错误 [{f.__name__}]: {error_type} - {error_msg}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': error_msg,
                'error_type': error_type
            }), 500
    return decorated_function

def monitor_performance(f):
    """监控 API 性能"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        
        duration = end_time - start_time
        app_logger.info(f"[性能] {f.__name__} 执行时间: {duration:.2f}秒")
        
        if duration > 10:
            app_logger.warning(f"[性能警告] {f.__name__} 响应时间过长: {duration:.2f}秒")
        
        return result
    return decorated_function

# ============================================================
# 配置验证
# ============================================================

def validate_config():
    """验证必需的配置"""
    required_vars = [
        'DEEPSEEK_API_KEY',
        'DEEPSEEK_BASE_URL',
        'DEEPSEEK_MODEL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")
    
    app_logger.info("✅ 配置验证通过")

app = Flask(__name__, 
            template_folder='frontend',
            static_folder='static')
CORS(app)

# 全局变量
system_ready = False
conversations = []

# 初始化查询扩展器和证据分级器
query_expander = SweetnessQueryExpander()
evidence_ranker = EvidenceRanker()

def initialize_rag_system():
    """初始化RAG系统（使用持久化存储）"""
    global system_ready
    
    try:
        print("[系统] 初始化RAG系统...")
        
        # 加载或创建索引（自动使用持久化）
        success = rag_system.load_or_create_index()
        
        if success:
            system_ready = True
            stats = rag_system.get_stats()
            print(f"[成功] 系统初始化完成")
            print(f"[统计] 文档数: {stats['total_documents']}")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"[失败] 系统初始化失败: {str(e)}")
        return False

# 路由
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/search.html')
def search():
    """文献搜索页面"""
    return render_template('search.html')



@app.route('/about.html')
def about():
    """关于页面"""
    return render_template('about.html')



# API路由



@app.route('/api/init', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_init():
    """初始化系统"""
    global system_ready
    
    app_logger.info("收到系统初始化请求")
    
    if system_ready:
        stats = rag_system.get_stats()
        app_logger.info(f"系统已初始化，文档数: {stats['total_documents']}")
        return jsonify({
            'success': True,
            'message': '系统已经初始化',
            'documents_count': stats['total_documents']
        })
    
    success = initialize_rag_system()
    stats = rag_system.get_stats() if success else {}
    
    if success:
        app_logger.info(f"系统初始化成功，文档数: {stats.get('total_documents', 0)}")
    else:
        app_logger.error("系统初始化失败")
    
    return jsonify({
        'success': success,
        'message': '系统初始化成功' if success else '系统初始化失败',
        'documents_count': stats.get('total_documents', 0)
    })

@app.route('/api/ask', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_ask():
    """
    处理问答请求
    
    重要概念区分：
    - Chunk（文本块）：一篇文献被分割成的小段文本，用于向量检索
    - Paper（文献）：完整的学术论文，一篇文献包含多个chunks
    
    处理流程：
    1. 检索相关的文本块（chunks）
    2. 过滤低相关度的文本块
    3. 使用所有文本块生成回答
    4. 按文献去重，返回唯一的文献引用（papers）
    
    返回结果：
    - answer: 基于所有相关文本块生成的回答
    - references: 去重后的文献列表（按文献为单位，不是文本块）
    """
    global system_ready, conversations
    
    if not system_ready:
        return jsonify({
            'success': False,
            'error': '系统未初始化，请先初始化系统'
        }), 400
    
    data = request.json
    question = data.get('question', '').strip()
    # 相关度阈值：只保留相似度分数高于此值的文档
    # 分数范围是0-1，0.40表示相关文献（降低阈值以获取更多文献）
    similarity_threshold = data.get('similarity_threshold', 0.40)
    # 输入验证
    try:
        similarity_threshold = float(similarity_threshold)
        if not (0 <= similarity_threshold <= 1):
            raise ValueError
    except (ValueError, TypeError):
        similarity_threshold = 0.40
        
    # 最大检索数量（从所有文档中检索）（增加到100以获取更多文献）
    max_results = data.get('max_results', 100)
    try:
        max_results = int(max_results)
        if max_results <= 0:
            max_results = 100
        if max_results > 200: # 限制上限
            max_results = 200
    except (ValueError, TypeError):
        max_results = 100
    
    app_logger.info(f"收到问答请求: {question[:100]}")
    
    if not question:
        app_logger.warning("问题为空")
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    try:
        start_time = time.time()
        
        # ============================================================
        # 第零步：查询扩展（新增）
        # 扩展同义词和相关术语，提高检索召回率
        # ============================================================
        query_expansion = query_expander.expand_query(question)
        expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
        
        print(f"[查询扩展] 原始: {question}")
        if query_expansion['matched_concepts']:
            print(f"[查询扩展] 匹配概念: {query_expansion['matched_concepts']}")
            print(f"[查询扩展] 扩展术语: {len(query_expansion['expanded_terms'])} 个")
        
        # ============================================================
        # 第一步：检索文本块（chunks）
        # 注意：这里返回的是文本块，不是完整文献
        # 一篇文献可能被分成多个块
        # ============================================================
        retriever = rag_system.index.as_retriever(similarity_top_k=max_results)
        # 使用扩展后的查询进行检索
        retrieved_chunks = retriever.retrieve(expanded_query)  # 明确命名：chunks
        
        print(f"[检索] 检索到 {len(retrieved_chunks)} 个文本块（chunks）")
        
        # ============================================================
        # 第二步：根据相关度阈值过滤文本块
        # ============================================================
        filtered_chunks = []  # 明确命名：chunks
        for chunk in retrieved_chunks:
            chunk_score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            if chunk_score >= similarity_threshold:
                filtered_chunks.append(chunk)
        
        # 如果没有文本块超过阈值，至少保留最相关的3个块
        if len(filtered_chunks) == 0 and len(retrieved_chunks) > 0:
            filtered_chunks = retrieved_chunks[:3]
            print(f"[调整] 没有文本块超过阈值 {similarity_threshold}，保留前 3 个最相关的块")
        
        print(f"[过滤] 过滤后保留 {len(filtered_chunks)} 个文本块（阈值: {similarity_threshold}）")
        
        # ============================================================
        # 第三步：收集所有文本块的内容用于生成回答
        # 注意：这里使用所有相关的文本块，不去重
        # 优化：限制上下文总长度，避免过长的输入
        # ============================================================
        # 先不构建上下文，等确定文献列表后再构建
        
        # ============================================================
        # 第四步：按文献去重（重要！）
        # 目的：将多个文本块合并为唯一的文献引用
        # 策略：同一篇文献只保留相关度最高的块的分数，并收集该文献的所有chunks
        # ============================================================
        unique_papers_dict = {}  # 明确命名：papers（文献）
        
        for chunk in filtered_chunks:
            # 提取文献标识信息
            paper_file_path = chunk.metadata.get('file_path', '')
            paper_filename = chunk.metadata.get('file_name', '未知文档')
            chunk_score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            
            # 使用文件路径作为文献的唯一标识
            if paper_file_path not in unique_papers_dict:
                unique_papers_dict[paper_file_path] = {
                    'file_path': paper_file_path,
                    'filename': paper_filename,
                    'max_score': chunk_score,  # 该文献的最高相关度
                    'chunks': [chunk],  # 收集该文献的所有chunks
                    'sample_content': chunk.text[:200] + '...' if len(chunk.text) > 200 else chunk.text
                }
            else:
                # 更新最高分数
                if chunk_score > unique_papers_dict[paper_file_path]['max_score']:
                    unique_papers_dict[paper_file_path]['max_score'] = chunk_score
                # 添加chunk到列表
                unique_papers_dict[paper_file_path]['chunks'].append(chunk)
        
        # 按相关度排序文献
        unique_papers_list = sorted(
            unique_papers_dict.values(), 
            key=lambda paper: paper['max_score'], 
            reverse=True
        )
        
        print(f"[去重] {len(filtered_chunks)} 个文本块 → {len(unique_papers_list)} 篇唯一文献")
        
        # ============================================================
        # 第五步：构建参考文献列表（按文献为单位）
        # 注意：这里返回的是文献（papers），不是文本块（chunks）
        # ============================================================
        references_raw = []  # 原始文献列表
        
        for paper_index, paper_info in enumerate(unique_papers_list, 1):
            paper_file_path = paper_info['file_path']
            paper_filename = paper_info['filename']
            paper_max_score = paper_info['max_score']
            paper_sample_content = paper_info['sample_content']
            
            # 获取文献的元数据（期刊、年份、标题等）
            paper_metadata = rag_system.metadata_storage.get_metadata(paper_file_path) if paper_file_path else None
            
            if paper_metadata:
                # 有元数据的情况（PDF文献）
                references_raw.append({
                    'ref_id': f'ref_{paper_index}',
                    'journal': paper_metadata.get('journal', 'Unknown Journal'),
                    'year': paper_metadata.get('year', 'N/A'),
                    'title': paper_metadata.get('title', 'Unknown Title'),
                    'authors': paper_metadata.get('authors', []),
                    'doi': paper_metadata.get('doi', 'Not Available'),
                    'filename': paper_filename,
                    'file_path': paper_file_path,  # 添加file_path
                    'score': paper_max_score,  # 该文献的最高相关度
                    'content': paper_sample_content
                })
            else:
                # 没有元数据的情况（如datasets文件）
                is_dataset = 'datasets' in paper_file_path.lower() or 'dataset' in paper_filename.lower()
                references_raw.append({
                    'ref_id': f'ref_{paper_index}',
                    'journal': '营养数据集' if is_dataset else 'Unknown',
                    'year': 'N/A',
                    'title': paper_filename,
                    'authors': [],
                    'doi': 'Not Available',
                    'filename': paper_filename,
                    'file_path': paper_file_path,  # 添加file_path
                    'score': paper_max_score,
                    'content': paper_sample_content
                })
        
        # ============================================================
        # 第五步半：证据分级（新增）
        # 对文献进行质量评估和分级
        # ============================================================
        print(f"[证据分级] 对 {len(references_raw)} 篇文献进行分级...")
        references_ranked = evidence_ranker.rank_papers(references_raw)
        
        # 重新排序：综合考虑相关度和证据质量
        # 策略：相关度权重60%，证据质量权重40%
        for ref in references_ranked:
            ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
        
        references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 重新分配ref_id
        references = []
        for idx, ref in enumerate(references_ranked, 1):
            ref['ref_id'] = f'ref_{idx}'
            references.append(ref)
        
        print(f"[证据分级] 完成，最高质量: Level {references[0]['evidence_level']} ({references[0]['evidence_label']})")
        
        # ============================================================
        # 第六步：构建提示词（关键修复：只使用references中的文献的chunks）
        # 策略：
        # 1. 从unique_papers_dict中获取每篇文献的所有chunks
        # 2. 只使用references中列出的文献
        # 3. 为每个chunk标注正确的ref_id
        # ============================================================
        # 构建file_path到ref的映射
        filepath_to_ref = {}
        for ref in references:
            filepath_to_ref[ref['file_path']] = ref
        
        print(f"[调试] References包含 {len(references)} 篇文献")
        
        # 只使用references中的文献的chunks
        numbered_context_chunks = []
        max_context_length = 12000  # 增加到12000字符以包含更多文献
        total_length = 0
        matched_count = 0
        
        import re
        
        for ref in references:
            ref_file_path = ref['file_path']
            ref_id = ref['ref_id']
            
            # 从unique_papers_dict中获取该文献的所有chunks
            if ref_file_path in unique_papers_dict:
                paper_chunks = unique_papers_dict[ref_file_path]['chunks']
                
                for chunk in paper_chunks:
                    chunk_text = chunk.text
                    
                    # ============================================================
                    # 关键：清理原始文档中可能被误解为ref的内容
                    # 移除类似 [1], [2], [CrossRef], [PubMed] 等标记
                    # ============================================================
                    # 移除方括号内的数字引用 [1], [2], [12]
                    chunk_text = re.sub(r'\[\d+\]', '', chunk_text)
                    # 移除方括号内的CrossRef、PubMed等
                    chunk_text = re.sub(r'\[CrossRef\]|\[PubMed\]|\[Google Scholar\]', '', chunk_text, flags=re.IGNORECASE)
                    # 移除行首的数字编号（如 "9. Author" 或 "46. de Ruyter"）
                    chunk_text = re.sub(r'^\d+\.\s+', '', chunk_text, flags=re.MULTILINE)
                    # 清理多余空格
                    chunk_text = re.sub(r'\s+', ' ', chunk_text).strip()
                    
                    # 检查长度限制
                    if total_length + len(chunk_text) > max_context_length:
                        print(f"[优化] 达到上下文长度限制 {max_context_length} 字符")
                        break
                    
                    # 添加ref标注（这是唯一的ref标记）
                    numbered_chunk = f"[{ref_id}] {chunk_text}"
                    numbered_context_chunks.append(numbered_chunk)
                    total_length += len(chunk_text)
                    matched_count += 1
                
                # 如果达到长度限制，停止添加更多文献
                if total_length >= max_context_length:
                    break
        
        print(f"[上下文] 使用 {len(references)} 篇文献的 {matched_count} 个chunks（共 {total_length} 字符）")
        
        # 构建参考文献列表摘要（用于prompt）
        ref_list_summary = "\n".join([
            f"{ref['ref_id']}: {ref.get('title', ref['filename'])} ({ref.get('journal', 'Unknown')}, {ref.get('year', 'N/A')})"
            for ref in references
        ])
        
        context = "\n\n".join(numbered_context_chunks)
        prompt = f"""你是甜味科学领域的专业知识系统。请基于以下参考文献回答问题。

【参考文献列表】（共{len(references)}篇，编号为ref_1到ref_{len(references)}）：
{ref_list_summary}

【重要】：
- 只能使用ref_1到ref_{len(references)}这些编号
- 在回答的关键信息后用[ref_X]或[ref_X, ref_Y]标注来源
- 不要引用任何其他编号

【参考文献内容】：
{context}

【问题】：{question}

请用中文回答，结构清晰，在重要观点后标注文献来源。"""
        
        # 调用DeepSeek API（流式输出）
        import persistent_storage
        answer = None
        reasoning = None
        max_retries = 3
        retry_delay = 2
        
        if hasattr(persistent_storage, 'deepseek_client'):
            for attempt in range(max_retries):
                try:
                    # 使用流式输出
                    stream = persistent_storage.deepseek_client.chat.completions.create(
                        model=persistent_storage.deepseek_model,
                        messages=[
                            {"role": "system", "content": f"你是甜味科学领域的专业知识系统。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.6,
                        max_tokens=2000,
                        stream=True  # 启用流式输出
                    )
                    
                    # 收集流式响应
                    answer_chunks = []
                    reasoning_chunks = []
                    
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            answer_chunks.append(chunk.choices[0].delta.content)
                        
                        # 检查是否有思维链
                        if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                            reasoning_chunks.append(chunk.choices[0].delta.reasoning_content)
                    
                    answer = ''.join(answer_chunks)
                    reasoning = ''.join(reasoning_chunks) if reasoning_chunks else None
                    
                    # ============================================================
                    # 后处理：清理无效的ref引用
                    # 将不在references列表中的ref编号替换为有效的编号
                    # ============================================================
                    import re
                    valid_ref_ids = {ref['ref_id'] for ref in references}
                    max_ref_num = len(references)
                    
                    def replace_invalid_ref(match):
                        ref_num = int(match.group(1))
                        if f'ref_{ref_num}' in valid_ref_ids:
                            return match.group(0)  # 有效的ref，保持不变
                        else:
                            # 无效的ref，映射到有效范围内
                            mapped_num = ((ref_num - 1) % max_ref_num) + 1
                            return f'[ref_{mapped_num}]'
                    
                    # 替换回答中的无效ref
                    answer = re.sub(r'\[ref_(\d+)\]', replace_invalid_ref, answer)
                    if reasoning:
                        reasoning = re.sub(r'\[ref_(\d+)\]', replace_invalid_ref, reasoning)
                    
                    print(f"[后处理] 清理了回答中的无效ref引用，有效范围: ref_1 到 ref_{max_ref_num}")
                    
                    # 如果有思维链，添加到答案前面
                    if reasoning and len(reasoning.strip()) > 0:
                        answer = f"<details><summary>思维链（点击展开）</summary>\n\n{reasoning}\n\n</details>\n\n---\n\n{answer}"
                    
                    break  # 成功则退出重试循环
                except Exception as api_error:
                    error_str = str(api_error)
                    if '503' in error_str or 'service_unavailable' in error_str.lower():
                        if attempt < max_retries - 1:
                            print(f"[警告] DeepSeek API繁忙，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                        else:
                            answer = f"抱歉，DeepSeek服务当前繁忙，请稍后再试。\n\n基于检索到的文档，我可以提供以下参考信息：\n\n{context[:500]}..."
                    else:
                        raise  # 其他错误直接抛出
        else:
            answer = "DeepSeek API 未配置，无法生成回答。"
        
        end_time = time.time()
        
        # 保存对话
        conversation = {
            'id': len(conversations) + 1,
            'question': question,
            'answer': answer,
            'references': references,
            'timestamp': datetime.now().isoformat(),
            'response_time': round(end_time - start_time, 2)
        }
        conversations.append(conversation)
        
        return jsonify({
            'success': True,
            'answer': answer,
            'references': references,
            'response_time': conversation['response_time']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@app.route('/api/search', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_search():
    """文献元数据搜索（支持中英文互查）"""
    global system_ready
    
    if not system_ready:
        app_logger.warning("搜索请求失败：系统未初始化")
        return jsonify({
            'success': False,
            'error': '系统未初始化'
        }), 400
    
    data = request.json
    query = data.get('query', '').strip()
    
    app_logger.info(f"收到搜索请求: {query}")
    
    if not query:
        app_logger.warning("搜索关键词为空")
        return jsonify({
            'success': False,
            'error': '搜索关键词不能为空'
        }), 400
    
    try:
        # 使用查询扩展器获取同义词和相关术语
        query_expansion = query_expander.expand_query(query)
        
        # 构建搜索关键词列表（原始查询 + 扩展术语）
        search_terms = [query.lower()]
        if query_expansion['expanded_terms']:
            search_terms.extend([term.lower() for term in query_expansion['expanded_terms']])
        
        print(f"[搜索] 原始查询: {query}")
        if query_expansion['matched_concepts']:
            print(f"[搜索] 匹配概念: {query_expansion['matched_concepts']}")
            print(f"[搜索] 扩展术语: {len(query_expansion['expanded_terms'])} 个")
        
        # 获取所有元数据
        all_metadata = rag_system.metadata_storage.get_all_metadata()
        
        # 搜索匹配的文献
        results = []
        seen_files = set()  # 避免重复
        
        for file_path, metadata in all_metadata.items():
            if file_path in seen_files:
                continue
                
            # 搜索字段：标题、作者、期刊、DOI、文件名
            searchable_text = ' '.join([
                metadata.get('title', ''),
                metadata.get('journal', ''),
                metadata.get('doi', ''),
                metadata.get('filename', ''),
                ' '.join(metadata.get('authors', []))
            ]).lower()
            
            # 检查是否匹配任何搜索词
            matched = False
            for term in search_terms:
                if term in searchable_text:
                    matched = True
                    break
            
            if matched:
                seen_files.add(file_path)
                results.append({
                    'title': metadata.get('title', 'Unknown Title'),
                    'authors': metadata.get('authors', []),
                    'journal': metadata.get('journal', 'Unknown Journal'),
                    'year': metadata.get('year', 'N/A'),
                    'doi': metadata.get('doi', 'Not Available'),
                    'filename': metadata.get('filename', ''),
                    'file_path': file_path
                })
        
        # 按年份排序（新的在前）
        results.sort(key=lambda x: x['year'], reverse=True)
        
        print(f"[搜索] 找到 {len(results)} 篇文献")
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'expanded_terms': query_expansion['expanded_terms'][:5] if query_expansion['expanded_terms'] else []
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'搜索失败: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET'])
@handle_api_errors
def api_stats():
    """获取系统统计信息"""
    stats = rag_system.get_stats() if system_ready else {}
    doc_count = stats.get('total_documents', 0)
    
    app_logger.debug(f"返回系统统计: {doc_count} 个文档")
    
    return jsonify({
        'success': True,
        'total_documents': doc_count,
        'total_chunks': doc_count * 10,  # 估算
        'total_conversations': len(conversations),
        'system_ready': system_ready,
        'index_persisted': stats.get('index_exists', False)
    })

@app.route('/api/conversations', methods=['GET'])
@handle_api_errors
def api_conversations():
    """获取对话历史"""
    app_logger.debug(f"返回 {len(conversations)} 条对话历史")
    return jsonify({
        'success': True,
        'conversations': conversations
    })

@app.route('/api/clear_conversations', methods=['POST'])
@handle_api_errors
def api_clear_conversations():
    """清空对话历史"""
    global conversations
    conversations = []
    app_logger.info("对话历史已清空")
    return jsonify({
        'success': True,
        'message': '对话历史已清空'
    })

@app.route('/api/health', methods=['GET'])
def api_health():
    """系统健康检查"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # 检查 RAG 系统
    try:
        stats = rag_system.get_stats()
        health_status['components']['rag_system'] = {
            'status': 'healthy' if system_ready else 'unhealthy',
            'documents': stats.get('total_documents', 0)
        }
    except Exception as e:
        health_status['components']['rag_system'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # 检查 DeepSeek API
    try:
        import persistent_storage
        health_status['components']['deepseek_api'] = {
            'status': 'configured' if hasattr(persistent_storage, 'deepseek_client') else 'not_configured'
        }
    except Exception as e:
        health_status['components']['deepseek_api'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 检查元数据存储
    try:
        metadata_count = len(rag_system.metadata_storage.get_all_metadata())
        health_status['components']['metadata_storage'] = {
            'status': 'healthy',
            'count': metadata_count
        }
    except Exception as e:
        health_status['components']['metadata_storage'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    app_logger.debug(f"健康检查: {health_status['status']}")
    return jsonify(health_status), status_code

@app.route('/api/ask_stream', methods=['POST'])
@handle_api_errors
def api_ask_stream():
    """
    流式问答 API（Server-Sent Events）
    实时返回思维过程和答案
    """
    from flask import Response, stream_with_context
    import json
    
    global system_ready
    
    if not system_ready:
        app_logger.warning("流式问答请求失败：系统未初始化")
        return jsonify({
            'success': False,
            'error': '系统未初始化'
        }), 400
    
    data = request.json
    question = data.get('question', '').strip()
    similarity_threshold = data.get('similarity_threshold', 0.40)  # 降低阈值
    max_results = data.get('max_results', 100)  # 增加到100
    
    app_logger.info(f"收到流式问答请求: {question[:100]}")
    
    if not question:
        app_logger.warning("流式问答问题为空")
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    def generate():
        try:
            import time
            
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始检索文献...'}, ensure_ascii=False)}\n\n"
            
            # 查询扩展
            query_expansion = query_expander.expand_query(question)
            expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
            
            # 检索文本块
            yield f"data: {json.dumps({'type': 'status', 'message': '正在检索相关文献...'}, ensure_ascii=False)}\n\n"
            
            retriever = rag_system.index.as_retriever(similarity_top_k=max_results)
            retrieved_chunks = retriever.retrieve(expanded_query)
            
            # 过滤文本块
            filtered_chunks = [chunk for chunk in retrieved_chunks if float(chunk.score) >= similarity_threshold]
            if len(filtered_chunks) == 0 and len(retrieved_chunks) > 0:
                filtered_chunks = retrieved_chunks[:3]
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'找到 {len(filtered_chunks)} 个相关文本块'}, ensure_ascii=False)}\n\n"
            
            # 构建上下文
            context_chunks = []
            max_context_length = 8000
            total_length = 0
            
            # 先不构建上下文，等确定文献列表后再构建
            
            # 构建参考文献列表（按文献去重）
            unique_papers_dict = {}
            for chunk in filtered_chunks:
                paper_file_path = chunk.metadata.get('file_path', '')
                paper_filename = chunk.metadata.get('file_name', '未知文档')
                chunk_score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
                
                if paper_file_path not in unique_papers_dict:
                    unique_papers_dict[paper_file_path] = {
                        'file_path': paper_file_path,
                        'filename': paper_filename,
                        'max_score': chunk_score,
                        'chunks': [chunk],  # 收集该文献的所有chunks
                        'sample_content': chunk.text[:200] + '...' if len(chunk.text) > 200 else chunk.text
                    }
                else:
                    if chunk_score > unique_papers_dict[paper_file_path]['max_score']:
                        unique_papers_dict[paper_file_path]['max_score'] = chunk_score
                    unique_papers_dict[paper_file_path]['chunks'].append(chunk)
            
            unique_papers_list = sorted(unique_papers_dict.values(), key=lambda paper: paper['max_score'], reverse=True)
            
            print(f"[流式API-去重] {len(filtered_chunks)} 个文本块 → {len(unique_papers_list)} 篇唯一文献")
            yield f"data: {json.dumps({'type': 'status', 'message': f'去重后找到 {len(unique_papers_list)} 篇唯一文献'}, ensure_ascii=False)}\n\n"
            
            # 构建参考文献
            references_raw = []
            for paper_index, paper_info in enumerate(unique_papers_list, 1):
                # 将绝对路径转换为相对路径
                file_path = paper_info['file_path']
                original_path = file_path
                if file_path.startswith('/'):
                    # 提取相对路径部分
                    import os
                    file_path = os.path.relpath(file_path, os.getcwd())
                
                # 调试：打印路径信息
                print(f"[调试] 原始路径: {original_path}")
                print(f"[调试] 转换后路径: {file_path}")
                
                paper_metadata = rag_system.metadata_storage.get_metadata(file_path) if file_path else None
                
                # 调试：打印元数据获取结果
                if paper_metadata:
                    print(f"[调试] ✅ 找到元数据: {paper_metadata.get('title', 'N/A')[:50]}")
                else:
                    print(f"[调试] ❌ 未找到元数据")
                
                if paper_metadata:
                    references_raw.append({
                        'ref_id': f'ref_{paper_index}',
                        'journal': paper_metadata.get('journal', 'Unknown Journal'),
                        'year': paper_metadata.get('year', 'N/A'),
                        'title': paper_metadata.get('title', 'Unknown Title'),
                        'authors': paper_metadata.get('authors', []),
                        'doi': paper_metadata.get('doi', 'Not Available'),
                        'filename': paper_info['filename'],
                        'file_path': paper_info['file_path'],  # 添加file_path
                        'score': paper_info['max_score'],
                        'content': paper_info['sample_content']
                    })
                else:
                    # 没有元数据的情况
                    is_dataset = 'datasets' in file_path.lower() or 'dataset' in paper_info['filename'].lower()
                    references_raw.append({
                        'ref_id': f'ref_{paper_index}',
                        'journal': '营养数据集' if is_dataset else 'Unknown',
                        'year': 'N/A',
                        'title': paper_info['filename'],
                        'authors': [],
                        'doi': 'Not Available',
                        'filename': paper_info['filename'],
                        'file_path': paper_info['file_path'],  # 添加file_path
                        'score': paper_info['max_score'],
                        'content': paper_info['sample_content']
                    })
            
            # 证据分级
            references_ranked = evidence_ranker.rank_papers(references_raw)
            for ref in references_ranked:
                ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
            references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
            
            references = []
            for idx, ref in enumerate(references_ranked, 1):
                ref['ref_id'] = f'ref_{idx}'
                references.append(ref)
            
            print(f"[流式API-证据分级] 完成，共 {len(references)} 篇文献")
            
            # 准备发送给前端的references数据（只包含必要字段）
            references_for_frontend = []
            for ref in references:
                references_for_frontend.append({
                    'ref_id': ref['ref_id'],
                    'title': ref.get('title', ref.get('filename', 'Unknown')),
                    'journal': ref.get('journal', 'Unknown'),
                    'year': ref.get('year', 'N/A'),
                    'authors': ref.get('authors', []),
                    'doi': ref.get('doi', 'Not Available'),
                    'filename': ref.get('filename', ''),
                    'score': ref.get('final_score', 0)
                })
            
            # 发送参考文献
            yield f"data: {json.dumps({'type': 'references', 'references': references_for_frontend}, ensure_ascii=False)}\n\n"
            
            # 开始生成答案
            yield f"data: {json.dumps({'type': 'status', 'message': '正在生成答案...'}, ensure_ascii=False)}\n\n"
            
            # 构建上下文：只使用references中的文献的chunks
            numbered_context_chunks = []
            max_context_length = 12000  # 增加到12000字符
            total_length = 0
            matched_count = 0
            
            import re
            
            for ref in references:
                ref_file_path = ref['file_path']
                ref_id = ref['ref_id']
                
                # 从unique_papers_dict中获取该文献的所有chunks
                if ref_file_path in unique_papers_dict:
                    paper_chunks = unique_papers_dict[ref_file_path]['chunks']
                    
                    for chunk in paper_chunks:
                        chunk_text = chunk.text
                        
                        # ============================================================
                        # 关键：清理原始文档中可能被误解为ref的内容
                        # ============================================================
                        # 移除方括号内的数字引用 [1], [2], [12]
                        chunk_text = re.sub(r'\[\d+\]', '', chunk_text)
                        # 移除方括号内的CrossRef、PubMed等
                        chunk_text = re.sub(r'\[CrossRef\]|\[PubMed\]|\[Google Scholar\]', '', chunk_text, flags=re.IGNORECASE)
                        # 移除行首的数字编号（如 "9. Author"）
                        chunk_text = re.sub(r'^\d+\.\s+', '', chunk_text, flags=re.MULTILINE)
                        # 清理多余空格
                        chunk_text = re.sub(r'\s+', ' ', chunk_text).strip()
                        
                        # 检查长度限制
                        if total_length + len(chunk_text) > max_context_length:
                            break
                        
                        # 添加ref标注（这是唯一的ref标记）
                        numbered_chunk = f"[{ref_id}] {chunk_text}"
                        numbered_context_chunks.append(numbered_chunk)
                        total_length += len(chunk_text)
                        matched_count += 1
                    
                    # 如果达到长度限制，停止添加更多文献
                    if total_length >= max_context_length:
                        break
            
            print(f"[流式API-上下文] 使用 {len(references)} 篇文献的 {matched_count} 个chunks（共 {total_length} 字符）")
            
            # 构建参考文献列表摘要（用于prompt）
            ref_list_summary = "\n".join([
                f"{ref['ref_id']}: {ref.get('title', ref['filename'])} ({ref.get('journal', 'Unknown')}, {ref.get('year', 'N/A')})"
                for ref in references
            ])
            
            context = "\n\n".join(numbered_context_chunks)
            prompt = f"""你是甜味科学领域的专业知识系统。请基于以下参考文献回答问题。

【参考文献列表】（共{len(references)}篇，编号为ref_1到ref_{len(references)}）：
{ref_list_summary}

【重要】：
- 只能使用ref_1到ref_{len(references)}这些编号
- 在回答的关键信息后用[ref_X]或[ref_X, ref_Y]标注来源
- 不要引用任何其他编号

【参考文献内容】：
{context}

【问题】：{question}

请用中文回答，结构清晰，在重要观点后标注文献来源。"""
            
            # 流式调用 DeepSeek API
            import persistent_storage
            
            if hasattr(persistent_storage, 'deepseek_client'):
                stream = persistent_storage.deepseek_client.chat.completions.create(
                    model=persistent_storage.deepseek_model,
                    messages=[
                        {"role": "system", "content": f"你是甜味科学领域的专业知识系统。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=2000,
                    stream=True
                )
                
                reasoning_started = False
                answer_started = False
                
                for chunk in stream:
                    # 处理思维链
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        if not reasoning_started:
                            yield f"data: {json.dumps({'type': 'reasoning_start'}, ensure_ascii=False)}\n\n"
                            reasoning_started = True
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.choices[0].delta.reasoning_content}, ensure_ascii=False)}\n\n"
                    
                    # 处理答案
                    if chunk.choices[0].delta.content:
                        if not answer_started:
                            if reasoning_started:
                                yield f"data: {json.dumps({'type': 'reasoning_end'}, ensure_ascii=False)}\n\n"
                            
                            # 在开始回答前发送references
                            yield f"data: {json.dumps({'type': 'references', 'references': references}, ensure_ascii=False)}\n\n"
                            
                            yield f"data: {json.dumps({'type': 'answer_start'}, ensure_ascii=False)}\n\n"
                            answer_started = True
                        yield f"data: {json.dumps({'type': 'answer', 'content': chunk.choices[0].delta.content}, ensure_ascii=False)}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("SweetSeek 启动中...")
    print("=" * 50)
    
    try:
        # 验证配置
        app_logger.info("开始配置验证...")
        validate_config()
        
        # 自动初始化系统
        app_logger.info("正在初始化RAG系统...")
        initialize_rag_system()
        
        # 从环境变量获取配置
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5001))
        debug = os.getenv('DEBUG', 'True').lower() == 'true'
        
        print("\n" + "=" * 50)
        print("✅ 服务器启动成功")
        print(f"访问地址: http://localhost:{port}")
        print(f"健康检查: http://localhost:{port}/api/health")
        print("停止服务: 按 Ctrl+C")
        print("=" * 50 + "\n")
        
        app_logger.info(f"服务器启动在 {host}:{port}")
        
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        app_logger.error(f"❌ 启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)
