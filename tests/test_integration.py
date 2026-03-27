# tests/test_integration.py
import pytest
import pandas as pd
from di_calculator import calculate_microservice_di, calculate_cloud_di, filter_production_issues
from processor import merge_data, filter_by_version

def test_full_di_calculation_flow():
    """测试完整的 DI 计算流程"""
    # 模拟数据
    df1 = pd.DataFrame([
        {
            "number": "BUG001",
            "severity_level": "致命",
            "status": "修复中",
            "assigned_to_domain": "CES API",
            "from_version": "V1.0",
            "discovered_environment": "生产环境",
            "valid": "有效",
            "delivery_scenario": "华为云"
        },
        {
            "number": "BUG002",
            "severity_level": "严重",
            "status": "待验收",
            "assigned_to_domain": "CES API",
            "from_version": "V1.0",
            "discovered_environment": "生产环境",
            "valid": "有效",
            "delivery_scenario": "华为云"
        }
    ])

    # 过滤生产环境问题
    df_filtered = filter_production_issues(df1)
    assert len(df_filtered) == 2  # 都保留

    # 计算云服务 DI
    cloud_di = calculate_cloud_di(df_filtered)
    assert cloud_di["di"] == 13  # 致命=10, 严重=3

    # 按微服务统计
    ms_di = calculate_microservice_di(df_filtered)
    assert len(ms_di) == 1
    assert ms_di.iloc[0]["assigned_to_domain"] == "CES API"
    assert ms_di.iloc[0]["di_sum"] == 13

def test_version_filter_with_empty():
    """测试版本过滤包含空版本"""
    df = pd.DataFrame([
        {"number": "BUG001", "from_version": "V1.0", "severity_level": "致命"},
        {"number": "BUG002", "from_version": "V2.0", "severity_level": "严重"},
        {"number": "BUG003", "from_version": "", "severity_level": "一般"},
        {"number": "BUG004", "from_version": None, "severity_level": "提示"}
    ])

    # 过滤 V1.0 版本时，应该包含 V1.0 + 空版本
    df_filtered = filter_by_version(df, "V1.0")
    assert len(df_filtered) == 3  # BUG001, BUG003, BUG004

def test_hcs_delivery_scenario():
    """测试 HCS 交付场景"""
    from di_calculator import apply_delivery_scenario

    df = pd.DataFrame([
        {"number": "BUG001", "severity_level": "致命", "delivery_scenario": "华为云"},
        {"number": "BUG002", "severity_level": "严重", "delivery_scenario": "HCS"}
    ])

    result = apply_delivery_scenario(df)
    # HCS 的 DI 应该被设为 0
    assert result.loc[result["delivery_scenario"] == "HCS", "_di_contribution"].values[0] == 0

def test_merge_and_deduplicate():
    """测试数据合并去重"""
    df1 = pd.DataFrame([
        {"number": "BUG001", "severity_level": "致命"},
        {"number": "BUG002", "severity_level": "严重"}
    ])

    df2 = pd.DataFrame([
        {"number": "BUG001", "severity_level": "致命"},  # 重复
        {"number": "BUG003", "severity_level": "一般"}
    ])

    result = merge_data(df1, df2)
    assert len(result) == 3  # 去重后应该只有3条
    assert result[result["number"] == "BUG001"].shape[0] == 1

def test_ces_microservice_fuzzy_match():
    """测试 CES 微服务模糊匹配"""
    from di_calculator import is_microservice

    # 精确匹配
    assert is_microservice("CES API") == True
    assert is_microservice("CES Agent") == True

    # 部分匹配
    assert is_microservice("CES") == True
    assert is_microservice("CES监控") == True

    # 不匹配
    assert is_microservice("云监控") == False
    assert is_microservice("其他服务") == False
    assert is_microservice("") == False
    assert is_microservice(None) == False