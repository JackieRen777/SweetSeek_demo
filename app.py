#!/usr/bin/env python3
"""
SweetSeek - Flask Backend
AI-powered research Q&A system
"""

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
from datetime import datetime
from persistent_storage import rag_system
from query_expander import SweetnessQueryExpander
from evidence_ranker import EvidenceRanker
import logging
from functools import wraps
import traceback
import sys
from config import config
from logger import setup_logger
from services.dependencies import build_services

# NOTE: 文件中的函数多数通过 Flask 的 @app.route 装饰器在运行时被调用。
# 静态分析工具（如 vulture）会将这些运行时注册的路由误判为未使用，
# 所以请在复核 vulture 输出时忽略此文件中的路由标记。

app_logger = setup_logger('sweetseek')

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
    missing_vars = []
    if not config.DEEPSEEK_API_KEY:
        missing_vars.append('DEEPSEEK_API_KEY')
    if not config.DEEPSEEK_BASE_URL:
        missing_vars.append('DEEPSEEK_BASE_URL')
    if not config.DEEPSEEK_MODEL:
        missing_vars.append('DEEPSEEK_MODEL')

    if missing_vars:
        raise ValueError(f"缺少必需的配置: {', '.join(missing_vars)}")
    
    app_logger.info("✅ 配置验证通过")

app = Flask(__name__)
CORS(app)

# 全局变量
system_ready = False
conversations = []

services = build_services()
query_expander = services.query_expander
evidence_ranker = services.evidence_ranker
llm_client = services.llm_client
compound_service = services.compound_service
chat_service = services.chat_service

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
    """主页 - 返回前端入口"""
    dist_dir = os.path.join(os.path.dirname(__file__), 'frontend-react', 'dist')
    if os.path.exists(os.path.join(dist_dir, 'index.html')):
        return send_from_directory(dist_dir, 'index.html')
    return jsonify({
        'message': 'SweetSeek Backend API is running',
        'version': '1.0.0',
        'docs': '/api/health'
    })

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    dist_dir = os.path.join(os.path.dirname(__file__), 'frontend-react', 'dist', 'assets')
    return send_from_directory(dist_dir, filename)

@app.route('/<path:path>')
def serve_static_proxy(path):
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
        
    dist_dir = os.path.join(os.path.dirname(__file__), 'frontend-react', 'dist')
    
    if os.path.exists(os.path.join(dist_dir, path)):
        return send_from_directory(dist_dir, path)
        
    # SPA Fallback
    if '.' not in os.path.basename(path) and os.path.exists(os.path.join(dist_dir, 'index.html')):
        return send_from_directory(dist_dir, 'index.html')
        
    return jsonify({'error': 'Not Found'}), 404

@app.route('/api/structure/render', methods=['GET'])
@handle_api_errors
def api_render_structure():
    """根据SMILES生成分子结构图"""
    smiles = request.args.get('smiles', '').strip()
    width = request.args.get('width', 400, type=int)
    height = request.args.get('height', 400, type=int)
    
    if not smiles:
        return jsonify({'success': False, 'error': 'SMILES不能为空'}), 400
        
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        import io
        from flask import send_file
        
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            # Try to handle common issues or just fail
            return jsonify({'success': False, 'error': '无效的SMILES字符串'}), 400
            
        # Generate image
        img = Draw.MolToImage(mol, size=(width, height))
        
        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    except ImportError:
        return jsonify({'success': False, 'error': 'RDKit未安装'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/compounds/search', methods=['GET', 'POST'])
@handle_api_errors
@monitor_performance
def api_search_compounds():
    """搜索化合物"""
    if request.method == 'POST':
        data = request.json
        query = data.get('query', '').strip()
        limit = data.get('limit', 5)
    else:
        query = request.args.get('query', '').strip()
        limit = request.args.get('limit', 5, type=int)
    
    if not query:
        return jsonify({
            'success': False,
            'error': '搜索关键词不能为空'
        }), 400
        
    try:
        results = compound_service.search(query, limit=limit)
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'搜索化合物失败: {str(e)}'
        }), 500

@app.route('/api/compounds/stats', methods=['GET'])
@handle_api_errors
def api_compound_stats():
    """获取化合物数据库统计信息"""
    stats = compound_service.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })

