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
from upload_handler import uploader
from persistent_storage import rag_system

# NOTE: 文件中的函数多数通过 Flask 的 @app.route 装饰器在运行时被调用。
# 静态分析工具（如 vulture）会将这些运行时注册的路由误判为未使用，
# 所以请在复核 vulture 输出时忽略此文件中的路由标记。

# 加载环境变量
load_dotenv()

app = Flask(__name__, 
            template_folder='frontend',
            static_folder='static')
CORS(app)

# 全局变量
system_ready = False
conversations = []

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

@app.route('/management.html')
def management():
    """文献管理页面"""
    return render_template('management.html')

@app.route('/about.html')
def about():
    """关于页面"""
    return render_template('about.html')

@app.route('/upload.html')
def upload():
    """文献上传页面"""
    return render_template('upload.html')

# API路由
def reload_documents():
    """重新加载文档并构建索引"""
    global system_ready
    
    print("[系统] 重新构建索引...")
    
    # 重建索引（会删除旧索引并重新构建）
    success = rag_system.rebuild_index()
    
    if success:
        system_ready = True
        stats = rag_system.get_stats()
        print(f"[成功] 索引重建完成，文档数: {stats['total_documents']}")
    else:
        system_ready = False
        print("[失败] 索引重建失败")

@app.route('/api/upload', methods=['POST'])
def upload_documents():
    """上传文档API - 使用增量索引"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    category = request.form.get('category', 'papers')
    use_incremental = request.form.get('incremental', 'true').lower() == 'true'
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
    # 上传文件
    results = uploader.upload_multiple_files(files, category)
    
    # 检查是否有成功上传的文件
    success_count = sum(1 for r in results if r['success'])
    
    if success_count > 0:
        try:
            if use_incremental and success_count <= 20:
                # 使用增量索引（快速）
                print(f"[增量索引] 处理 {success_count} 个新文件...")
                from incremental_indexer import IncrementalIndexer
                indexer = IncrementalIndexer()
                indexer.add_new_documents()
                print("[增量索引] 完成")
            else:
                # 全量重建（文件太多时）
                print(f"[全量重建] 处理 {success_count} 个文件...")
                reload_documents()
                print("[全量重建] 完成")
            
            return jsonify({
                'success': True,
                'message': f'成功上传 {success_count} 个文件',
                'method': 'incremental' if use_incremental and success_count <= 20 else 'full_rebuild',
                'results': results
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'文件上传成功但索引更新失败: {str(e)}'
            }), 500
    else:
        return jsonify({
            'success': False,
            'error': '所有文件上传失败',
            'results': results
        }), 400

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """获取文档列表"""
    documents = uploader.list_documents()
    return jsonify({
        'success': True,
        'documents': documents,
        'total': sum(len(docs) for docs in documents.values())
    })

@app.route('/api/documents/<category>/<filename>', methods=['DELETE'])
def delete_document(category, filename):
    """删除文档"""
    result = uploader.delete_document(filename, category)
    
    if result['success']:
        try:
            reload_documents()
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'文件删除成功但索引重建失败: {str(e)}'
            }), 500
    else:
        return jsonify(result), 400

@app.route('/api/init', methods=['POST'])
def api_init():
    """初始化系统"""
    global system_ready
    
    if system_ready:
        stats = rag_system.get_stats()
        return jsonify({
            'success': True,
            'message': '系统已经初始化',
            'documents_count': stats['total_documents']
        })
    
    success = initialize_rag_system()
    stats = rag_system.get_stats() if success else {}
    
    return jsonify({
        'success': success,
        'message': '系统初始化成功' if success else '系统初始化失败',
        'documents_count': stats.get('total_documents', 0)
    })

@app.route('/api/ask', methods=['POST'])
def api_ask():
    """处理问答请求"""
    global system_ready, conversations
    
    if not system_ready:
        return jsonify({
            'success': False,
            'error': '系统未初始化，请先初始化系统'
        }), 400
    
    data = request.json
    question = data.get('question', '').strip()
    # 相关度阈值：只保留相似度分数高于此值的文档
    # 分数范围是0-1，0.38表示高质量相关文献
    similarity_threshold = data.get('similarity_threshold', 0.38)
    # 最大检索数量（从所有文档中检索）
    max_results = data.get('max_results', 50)
    
    if not question:
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    try:
        start_time = time.time()
        
        # 检索文档
        retriever = rag_system.index.as_retriever(similarity_top_k=max_results)
        nodes = retriever.retrieve(question)
        
        # 根据相关度阈值过滤文档（不限制数量）
        filtered_nodes = []
        for node in nodes:
            score = float(node.score) if hasattr(node, 'score') else 0.0
            if score >= similarity_threshold:
                filtered_nodes.append(node)
        
        # 如果没有文档超过阈值，至少保留最相关的3篇
        if len(filtered_nodes) == 0 and len(nodes) > 0:
            filtered_nodes = nodes[:3]
            print(f"[调整] 没有文档超过阈值 {similarity_threshold}，保留前 3 篇最相关的")
        
        print(f"[检索] 原始: {len(nodes)} 篇, 过滤后: {len(filtered_nodes)} 篇 (阈值: {similarity_threshold})")
        
        # 提取参考文档（增强版，包含元数据）
        references = []
        context_texts = []
        for idx, node in enumerate(filtered_nodes, 1):
            file_path = node.metadata.get('file_path', '')
            filename = node.metadata.get('file_name', '未知文档')
            
            # 获取元数据
            metadata = rag_system.metadata_storage.get_metadata(file_path) if file_path else None
            
            if metadata:
                # 有元数据的情况（PDF文件）
                references.append({
                    'ref_id': f'ref_{idx}',
                    'journal': metadata.get('journal', 'Unknown Journal'),
                    'year': metadata.get('year', 'N/A'),
                    'title': metadata.get('title', 'Unknown Title'),
                    'authors': metadata.get('authors', []),
                    'doi': metadata.get('doi', 'Not Available'),
                    'filename': filename,
                    'score': float(node.score) if hasattr(node, 'score') else 0.0,
                    'content': node.text[:200] + '...' if len(node.text) > 200 else node.text
                })
            else:
                # 没有元数据的情况（如datasets文件）
                is_dataset = 'datasets' in file_path.lower() or 'dataset' in filename.lower()
                references.append({
                    'ref_id': f'ref_{idx}',
                    'journal': '营养数据集' if is_dataset else 'Unknown',
                    'year': 'N/A',
                    'title': filename,
                    'authors': [],
                    'doi': 'Not Available',
                    'filename': filename,
                    'score': float(node.score) if hasattr(node, 'score') else 0.0,
                    'content': node.text[:200] + '...' if len(node.text) > 200 else node.text
                })
            
            context_texts.append(node.text)
        
        # 构建提示词
        context = "\n\n".join(context_texts)
        prompt = f"""基于以下参考文档回答问题。如果文档中没有相关信息，请说明无法从提供的文档中找到答案。

