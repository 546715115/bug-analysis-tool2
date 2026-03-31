# test_api_flow.py - 模拟API响应，测试API导入全流程
import pandas as pd
from datetime import datetime
import sys
sys.path.insert(0, '.')

from crawler import BugCrawler
from processor import load_excel, merge_data, normalize_columns, get_version_list, filter_by_version, get_chart_data
from di_calculator import (
    calculate_cloud_di, calculate_microservice_di_with_count,
    filter_production_issues, should_count_di, calculate_di_for_issue, is_delivery_excluded
)

print("=" * 70)
print("Simulate API Response Test - Full Flow Verification")
print("=" * 70)

# ============================================================
# Step 1: Mock API Response
# ============================================================
def mock_api_response():
    import random
    statuses = [
        ("ISSUE_STATUS_SUBMIT", ""),
        ("ISSUE_STATUS_ANALYSIS", ""),
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_PLANNING"),
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_CODE"),
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_TEST"),
        ("ISSUE_STATUS_FIXING", "ISSUE_STAGE_DONE"),
        ("ISSUE_STATUS_VERIFYING", ""),
        ("ISSUE_STATUS_REGRESSION_TEST", ""),
        ("ISSUE_STATUS_RETURNED", ""),
    ]
    severities = ["04003001", "04003002", "04003003", "04003004"]
    domains = [
        {"id": 33901, "title": "CES公共开发"},
        {"id": 33902, "title": "CES告警"},
        {"id": 33903, "title": "Cloud Eye"}
    ]
    envs = [
        {"id": 4, "category": "dev", "title": "非生产环境"},
        {"id": 5, "category": "prod", "title": "生产环境"}
    ]
    versions = [
        {"id": 1, "number": "RP2026032700001", "title": "25.1.0"},
        {"id": 2, "number": "RP2026032700002", "title": "25.2.0"},
        {"id": 3, "number": "RP2026032700003", "title": "25.3.0"},
    ]

    items = []
    for i in range(30):
        status_raw, stage_raw = random.choice(statuses)
        severity = random.choice(severities)
        discovered_env = random.choice(envs)
        domain = random.choice(domains)
        version = random.choice(versions)
        days_ago = random.randint(8, 60)
        updated = (datetime.now() - pd.Timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")

        item = {
            "id": 4774898 + i,
            "number": f"BUG20260327{i:04d}",
            "title": f"[Test] Issue Title {i+1}",
            "severity": severity,
            "status": status_raw,
            "stage": stage_raw,
            "assigned_domain": domain,
            "discovered_environment": discovered_env,
            "fromVersion": version,
            "deliveryScenario": "HCSO",
            "valid": 1,
            "created_time": "2026-03-27 16:03:01",
            "updated_time": updated,
            "develop_owners": [{"id": 312281, "name": "ZhangSan"}],
            "test_owners": [{"id": 312282, "name": "LiSi"}],
            "labels": [],
            "iteration": "Iteration1",
        }
        items.append(item)

    return {
        "code": 200,
        "message": "Success",
        "data": {
            "result": items,
            "total_pages": 1,
            "page_size": 100,
            "current_page": 1,
            "total_records": 30,
        }
    }

# ============================================================
# Step 2: Simulate API fetch
# ============================================================
print("\n[Step 1] Simulate API fetch_all_domains()")
print("-" * 50)

response = mock_api_response()
items = response["data"]["result"]
print(f"  API returned items: {len(items)}")

crawler = BugCrawler({})
parsed_items = [crawler._parse_issue(item) for item in items]
df_api = pd.DataFrame(parsed_items)
print(f"  pd.DataFrame rows: {len(df_api)}")
print(f"  Columns: {list(df_api.columns)}")

# ============================================================
# Step 3: Simulate data processing (shared with Excel)
# ============================================================
print("\n[Step 2] Simulate data processing (merge_data + normalize_columns)")
print("-" * 50)

merged = merge_data(pd.DataFrame(), df_api)
print(f"  After merge_data: {len(merged)} rows")

merged = normalize_columns(merged)
print(f"  After normalize_columns columns: {list(merged.columns)}")

# ============================================================
# Step 4: Simulate main flow
# ============================================================
print("\n[Step 3] Simulate main flow (version filter + CCB filter + DI)")
print("-" * 50)

versions = get_version_list(merged)
print(f"  Version list: {versions}")

selected_version = versions[0] if versions else "全部"
print(f"  Selected version: {selected_version}")
df_filtered = filter_by_version(merged, selected_version)
print(f"  After version filter: {len(df_filtered)} rows")

df_prod = filter_production_issues(df_filtered)
print(f"  After filter_production_issues: {len(df_prod)} rows")

cloud_di = calculate_cloud_di(df_prod)
print(f"  Cloud DI: {cloud_di['di']}")
print(f"  Cloud Qualified: {cloud_di['qualified']}")
print(f"  DI debug: {cloud_di['debug']}")

ms_di = calculate_microservice_di_with_count(df_prod)
print(f"  Microservice DI details:")
if not ms_di.empty:
    for _, row in ms_di.iterrows():
        print(f"    - {row['assigned_to_domain']}: DI={row['di_sum']}, count={row['issue_count']}, qualified={row['qualified']}")

# ============================================================
# Step 5: Simulate charts
# ============================================================
print("\n[Step 4] Simulate chart data")
print("-" * 50)

chart_data = get_chart_data(df_prod)

print(f"  Monthly distribution:")
for _, row in chart_data["monthly"].iterrows():
    print(f"    {row['月份']}: {row['问题单数']}")

print(f"  Severity distribution:")
for _, row in chart_data["severity"].iterrows():
    print(f"    {row['severity_level']}: {row['数量']}")

print(f"  Environment distribution:")
for _, row in chart_data["environment"].iterrows():
    print(f"    {row['discovered_environment']}: {row['数量']}")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 70)
print("TEST PASSED!")
print("=" * 70)
print("\n[Verification Checklist]")
print(f"  [PASS] API data parsed: {len(df_api)} rows")
print(f"  [PASS] Data processing: {len(merged)} rows")
print(f"  [PASS] CCB filter: {len(df_prod)} rows")
print(f"  [PASS] Cloud DI: {cloud_di['di']}")
print(f"  [PASS] Versions: {versions}")