@app.route('/api/compounds/<int:compound_id>', methods=['GET'])
@handle_api_errors
def api_get_compound(compound_id):
    """获取化合物详情"""
    compound = compound_service.get_by_id(compound_id)
    if compound:
        return jsonify({
            'success': True,
            'data': compound
        })
    else:
        return jsonify({
            'success': False,
            'error': '未找到该化合物'
        }), 404

@app.route('/api/compounds', methods=['GET'])
@handle_api_errors
def api_list_compounds():
    """获取化合物列表"""
    limit = request.args.get('limit', 100, type=int)
    compounds = compound_service.get_all(limit=limit)
    return jsonify({
        'success': True,
        'data': compounds,
        'count': len(compounds)
    })

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
    """
    if not system_ready:
        return jsonify({
            'success': False,
            'error': '系统未初始化，请先初始化系统'
        }), 400
    
    data = request.json
    question = data.get('question', '').strip()
    similarity_threshold = data.get('similarity_threshold', config.RAG_SIMILARITY_THRESHOLD)
    
    try:
        similarity_threshold = float(similarity_threshold)
        if not (0 <= similarity_threshold <= 1):
            raise ValueError
    except (ValueError, TypeError):
        similarity_threshold = config.RAG_SIMILARITY_THRESHOLD
        
    max_results = data.get('max_results', config.RAG_MAX_RESULTS)
    try:
        max_results = int(max_results)
        if max_results < 1:
            raise ValueError
        if max_results > 200:
            max_results = 200
    except (ValueError, TypeError):
        max_results = config.RAG_MAX_RESULTS
    
    if not question:
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    result = chat_service.ask(question, similarity_threshold, max_results)
    return jsonify(result)

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
        'total_conversations': len(chat_service.get_conversations()),
        'system_ready': system_ready,
        'index_persisted': stats.get('index_exists', False)
    })

@app.route('/api/conversations', methods=['GET'])
@handle_api_errors
def api_conversations():
    """获取对话历史"""
    conversations = chat_service.get_conversations()
    app_logger.debug(f"返回 {len(conversations)} 条对话历史")
    return jsonify({
        'success': True,
        'conversations': conversations
    })

@app.route('/api/clear_conversations', methods=['POST'])
@handle_api_errors
def api_clear_conversations():
    """清空对话历史"""
    chat_service.clear_conversations()
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
        if not hasattr(persistent_storage, 'deepseek_client') and hasattr(persistent_storage, "configure_llm"):
            persistent_storage.configure_llm()
            
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
    
    if not system_ready:
        return jsonify({
            'success': False,
            'error': '系统未初始化'
        }), 400
    
    data = request.json
    question = data.get('question', '').strip()
    similarity_threshold = data.get('similarity_threshold', config.RAG_SIMILARITY_THRESHOLD)
    try:
        similarity_threshold = float(similarity_threshold)
        if not (0 <= similarity_threshold <= 1):
            raise ValueError
    except (ValueError, TypeError):
        similarity_threshold = config.RAG_SIMILARITY_THRESHOLD

    max_results = data.get('max_results', config.RAG_MAX_RESULTS)
    try:
        max_results = int(max_results)
        if max_results < 1:
            raise ValueError
        if max_results > 200:
            max_results = 200
    except (ValueError, TypeError):
        max_results = config.RAG_MAX_RESULTS
    
    if not question:
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    return Response(stream_with_context(chat_service.ask_stream(question, similarity_threshold, max_results)), mimetype='text/event-stream') 

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    # 兼容旧路径，或直接返回404
    return jsonify({'error': 'Static files not served by backend'}), 404

# 自动初始化（针对 Gunicorn 等 WSGI 容器）
if __name__ != '__main__':
    try:
        app_logger.info("检测到非主程序运行模式，尝试初始化 RAG 系统...")
        initialize_rag_system()
    except Exception as e:
        app_logger.error(f"自动初始化失败: {e}")

if __name__ == '__main__':
    # 优先从环境变量读取端口，默认为 5001
    port = int(os.environ.get('PORT', config.PORT))
    
    print("SweetSeek 启动中...")
    print("=" * 50)
    
    try:
        # 验证配置
        app_logger.info("开始配置验证...")
        validate_config()
        
        # 自动初始化系统
        app_logger.info("正在初始化RAG系统...")
        initialize_rag_system()
        
        host = config.HOST
        # port = config.PORT # Removed to use local variable
        debug = config.DEBUG
        
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
