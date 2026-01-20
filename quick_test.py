#!/usr/bin/env python3
"""快速测试 - 查看实际返回的references"""

import requests
import json
import sys

question = "人工甜味剂的影响"
print(f"问题: {question}\n")

response = requests.post(
    'http://localhost:5001/api/ask_stream',
    json={'question': question},
    stream=True,
    timeout=30
)

references = []
answer = ""
ref_count = 0

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            try:
                data = json.loads(line_str[6:])
                
                if data['type'] == 'references':
                    references = data['references']
                    ref_count = len(references)
                    print(f"收到 {ref_count} 篇参考文献:")
                    for i, ref in enumerate(references, 1):
                        print(f"  {i}. {ref['ref_id']}: {ref.get('title', ref['filename'])[:50]}")
                    print()
                
                elif data['type'] == 'answer':
                    answer += data['content']
                
                elif data['type'] == 'done':
                    break
                    
            except:
                pass

# 分析回答中的ref引用
import re
ref_pattern = r'\[ref_(\d+)\]'
found_refs = sorted(set(re.findall(ref_pattern, answer)), key=int)

print("\n" + "="*60)
print("分析结果:")
print("="*60)
print(f"References列表中的ref: {[ref['ref_id'] for ref in references]}")
print(f"回答中引用的ref: {['ref_' + r for r in found_refs]}")

valid_refs = {ref['ref_id'].replace('ref_', '') for ref in references}
invalid_refs = set(found_refs) - valid_refs

if invalid_refs:
    print(f"\n❌ 错误！回答中引用了不存在的ref: {['ref_' + r for r in sorted(invalid_refs, key=int)]}")
    print(f"\n回答片段:")
    print(answer[:500])
else:
    print(f"\n✅ 所有引用都正确！")
