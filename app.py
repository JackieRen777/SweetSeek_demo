#!/usr/bin/env python3
"""
SweetSeek - Flask Backend
AI-powered research Q&A system
"""

# macOS ARM64: PyTorch (MPS) and SHAP/sklearn each ship their own libomp.dylib.
# Loading SHAP inside the same process as PyTorch causes a SIGSEGV unless we
# allow OpenMP duplicates. Must run before any numpy/torch/sklearn import.
import os as _os
_os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_os.environ.setdefault("OMP_NUM_THREADS", "1")
_os.environ.setdefault("MKL_NUM_THREADS", "1")
_os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
_os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
_os.environ.setdefault("KMP_BLOCKTIME", "0")

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import time
from datetime import datetime
from pathlib import Path
from persistent_storage import rag_system
from query_expander import SweetnessQueryExpander, DualProteinQueryExpander, ProteoglycanQueryExpander
from evidence_ranker import EvidenceRanker
import logging
from functools import wraps
import traceback
import threading
from config import config
from logger import setup_logger
from services.dependencies import build_services
from knowledge_paths import get_domain_paths

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

from services.md_builder_api import InMemoryUploadRequest
app.request_class = InMemoryUploadRequest

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"success": False, "error": "Request exceeds the 20 MB upload limit"}), 413

def _parse_csv_env(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]

_cors_allow_all = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"
if _cors_allow_all:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    default_origins = ",".join([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://sweetseek.top",
        "https://www.sweetseek.top",
    ])
    allowed_origins = _parse_csv_env(os.getenv("CORS_ALLOWED_ORIGINS", default_origins))
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})


