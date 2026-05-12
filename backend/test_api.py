import requests
import json

BASE_URL = 'http://localhost:5000'

print('=== 测试 API 连接 ===')

# 测试 Token 状态
print('\n1. 检查 Token 状态...')
resp = requests.get(f'{BASE_URL}/api/token-status')
print(f'状态: {resp.status_code}')
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

# 测试同步
print('\n2. 测试数据同步...')
resp = requests.post(f'{BASE_URL}/api/sync', json={'days': 7})
print(f'状态: {resp.status_code}')
data = resp.json()
if data.get('success'):
    print('同步成功！')
    print(f"总花费: ${data['data']['summary']['total_spend']:,.2f}")
    print(f"总销售额: ${data['data']['summary']['total_sales']:,.2f}")
    print(f"平均 ROI: {data['data']['summary']['avg_roi']:.2f}")
else:
    print('同步失败:', data.get('message'))

print('\n=== 测试完成 ===')
