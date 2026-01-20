#!/usr/bin/env python3
"""测试API并查看references数据"""

import requests
import json

# 测试问题
question = "人工甜味剂对健康的影响"

print(f"提问: {question}\n")

# 调用API
response = requests.post(
    'http://localhost:5001/api/ask_stream',
    json={'question': question},
    stream=True
)

references = []
answer_parts = []

print("=" * 60)
print("接收到的数据流：")
print("=" * 60)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            try:
                data = json.loads(line_str[6:])
                
                if data['type'] == 'status':
                    print(f"[状态] {data['message']}")
                
                elif data['type'] == 'references':
                    references = data['references']
                    print(f"\n[参考文献] 收到 {len(references)} 篇文献:")
                    for ref in references:
                        print(f"  - {ref['ref_id']}: {ref.get('title', ref['filename'])[:60]}...")
                
                elif data['type'] == 'answer':
                    answer_parts.append(data['content'])
                
                elif data['type'] == 'done':
                    print("\n[完成] 数据流结束")
                    
            except json.JSONDecodeError as e:
                print(f"[错误] JSON解析失败: {e}")

print("\n" + "=" * 60)
print("完整回答：")
print("=" * 60)
answer = ''.join(answer_parts)
print(answer[:500] + "..." if len(answer) > 500 else answer)

print("\n" + "=" * 60)
print("References详情：")
print("=" * 60)
for ref in references:
    print(f"\n{ref['ref_id']}:")
    print(f"  标题: {ref.get('title', ref['filename'])}")
    print(f"  期刊: {ref.get('journal', 'Unknown')}")
    print(f"  年份: {ref.get('year', 'N/A')}")
    print(f"  文件名: {ref['filename']}")

print("\n" + "=" * 60)
print("分析：")
print("=" * 60)
print(f"总共返回 {len(references)} 篇参考文献")
print(f"ref_id范围: {references[0]['ref_id']} 到 {references[-1]['ref_id']}")

# 检查回答中的ref引用
import re
ref_pattern = r'\[ref_(\d+)\]'
found_refs = set(re.findall(ref_pattern, answer))
print(f"\n回答中引用的ref编号: {sorted(found_refs, key=int)}")
print(f"实际存在的ref编号: {[ref['ref_id'] for ref in references]}")

# 检查是否有不匹配的引用
valid_ref_ids = {ref['ref_id'].replace('ref_', '') for ref in references}
invalid_refs = found_refs - valid_ref_ids
if invalid_refs:
    print(f"\n⚠️  警告：回答中引用了不存在的ref编号: {sorted(invalid_refs, key=int)}")
else:
    print(f"\n✅ 所有引用的ref编号都有效！")