def _get_json_dict() -> dict:
    """Safely parse JSON body and always return a dict."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def _parse_retrieval_params(data: dict, default_threshold: float, default_max_results: int) -> tuple[float, int]:
    similarity_threshold = data.get('similarity_threshold', default_threshold)
    try:
        similarity_threshold = float(similarity_threshold)
        if not (0 <= similarity_threshold <= 1):
            raise ValueError
    except (ValueError, TypeError):
        similarity_threshold = default_threshold

    max_results = data.get('max_results', default_max_results)
    try:
        max_results = int(max_results)
        if max_results < 1:
            raise ValueError
        if max_results > 200:
            max_results = 200
    except (ValueError, TypeError):
        max_results = default_max_results

    return similarity_threshold, max_results

# 全局变量
system_ready = False
dual_protein_system_ready = False
dual_protein_initializing = False
dual_protein_docs_count_cache = 0
dual_protein_dim_fix_lock = threading.Lock()
dual_protein_last_dim_fix_ts = 0.0
main_rag_initializing = False
rag_load_lock = threading.Lock()
main_rag_init_lock = threading.Lock()
conversations = []

services = build_services()
query_expander = services.query_expander
evidence_ranker = services.evidence_ranker
llm_client = services.llm_client
compound_service = services.compound_service
chat_service = services.chat_service

from services.md_builder_api import create_md_builder_blueprint
app.register_blueprint(create_md_builder_blueprint(lambda: llm_client))
from services.docking_api import create_docking_blueprint
app.register_blueprint(create_docking_blueprint())

# 双蛋白 RAG 系统（独立实例）
from persistent_storage import PersistentRAGSystem
from services.chat_service import ChatService
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DUAL_PROTEIN_PATHS = get_domain_paths("dual_protein")
DUAL_PROTEIN_METADATA_PATH = str(DUAL_PROTEIN_PATHS.metadata)
dual_protein_rag = PersistentRAGSystem(
    data_dir=str(DUAL_PROTEIN_PATHS.papers),
    persist_dir=str(DUAL_PROTEIN_PATHS.index),
    metadata_path=DUAL_PROTEIN_METADATA_PATH,
)
dual_protein_chat_service = ChatService(
    rag_system=dual_protein_rag,
    query_expander=DualProteinQueryExpander(),
    evidence_ranker=evidence_ranker,
    llm_client=llm_client,
    mode="dual",
)

ENCAPSULATION_PATHS = get_domain_paths("encapsulation")
ENCAPSULATION_DATA_DIR = str(ENCAPSULATION_PATHS.papers)
ENCAPSULATION_PERSIST_DIR = str(ENCAPSULATION_PATHS.index)
ENCAPSULATION_METADATA_PATH = str(ENCAPSULATION_PATHS.metadata)

# Encapsulation（包埋）独立知识域：与现有 Sweetness/Dual-Protein 索引隔离。
encapsulation_system_ready = False
encapsulation_initializing = False
encapsulation_rag = PersistentRAGSystem(
    data_dir=ENCAPSULATION_DATA_DIR,
    persist_dir=ENCAPSULATION_PERSIST_DIR,
    metadata_path=ENCAPSULATION_METADATA_PATH,
)
encapsulation_chat_service = ChatService(
    rag_system=encapsulation_rag,
    query_expander=DualProteinQueryExpander(),
    evidence_ranker=evidence_ranker,
    llm_client=llm_client,
    mode="encapsulation",
)

def initialize_encapsulation_rag():
    global encapsulation_system_ready, encapsulation_initializing
    if encapsulation_initializing:
        return encapsulation_system_ready
    encapsulation_initializing = True
    try:
        with rag_load_lock:
            encapsulation_system_ready = bool(encapsulation_rag.load_or_create_index())
        return encapsulation_system_ready
    except Exception as exc:
        app_logger.error(f"Encapsulation 初始化失败: {exc}")
        encapsulation_system_ready = False
        return False
    finally:
        encapsulation_initializing = False

PROTEOGLYCAN_PATHS = get_domain_paths("proteoglycan")
PROTEOGLYCAN_DATA_DIR = str(PROTEOGLYCAN_PATHS.papers)
PROTEOGLYCAN_PERSIST_DIR = str(PROTEOGLYCAN_PATHS.index)
PROTEOGLYCAN_METADATA_PATH = str(PROTEOGLYCAN_PATHS.metadata)
PROTEOGLYCAN_EMPTY_MESSAGE = "Proteoglycan 知识库尚未建立，请先导入 PDF 并构建索引"

proteoglycan_system_ready = False
proteoglycan_initializing = False
proteoglycan_rag = PersistentRAGSystem(
    data_dir=PROTEOGLYCAN_DATA_DIR,
    persist_dir=PROTEOGLYCAN_PERSIST_DIR,
    metadata_path=PROTEOGLYCAN_METADATA_PATH,
    allow_auto_build=False,
)
proteoglycan_chat_service = ChatService(
    rag_system=proteoglycan_rag,
    query_expander=ProteoglycanQueryExpander(),
    evidence_ranker=evidence_ranker,
    llm_client=llm_client,
    mode="proteoglycan",
)

def proteoglycan_index_exists() -> bool:
    current = Path(PROTEOGLYCAN_PERSIST_DIR) / "current"
    if all((current / name).is_file() for name in ("index.faiss", "index.ids.txt", "metadata.db")):
        return True
    required = ("docstore.json", "index_store.json", "default__vector_store.json")
    return all(os.path.isfile(os.path.join(PROTEOGLYCAN_PERSIST_DIR, name)) for name in required)

def initialize_proteoglycan_rag():
    global proteoglycan_system_ready, proteoglycan_initializing
    if proteoglycan_initializing:
        return proteoglycan_system_ready
    if not proteoglycan_index_exists():
        proteoglycan_system_ready = False
        return False
    proteoglycan_initializing = True
    try:
        with rag_load_lock:
            proteoglycan_system_ready = bool(proteoglycan_rag.load_existing_index())
        return proteoglycan_system_ready
    except Exception as exc:
        app_logger.error(f"Proteoglycan 初始化失败: {exc}")
        proteoglycan_system_ready = False
        return False
    finally:
        proteoglycan_initializing = False

def initialize_rag_system():
    """初始化RAG系统（使用持久化存储）"""
    global system_ready, main_rag_initializing

    try:
        main_rag_initializing = True
        print("[系统] 初始化RAG系统...")

        # 启动时自动迁移元数据路径（绝对→相对）
        try:
            rag_system.metadata_storage.migrate_to_relative_paths()
        except Exception as e:
            app_logger.warning(f"元数据路径迁移跳过: {e}")

        # 加载或创建索引（自动使用持久化）
        with rag_load_lock:
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
    finally:
        main_rag_initializing = False


def start_main_rag_initialization() -> str:
    """Start exactly one background initialization and return its state."""
    global main_rag_initializing

    if system_ready:
        return "ready"

    with main_rag_init_lock:
        if main_rag_initializing:
            return "initializing"
        # Set the flag before starting the thread so concurrent requests cannot
        # enqueue multiple expensive index loads.
        main_rag_initializing = True

        def _initialize() -> None:
            initialize_rag_system()

        threading.Thread(target=_initialize, daemon=True, name="main-rag-init").start()
    return "initializing"

def initialize_dual_protein_rag():
    """初始化双蛋白RAG系统"""
    global dual_protein_system_ready, dual_protein_initializing, dual_protein_docs_count_cache
    if dual_protein_initializing:
        # 并发请求到达时，等待正在进行的初始化完成，避免直接返回失败。
        wait_deadline = time.time() + 120
        while dual_protein_initializing and time.time() < wait_deadline:
            time.sleep(0.2)
        return dual_protein_system_ready
    dual_protein_initializing = True
    try:
        # 启动时自动迁移元数据路径（绝对→相对）
        try:
            dual_protein_rag.metadata_storage.migrate_to_relative_paths()
        except Exception as e:
            app_logger.warning(f"双蛋白元数据路径迁移跳过: {e}")

        with rag_load_lock:
            success = dual_protein_rag.load_or_create_index()
        if success:
            dual_protein_system_ready = True
            stats = dual_protein_rag.get_stats()
            dual_protein_docs_count_cache = stats.get('total_documents', 0)
            print("[成功] 双蛋白系统初始化完成")
        else:
            dual_protein_system_ready = False
        return success
    except Exception as e:
        print(f"[失败] 双蛋白系统初始化失败: {str(e)}")
        dual_protein_system_ready = False
        return False
    finally:
        dual_protein_initializing = False

def _ensure_dual_protein_dim_consistent() -> bool:
    """确保 dual-protein 索引与当前 embedding 维度一致。"""
    global dual_protein_system_ready, dual_protein_last_dim_fix_ts

    def _is_mismatch() -> bool:
        dims = dual_protein_rag._collect_index_embedding_dims() if hasattr(dual_protein_rag, "_collect_index_embedding_dims") else set()
        model_dim = int(getattr(dual_protein_rag, "embedding_dim", 0) or 0)
        return (len(dims) > 1) or (len(dims) == 1 and model_dim and next(iter(dims)) != model_dim)

    try:
        success = initialize_dual_protein_rag() if not dual_protein_system_ready else True
        if not success:
            return False

        if not _is_mismatch():
            return True

        # 同一 worker 内串行执行维度修复；并发请求等待修复完成再复检。
        if not dual_protein_dim_fix_lock.acquire(blocking=False):
            wait_deadline = time.time() + 180
            while time.time() < wait_deadline:
                if initialize_dual_protein_rag() and not _is_mismatch():
                    return True
                time.sleep(1)
            return False

        try:
            # 双重检查，避免重复重建。
            if not _is_mismatch():
                return True

            now = time.time()
            if now - dual_protein_last_dim_fix_ts < 30:
                app_logger.warning("dual-protein 维度修复处于冷却窗口，等待初始化后重试")
                return initialize_dual_protein_rag() and not _is_mismatch()

            dual_protein_last_dim_fix_ts = now
            dims = dual_protein_rag._collect_index_embedding_dims() if hasattr(dual_protein_rag, "_collect_index_embedding_dims") else set()
            model_dim = int(getattr(dual_protein_rag, "embedding_dim", 0) or 0)
            app_logger.warning(f"检测到 dual-protein 维度不一致，执行自动重建: dims={sorted(dims)}, model_dim={model_dim}")
            rebuilt = dual_protein_rag.rebuild_index()
            if not rebuilt:
                app_logger.error("dual-protein 自动重建失败")
                return False
            dual_protein_system_ready = False
            return initialize_dual_protein_rag() and not _is_mismatch()
        finally:
            dual_protein_dim_fix_lock.release()

        return True
    except Exception as e:
        app_logger.error(f"dual-protein 维度一致性检查失败: {e}")
        return False


def _index_exists(rag) -> bool:
    hybrid = getattr(rag, "_hybrid_index_dir", lambda: None)()
    if hybrid:
        return True
    required = ("docstore.json", "index_store.json", "default__vector_store.json")
    return all(os.path.isfile(os.path.join(rag.persist_dir, name)) for name in required)


from services.rag_runtime import RAGRuntimeCoordinator

rag_runtime = RAGRuntimeCoordinator()
rag_runtime.register("sweetness", rag_system, initialize_rag_system, lambda: _index_exists(rag_system))
rag_runtime.register(
    "dual_protein", dual_protein_rag, initialize_dual_protein_rag,
    lambda: _index_exists(dual_protein_rag),
)
rag_runtime.register(
    "encapsulation", encapsulation_rag, initialize_encapsulation_rag,
    lambda: _index_exists(encapsulation_rag),
)
rag_runtime.register(
    "proteoglycan", proteoglycan_rag, initialize_proteoglycan_rag,
    lambda: _index_exists(proteoglycan_rag),
)


def _prewarm_response(domain: str):
    payload = rag_runtime.prewarm(domain)
    payload["message"] = "系统已经初始化" if payload["ready"] else "系统正在后台初始化"
    return jsonify(payload), 200 if payload["ready"] else 202


def _not_ready_stream(domain: str):
    from flask import Response
    import json

    payload = rag_runtime.snapshot(domain)

    def events():
        yield f"event: status\ndata: {json.dumps({'message': f'{domain} 知识库尚未就绪', **payload}, ensure_ascii=False)}\n\n"
        yield f"event: error\ndata: {json.dumps({'error': '知识库未初始化，请先调用 prewarm 接口'}, ensure_ascii=False)}\n\n"

    return Response(events(), status=202, mimetype="text/event-stream")

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
        data = _get_json_dict()
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
    """Start RAG initialization without occupying an HTTP worker."""
    
    app_logger.info("收到系统初始化请求")
    
    if system_ready:
        rag_runtime.mark_ready("sweetness", True)
    else:
        rag_runtime.mark_unloaded("sweetness")
    return _prewarm_response("sweetness")

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
    
    data = _get_json_dict()
    question = data.get('question', '').strip()
    similarity_threshold, max_results = _parse_retrieval_params(
        data,
        config.RAG_SIMILARITY_THRESHOLD,
        config.RAG_MAX_RESULTS,
    )
    
    if not question:
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    result = chat_service.ask(question, similarity_threshold, max_results)
    return jsonify(result)

@app.route('/api/dual-protein/init', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_dual_protein_init():
    """Compatibility alias for non-blocking dual-protein prewarm."""
    if dual_protein_system_ready:
        rag_runtime.mark_ready("dual_protein", True)
    return _prewarm_response("dual_protein")

@app.route('/api/dual-protein/prewarm', methods=['POST'])
@handle_api_errors
def api_dual_protein_prewarm():
    """触发双蛋白系统后台预热（非阻塞）。"""
    if dual_protein_system_ready:
        rag_runtime.mark_ready("dual_protein", True)
    return _prewarm_response("dual_protein")

@app.route('/api/dual-protein/ask', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_dual_protein_ask():
    """处理双蛋白问答请求"""
    if not dual_protein_system_ready:
        return jsonify({
            'success': False,
            'error': '双蛋白系统未初始化，请先调用 /api/dual-protein/init'
        }), 400

    data = _get_json_dict()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400

    dual_default_threshold = float(os.getenv("DUAL_RAG_SIMILARITY_THRESHOLD", "0.18"))
    dual_default_max_results = int(os.getenv("DUAL_RAG_MAX_RESULTS", "120"))
    similarity_threshold, max_results = _parse_retrieval_params(
        data,
        dual_default_threshold,
        dual_default_max_results,
    )

    result = dual_protein_chat_service.ask(question, similarity_threshold, max_results)
    return jsonify(result)

@app.route('/api/dual-protein/health', methods=['GET'])
@handle_api_errors
def api_dual_protein_health():
    """双蛋白系统健康检查"""
    global dual_protein_docs_count_cache
    stats = dual_protein_rag.get_stats()
    if dual_protein_system_ready and dual_protein_docs_count_cache == 0:
        dual_protein_docs_count_cache = stats.get('total_documents', 0)
    try:
        dual_metadata_count = len(dual_protein_rag.metadata_storage.get_all_metadata())
    except Exception:
        dual_metadata_count = 0
    if dual_protein_system_ready:
        rag_runtime.mark_ready("dual_protein", True)
    payload = rag_runtime.snapshot("dual_protein")
    return jsonify({**payload,
        'system_ready': dual_protein_system_ready,
        'initializing': dual_protein_initializing,
        'dual_protein_docs_count': dual_protein_docs_count_cache if dual_protein_system_ready else 0,
        'dual_protein_metadata_count': dual_metadata_count,
        'index_exists': stats.get('index_exists', False),
        'persist_dir': stats.get('persist_dir', './storage_dual_protein'),
    })

@app.route('/api/encapsulation/health', methods=['GET'])
@app.route('/api/embedding/health', methods=['GET'])
@handle_api_errors
def api_encapsulation_health():
    stats = encapsulation_rag.get_stats()
    try:
        count = len(encapsulation_rag.metadata_storage.get_all_metadata())
    except Exception:
        count = 0
    if encapsulation_system_ready:
        rag_runtime.mark_ready("encapsulation", True)
    payload = rag_runtime.snapshot("encapsulation")
    return jsonify({**payload, 'system_ready': encapsulation_system_ready, 'initializing': encapsulation_initializing,
                    'documents_count': count, 'index_exists': stats.get('index_exists', False),
                    'persist_dir': stats.get('persist_dir', ENCAPSULATION_PERSIST_DIR),
                    'last_error': encapsulation_rag.last_error})

@app.route('/api/encapsulation/prewarm', methods=['POST'])
@app.route('/api/embedding/prewarm', methods=['POST'])
@handle_api_errors
def api_encapsulation_prewarm():
    if encapsulation_system_ready:
        rag_runtime.mark_ready("encapsulation", True)
    return _prewarm_response("encapsulation")

@app.route('/api/encapsulation/ask_stream', methods=['POST'])
@app.route('/api/embedding/ask_stream', methods=['POST'])
@handle_api_errors
def api_encapsulation_ask_stream():
    from flask import Response, stream_with_context
    if not encapsulation_system_ready:
        return _not_ready_stream("encapsulation")
    data = _get_json_dict(); question = data.get('question', '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400
    threshold, max_results = _parse_retrieval_params(data, float(os.getenv('EMBEDDING_RAG_SIMILARITY_THRESHOLD', '0.18')), int(os.getenv('EMBEDDING_RAG_MAX_RESULTS', '120')))
    return Response(stream_with_context(encapsulation_chat_service.ask_stream(question, threshold, max_results)), mimetype='text/event-stream')

@app.route('/api/encapsulation/documents', methods=['GET'])
@app.route('/api/embedding/documents', methods=['GET'])
@handle_api_errors
def api_encapsulation_documents():
    rows = []
    for path, meta in encapsulation_rag.metadata_storage.get_all_metadata().items():
        rows.append({'id': path, 'filename': meta.get('filename', os.path.basename(path)), 'title': meta.get('title', ''),
                     'authors': meta.get('authors', []), 'journal': meta.get('journal', ''), 'year': meta.get('year', 'N/A'),
                     'doi': meta.get('doi', ''), 'status': 'indexed', 'path': path})
    query = request.args.get('q', '').lower().strip()
    if query: rows = [r for r in rows if query in ' '.join([r['filename'], r['title'], r['journal'], str(r['year'])]).lower()]
    return jsonify({'success': True, 'documents': rows, 'total': len(rows), 'system_ready': encapsulation_system_ready})

@app.route('/api/encapsulation/documents/upload', methods=['POST'])
@app.route('/api/embedding/documents/upload', methods=['POST'])
@handle_api_errors
def api_encapsulation_upload():
    return jsonify({
        'success': False,
        'error': '网页上传已禁用。请将 PDF 放入 SweetSeek_paper_database/encapsulation/papers 后运行离线索引维护脚本。',
    }), 403

@app.route('/api/proteoglycan/health', methods=['GET'])
@handle_api_errors
def api_proteoglycan_health():
    try:
        count = len(proteoglycan_rag.metadata_storage.get_all_metadata())
    except Exception:
        count = 0
    if proteoglycan_system_ready:
        rag_runtime.mark_ready("proteoglycan", True)
    payload = rag_runtime.snapshot("proteoglycan")
    return jsonify({**payload,
        'system_ready': proteoglycan_system_ready,
        'initializing': proteoglycan_initializing,
        'documents_count': count,
        'index_exists': proteoglycan_index_exists(),
        'persist_dir': PROTEOGLYCAN_PERSIST_DIR,
        'last_error': proteoglycan_rag.last_error,
    })

@app.route('/api/proteoglycan/prewarm', methods=['POST'])
@handle_api_errors
def api_proteoglycan_prewarm():
    if not proteoglycan_index_exists():
        payload = rag_runtime.snapshot("proteoglycan")
        payload.update(state="not_built", status="not_indexed", ready=False, index_exists=False)
        return jsonify(payload), 202
    if proteoglycan_system_ready:
        rag_runtime.mark_ready("proteoglycan", True)
    return _prewarm_response("proteoglycan")

@app.route('/api/proteoglycan/ask_stream', methods=['POST'])
@handle_api_errors
def api_proteoglycan_ask_stream():
    from flask import Response, stream_with_context
    if not proteoglycan_index_exists():
        return jsonify({'success': False, 'error': PROTEOGLYCAN_EMPTY_MESSAGE}), 503
    if not proteoglycan_system_ready:
        return _not_ready_stream("proteoglycan")
    data = _get_json_dict()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400
    threshold, max_results = _parse_retrieval_params(
        data,
        float(os.getenv('PROTEOGLYCAN_RAG_SIMILARITY_THRESHOLD', '0.18')),
        int(os.getenv('PROTEOGLYCAN_RAG_MAX_RESULTS', '120')),
    )
    return Response(
        stream_with_context(proteoglycan_chat_service.ask_stream(question, threshold, max_results)),
        mimetype='text/event-stream',
    )

@app.route('/api/proteoglycan/documents', methods=['GET'])
@handle_api_errors
def api_proteoglycan_documents():
    rows = []
    for path, meta in proteoglycan_rag.metadata_storage.get_all_metadata().items():
        rows.append({
            'id': path,
            'filename': meta.get('filename', os.path.basename(path)),
            'title': meta.get('title', ''),
            'authors': meta.get('authors', []),
            'journal': meta.get('journal', ''),
            'year': meta.get('year', 'N/A'),
            'doi': meta.get('doi', ''),
            'status': 'indexed',
            'path': path,
        })
    query = request.args.get('q', '').lower().strip()
    if query:
        rows = [row for row in rows if query in ' '.join([
            row['filename'], row['title'], row['journal'], str(row['year'])
        ]).lower()]
    return jsonify({
        'success': True,
        'documents': rows,
        'total': len(rows),
        'system_ready': proteoglycan_system_ready,
    })

@app.route('/api/proteoglycan/documents/upload', methods=['POST'])
@handle_api_errors
def api_proteoglycan_upload():
    return jsonify({
        'success': False,
        'error': '网页上传已禁用。请将 PDF 放入 SweetSeek_paper_database/proteoglycan/papers 后运行离线索引维护脚本。',
    }), 403

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
    
    data = _get_json_dict()
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

@app.route('/api/live', methods=['GET'])
def api_live():
    """Process liveness endpoint that never initializes RAG state."""
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now().isoformat(),
        'pid': os.getpid(),
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """系统健康检查"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # 主甜味系统文档统计
    try:
        stats = rag_system.get_stats()
        sweetness_docs_count = stats.get('total_documents', 0)
        health_status['components']['rag_system'] = {
            'status': 'healthy' if system_ready else 'unhealthy',
            'documents': sweetness_docs_count
        }
        health_status['sweetness_docs_count'] = sweetness_docs_count
    except Exception as e:
        health_status['components']['rag_system'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
        health_status['sweetness_docs_count'] = 0
    
    # 检查 DeepSeek API
    try:
        import persistent_storage
        if not hasattr(persistent_storage, 'deepseek_client') and hasattr(persistent_storage, "configure_llm"):
            persistent_storage.configure_llm()

        deepseek_client = getattr(persistent_storage, 'deepseek_client', None)
        health_status['components']['deepseek_api'] = {
            'status': 'configured' if deepseek_client is not None else 'not_configured'
        }
    except Exception as e:
        health_status['components']['deepseek_api'] = {
            'status': 'error',
            'error': str(e)
        }

    # 检查 embedding 模式（真实模型/占位模式）
    try:
        embed_mode = getattr(rag_system, 'embedding_mode', 'unknown')
        embed_dim = getattr(rag_system, 'embedding_dim', None)
        embed_status = 'healthy'
        if embed_mode == 'placeholder':
            embed_status = 'degraded'
            health_status['status'] = 'degraded'

        health_status['components']['embedding_model'] = {
            'status': embed_status,
            'mode': embed_mode,
            'dimension': embed_dim,
        }
    except Exception as e:
        health_status['components']['embedding_model'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 主元数据存储统计（不是 dual-protein 文献数）
    try:
        metadata_count = len(rag_system.metadata_storage.get_all_metadata())
        health_status['components']['metadata_storage'] = {
            'status': 'healthy',
            'count': metadata_count
        }
        health_status['main_metadata_count'] = metadata_count
    except Exception as e:
        health_status['components']['metadata_storage'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['main_metadata_count'] = 0

    # Dual-Protein 文档统计（独立于主甜味系统）
    try:
        dp_stats = dual_protein_rag.get_stats()
        health_status['dual_protein_docs_count'] = dp_stats.get('total_documents', 0)
    except Exception:
        health_status['dual_protein_docs_count'] = 0
    
    if system_ready:
        rag_runtime.mark_ready("sweetness", True)
    health_status["domains"] = {
        domain: rag_runtime.snapshot(domain)
        for domain in ("sweetness", "dual_protein", "encapsulation", "proteoglycan")
    }
    if not all(item.get("ready") for item in health_status["domains"].values()):
        health_status['status'] = 'degraded'
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
    
    data = _get_json_dict()
    question = data.get('question', '').strip()
    similarity_threshold, max_results = _parse_retrieval_params(
        data,
        config.RAG_SIMILARITY_THRESHOLD,
        config.RAG_MAX_RESULTS,
    )
    
    if not question:
        return jsonify({
            'success': False,
            'error': '问题不能为空'
        }), 400
    
    return Response(stream_with_context(chat_service.ask_stream(question, similarity_threshold, max_results)), mimetype='text/event-stream')

@app.route('/api/dual-protein/ask_stream', methods=['POST'])
@handle_api_errors
def api_dual_protein_ask_stream():
    """双蛋白流式问答 API（Server-Sent Events）"""
    from flask import Response, stream_with_context

    if not dual_protein_system_ready:
        return _not_ready_stream("dual_protein")

    data = _get_json_dict()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400

    dual_default_threshold = float(os.getenv("DUAL_RAG_SIMILARITY_THRESHOLD", "0.18"))
    dual_default_max_results = int(os.getenv("DUAL_RAG_MAX_RESULTS", "120"))
    similarity_threshold, max_results = _parse_retrieval_params(
        data,
        dual_default_threshold,
        dual_default_max_results,
    )

    return Response(
        stream_with_context(dual_protein_chat_service.ask_stream(question, similarity_threshold, max_results)),
        mimetype='text/event-stream'
    )

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    # 兼容旧路径，或直接返回404
    return jsonify({'error': 'Static files not served by backend'}), 404

# 自动初始化（针对 Gunicorn 等 WSGI 容器）
if __name__ != '__main__' and os.getenv('RAG_EAGER_INIT', '').strip().lower() in {'1', 'true', 'yes'}:
    def _background_init_main_rag():
        try:
            app_logger.info("检测到非主程序运行模式，后台初始化 RAG 系统...")
            rag_runtime.prewarm("sweetness")
        except Exception as e:
            app_logger.error(f"自动初始化失败: {e}")

    def _background_init_dual_protein_rag():
        try:
            app_logger.info("检测到非主程序运行模式，后台初始化双蛋白 RAG 系统...")
            rag_runtime.prewarm("dual_protein")
        except Exception as e:
            app_logger.error(f"双蛋白自动初始化失败: {e}")

    # 低内存生产机按需加载。显式启用时也串行初始化，避免多个大索引同时产生峰值。
    def _background_init_all_rag():
        _background_init_main_rag()
        _background_init_dual_protein_rag()

    threading.Thread(target=_background_init_all_rag, daemon=True).start()

# ============================================================
# ML 甜味预测 API
# ============================================================

@app.route('/api/ml/predict', methods=['POST'])
@handle_api_errors
@monitor_performance
def api_ml_predict():
    """
    甜味预测 API
    输入: {"smiles": "CCO"} 或 {"smiles": ["CCO", "C1=CC=C(C=C1)O"]}
    输出: 单个预测结果或列表
    """
    from services.sweetness_prediction_service import get_sweetness_prediction_service

    data = _get_json_dict()
    smiles_input = data.get('smiles', '')

    if not smiles_input:
        return jsonify({
            'success': False,
            'error': 'SMILES 不能为空'
        }), 400

    predictor = get_sweetness_prediction_service().predictor

    # 支持单个或批量
    if isinstance(smiles_input, str):
        result = predictor.predict(smiles_input)
        return jsonify({
            'success': True,
            'result': result
        })
    elif isinstance(smiles_input, list):
        results = predictor.predict_batch(smiles_input)
        return jsonify({
            'success': True,
            'results': results
        })
    else:
        return jsonify({
            'success': False,
            'error': 'smiles 参数必须是字符串或字符串列表'
        }), 400

@app.route('/predict')
def predict_page():
    """甜味预测页面"""
    return render_template('predict.html')

if __name__ == '__main__':
    # 固定默认端口 5001：与现有 gunicorn/nginx/部署脚本保持一致，降低本地与线上端口漂移风险。
    # 允许通过 PORT 覆盖仅用于极少数临时调试场景；常规开发与部署保持 5001 不变。
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
