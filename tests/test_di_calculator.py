# tests/test_di_calculator.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from di_calculator import (
    SEVERITY_DI, SLA_THRESHOLDS, QUALIFICATION_THRESHOLDS,
    CES_MICROSERVICES, calculate_di_for_issue, is_microservice,
    calculate_microservice_di, filter_production_issues
)

def test_severity_di_weights():
    """测试 DI 权重"""
    assert SEVERITY_DI["致命"] == 10
    assert SEVERITY_DI["严重"] == 3
    assert SEVERITY_DI["一般"] == 1
    assert SEVERITY_DI["提示"] == 0.1

def test_sla_thresholds():
    """测试 SLA 阈值"""
    assert SLA_THRESHOLDS["致命"] == 7
    assert SLA_THRESHOLDS["严重"] == 14
    assert SLA_THRESHOLDS["一般"] == 30
    assert SLA_THRESHOLDS["提示"] == 30

def test_is_microservice():
    """测试 CES 微服务模糊匹配"""
    assert is_microservice("CES API") == True
    assert is_microservice("CES-Agent") == True
    assert is_microservice("云监控") == False
    assert is_microservice("其他服务") == False

def test_filter_production_issues():
    """测试生产环境问题过滤（非生产环境+挂起=剔除）"""
    df = pd.DataFrame([
        {"discovered_environment": "生产环境", "valid": "挂起", "severity_level": "致命"},
        {"discovered_environment": "非生产环境", "valid": "挂起", "severity_level": "严重"},
        {"discovered_environment": "非生产环境", "valid": "有效", "severity_level": "一般"},
        {"discovered_environment": "生产环境", "valid": "有效", "severity_level": "提示"},
    ])

    result = filter_production_issues(df)
    # 非生产+挂起应该被剔除，保留3条
    assert len(result) == 3

def test_calculate_di_for_issue():
    """测试单个问题的 DI 计算"""
    # 致命问题 DI=10
    assert calculate_di_for_issue("致命") == 10

    # 严重问题 DI=3
    assert calculate_di_for_issue("严重") == 3

    # 一般问题 DI=1
    assert calculate_di_for_issue("一般") == 1

    # 提示问题 DI=0.1
    assert calculate_di_for_issue("提示") == 0.1

def test_calculate_microservice_di():
    """测试按微服务分组统计"""
    df = pd.DataFrame([
        {"assigned_to_domain": "CES API", "severity_level": "致命", "from_version": "V1.0"},
        {"assigned_to_domain": "CES API", "severity_level": "严重", "from_version": "V1.0"},
        {"assigned_to_domain": "云监控", "severity_level": "一般", "from_version": "V1.0"},
    ])

    result = calculate_microservice_di(df)

    # CES API 有2条问题单，DI=10+3=13
    ces_api = result[result["assigned_to_domain"] == "CES API"]
    assert ces_api.iloc[0]["di_sum"] == 13
    assert ces_api.iloc[0]["issue_count"] == 2

    # 云监控不在 CES 微服务列表，不显示
    assert len(result[result["assigned_to_domain"] == "云监控"]) == 0