#!/usr/bin/env python3
"""
测试MPS加速后的Embedding性能

对比:
- CPU模式: ~280ms
- MPS模式: 预计 ~50-80ms (3-5倍提速)
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import torch
from sentence_transformers import SentenceTransformer

def test_mps_speedup():
    """测试MPS加速效果"""
    print("=" * 60)
    print("测试MPS加速效果")
    print("=" * 60)

    model_path = project_root / "models" / "modelscope_cache" / "BAAI" / "bge-small-zh-v1___5"

    test_queries = [
        "甜味剂的种类和特点",
        "天然甜味物质有哪些",
        "人工甜味剂的安全性",
    ]

    # 测试CPU模式
    print("\n【CPU模式】")
    print("-" * 60)
    model_cpu = SentenceTransformer(str(model_path), device="cpu")

    cpu_times = []
    for query in test_queries:
        start = time.time()
        _ = model_cpu.encode(query, convert_to_numpy=True)
        elapsed = time.time() - start
        cpu_times.append(elapsed)
        print(f"  {query}: {elapsed*1000:.1f}ms")

    avg_cpu = sum(cpu_times) / len(cpu_times)
    print(f"平均: {avg_cpu*1000:.1f}ms")

    # 测试MPS模式
    print("\n【MPS模式】")
    print("-" * 60)

    if not torch.backends.mps.is_available():
        print("⚠️  MPS不可用")
        return

    model_mps = SentenceTransformer(str(model_path), device="mps")

    # 预热
    _ = model_mps.encode("预热", convert_to_numpy=True)

    mps_times = []
    for query in test_queries:
        start = time.time()
        _ = model_mps.encode(query, convert_to_numpy=True)
        elapsed = time.time() - start
        mps_times.append(elapsed)
        print(f"  {query}: {elapsed*1000:.1f}ms")

    avg_mps = sum(mps_times) / len(mps_times)
    print(f"平均: {avg_mps*1000:.1f}ms")

    # 对比
    print("\n" + "=" * 60)
    print("【性能对比】")
    print("=" * 60)
    speedup = avg_cpu / avg_mps
    print(f"CPU平均:  {avg_cpu*1000:.1f}ms")
    print(f"MPS平均:  {avg_mps*1000:.1f}ms")
    print(f"加速比:   {speedup:.1f}x ⚡️")
    print(f"节省时间: {(avg_cpu - avg_mps)*1000:.1f}ms")

if __name__ == "__main__":
    test_mps_speedup()