参考文档：
{context}

问题：{question}

请用中文回答："""
        
        # 调用DeepSeek API（带重试机制）
        import persistent_storage
        answer = None
        max_retries = 3
        retry_delay = 2
        
        if hasattr(persistent_storage, 'deepseek_client'):
            for attempt in range(max_retries):
                try:
                    response = persistent_storage.deepseek_client.chat.completions.create(
                        model=persistent_storage.deepseek_model,
                        messages=[
                            {"role": "system", "content": "你是一个高度智能的AI，专门提供关于甜味领域的深入、准确和详细的回答。你的知识涵盖甜味剂、味觉感知、食品化学以及甜味科学的各个方面，能够解答从基础概念到前沿研究的问题，特别是在食品科学与工程中的甜味物理化学原理。\n\n重要原则：\n1. 你必须严格基于提供的参考文档回答问题，不得编造或使用文档外的信息\n2. 如果参考文档中没有相关信息，请明确说明\"根据当前数据库中的文献，暂无相关信息\"\n3. 回答时应引用具体的研究发现，并说明来源\n4. 将复杂的术语解释得通俗易懂，适合不同水平的用户\n5. 提供简洁明了、证据充分且上下文适配的答案，既适合学术研究，也适合一般用户的好奇心"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    answer = response.choices[0].message.content
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
def api_search():
    """文献搜索"""
    global system_ready
    
    if not system_ready:
        return jsonify({
            'success': False,
            'error': '系统未初始化'
        }), 400
    
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': '搜索关键词不能为空'
        }), 400
    
    try:
        # 获取查询引擎
        query_engine = rag_system.get_query_engine()
        
        # 使用RAG引擎检索相关文档
        response = query_engine.query(query)
        
        results = []
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                results.append({
                    'title': node.metadata.get('file_name', '未知文档'),
                    'content': node.text[:300] + '...' if len(node.text) > 300 else node.text,
                    'score': float(node.score) if hasattr(node, 'score') else 0.0,
                    'metadata': node.metadata
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'搜索失败: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """获取系统统计信息"""
    stats = rag_system.get_stats() if system_ready else {}
    doc_count = stats.get('total_documents', 0)
    
    return jsonify({
        'success': True,
        'total_documents': doc_count,
        'total_chunks': doc_count * 10,  # 估算
        'total_conversations': len(conversations),
        'system_ready': system_ready,
        'index_persisted': stats.get('index_exists', False)
    })

@app.route('/api/conversations', methods=['GET'])
def api_conversations():
    """获取对话历史"""
    return jsonify({
        'success': True,
        'conversations': conversations
    })

@app.route('/api/clear_conversations', methods=['POST'])
def api_clear_conversations():
    """清空对话历史"""
    global conversations
    conversations = []
    return jsonify({
        'success': True,
        'message': '对话历史已清空'
    })

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("SweetSeek 启动中...")
    print("=" * 50)
    
    # 自动初始化系统
    print("正在初始化RAG系统...")
    initialize_rag_system()
    
    print("\n" + "=" * 50)
    print("服务器启动成功")
    print("访问地址: http://localhost:5001")
    print("停止服务: 按 Ctrl+C")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
