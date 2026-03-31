# test_crawler.py - 模拟API输出测试工具功能
import sys
import pandas as pd
from datetime import datetime, timedelta
import random

# 导入模块
from crawler import BugCrawler, STATUS_MAPPING, STAGE_MAPPING, SEVERITY_MAPPING
from processor import get_version_list, filter_by_version, get_chart_data, normalize_columns
from di_calculator import (
    calculate_cloud_di, calculate_microservice_di_with_count,
    filter_production_issues, should_count_di, calculate_di_for_issue
)

print("=" * 60)
print("模拟API测试 - 开始")
print("=" * 60)

# 1. 模拟API返回数据（使用原始API值）
def mock_api_items():
    """模拟API返回的数据"""
    statuses_raw = [
        ("ISSUE_STATUS_SUBMIT", ""),
        ("ISSUE_STATUS_ANALYSIS", ""),
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_PLANNING"),  # 待修复
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_CODE"),      # 修复中
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_TEST"),      # 修复测试
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_DONE"),       # 修复完成
        ("ISSUE_STATUS_VERIFYING", ""),                    # 待验收
        ("ISSUE_STATUS_REGRESSION_TEST", ""),              # 已关闭
        ("ISSUE_STATUS_RETURNED", ""),                     # 待确认
    ]
    severities = ["04003001", "04003002", "04003003", "04003004"]  # 提示/一般/严重/致命
    domains = [{"id": 33901, "title": "CES公共开发"}, {"id": 33902, "title": "CES告警"}]
    envs = [
        {"id": 4, "category": "dev", "title": "非生产环境"},
        {"id": 5, "category": "prod", "title": "生产环境"}
    ]

    items = []
    for i in range(20):
        status_raw, stage_raw = random.choice(statuses_raw)
        severity = random.choice(severities)
        discovered_env = random.choice(envs)
        domain = random.choice(domains)

        item = {
            "id": 4774898 + i,
            "number": f"BUG202603273942{i:02d}",
            "title": f"[Test] Issue {i+1}",
            "severity": severity,
            "status": status_raw,
            "stage": stage_raw,
            "assigned_domain": domain,
            "discovered_environment": discovered_env,
            "fromVersion": {"id": 440701, "number": "RP2024122000369"},
            "deliveryScenario": "HCSO",
            "valid": 1,  # 有效
            "created_time": "2026-03-27 16:03:01",
            "updated_time": "2026-01-15 10:00:00",  # 超过SLA阈值
            "develop_owners": [{"id": 312281, "name": "ZhangSan"}],
            "test_owners": [{"id": 312282, "name": "LiSi"}],
            "labels": [],
            "iteration": "Iteration1",
        }
        items.append(item)

    return items

# 2. 使用 crawler 解析数据
crawler = BugCrawler({})
items = mock_api_items()
parsed_items = [crawler._parse_issue(item) for item in items]
df = pd.DataFrame(parsed_items)

print("\n[1] 解析后数据（前5条）:")
for i, row in df.head(5).iterrows():
    print(f"  {row['number']}: status={row['status']}, stage={row['stage']}, env={row['discovered_environment']}, severity={row['severity_level']}")

# 3. 版本列表
print("\n[2] 版本列表:")
versions = get_version_list(df)
print(f"  {versions}")

# 4. 测试 should_count_di（使用映射后的值）
print("\n[3] 测试 should_count_di:")
test_cases = [
    ("待提交", "", "非生产环境"),
    ("定位中", "", "非生产环境"),
    ("修复", "待修复", "非生产环境"),
    ("修复", "修复中", "非生产环境"),
    ("修复", "修复测试", "非生产环境"),
    ("修复", "修复完成", "非生产环境"),
    ("待验收", "", "生产环境"),
    ("已关闭", "", "生产环境"),
    ("待确认", "", "生产环境"),
]

for status, stage, env in test_cases:
    should, reason = should_count_di(status, stage, env)
    print(f"  status={status}, stage={stage}, env={env} -> count={should}, reason={reason}")

# 5. DI 计算
print("\n[4] DI 计算:")
df_prod = filter_production_issues(df)
print(f"  filter_production_issues: {len(df_prod)} 条")

cloud_di = calculate_cloud_di(df_prod)
print(f"  云服务DI: {cloud_di['di']}")
print(f"  云服务合格: {cloud_di['qualified']}")
print(f"  调试: {cloud_di['debug']}")

ms_di = calculate_microservice_di_with_count(df_prod)
print(f"  微服务DI明细:")
if not ms_di.empty:
    for _, row in ms_di.iterrows():
        print(f"    {row['assigned_to_domain']}: DI={row['di_sum']}, count={row['issue_count']}, qualified={row['qualified']}")
else:
    print("    (无)")

# 6. 逐个检查 DI > 0 的问题单
print("\n[5] 逐个检查 DI > 0 的问题单:")
from datetime import datetime
now = datetime.now()
di_details = []
for _, row in df_prod.iterrows():
    di = calculate_di_for_issue(row, now)
    if di > 0:
        di_details.append({
            'number': row['number'],
            'status': row['status'],
            'stage': row['stage'],
            'env': row['discovered_environment'],
            'severity': row['severity_level'],
            'di': di
        })

if di_details:
    for d in di_details:
        print(f"  {d['number']}: status={d['status']}, stage={d['stage']}, env={d['env']}, severity={d['severity']}, DI={d['di']}")
else:
    print("  (无 DI > 0 的问题单)")

# 7. 测试图表数据
print("\n[6] 图表数据:")
chart_data = get_chart_data(df_prod)
print(f"  月度分布: {chart_data['monthly'].to_dict()}")
print(f"  严重程度: {chart_data['severity'].to_dict()}")
print(f"  环境分布: {chart_data['environment'].to_dict()}")

print("\n" + "=" * 60)
print("模拟API测试 - 完成")
print("=" * 60)
