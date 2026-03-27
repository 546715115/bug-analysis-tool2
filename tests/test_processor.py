# tests/test_processor.py
import pytest
import pandas as pd
from io import BytesIO
from processor import load_excel, merge_data, normalize_columns, FIELD_MAPPING

def test_field_mapping_contains_required_fields():
    """测试字段映射包含所有必需字段"""
    required_fields = [
        "severity_level", "status", "assigned_to_domain",
        "from_version", "created_time", "delivery_scenario",
        "valid", "discovered_environment", "labels",
        "dev_person", "testOwners", "number", "title"
    ]
    for field in required_fields:
        assert field in FIELD_MAPPING, f"Missing field: {field}"

def test_load_excel_with_sample_data():
    """测试加载 Excel 数据"""
    # 创建一个简单的测试 Excel
    df = pd.DataFrame({
        "number": ["BUG001", "BUG002"],
        "title": ["Test1", "Test2"],
        "severity_level": ["致命", "严重"]
    })
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    result = load_excel(buffer.getvalue())
    assert len(result) == 2
    assert "number" in result.columns

def test_merge_data_removes_duplicates():
    """测试合并数据并去重"""
    df1 = pd.DataFrame({
        "number": ["BUG001", "BUG002"],
        "severity_level": ["致命", "严重"]
    })
    df2 = pd.DataFrame({
        "number": ["BUG001", "BUG003"],
        "severity_level": ["致命", "一般"]
    })

    result = merge_data(df1, df2)
    assert len(result) == 3  # 去重后应该只有3条
    assert result[result["number"] == "BUG001"].shape[0] == 1  # 只有一条