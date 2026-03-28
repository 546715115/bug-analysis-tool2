# processor.py
import pandas as pd
from io import BytesIO
from typing import List, Optional

FIELD_MAPPING = {
    "number": ["问题单号", "问题编号"],
    "title": ["标题", "问题标题"],
    "severity_level": ["严重程度"],
    "status": ["问题状态", "状态"],
    "assigned_to_domain": ["责任服务", "负责域"],
    "from_version": ["发现问题版本", "版本"],
    "discover_iteration": ["发现迭代"],
    "created_time": ["创建时间"],
    "stage": ["问题阶段"],
    "discovered_time": ["发现时间"],
    "delivery_scenario": ["交付场景"],
    "valid": ["挂起/撤销"],
    "discovered_environment": ["发现环境"],
    "labels": ["标签"],
    "dev_person": ["研发责任人"],
    "testOwners": ["测试责任人"]
}

# 中文到英文的反向映射（处理多种中文列名对应同一英文）
CHINESE_TO_ENGLISH = {}
for en, cn_list in FIELD_MAPPING.items():
    for cn in cn_list:
        CHINESE_TO_ENGLISH[cn] = en

def load_excel(file_bytes: bytes) -> pd.DataFrame:
    """读取 Excel 文件，返回 DataFrame"""
    try:
        from openpyxl import load_workbook
        # 先检查 Excel 结构
        wb = load_workbook(BytesIO(file_bytes))
        print(f"Excel sheet 列表: {wb.sheetnames}")
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            print(f"Sheet '{sheet_name}' 行数: {ws.max_row}, 列数: {ws.max_column}")

        # 读取数据，默认取第一个 sheet
        df = pd.read_excel(BytesIO(file_bytes), sheet_name=0)
        print(f"读取到 {len(df)} 行, 列: {list(df.columns)[:5]}...")
        return df
    except Exception as e:
        print(f"读取 Excel 失败: {e}")
        return pd.DataFrame()

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将中文列名标准化为英文字段名"""
    if df.empty:
        return df

    result_df = df.copy()

    # 中文列名转英文字段名
    rename_map = {}
    for cn_name, en_name in CHINESE_TO_ENGLISH.items():
        if cn_name in result_df.columns:
            rename_map[cn_name] = en_name

    if rename_map:
        result_df = result_df.rename(columns=rename_map)

    return result_df

def merge_data(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """合并两个数据源，按问题单号去重"""
    if df1.empty and df2.empty:
        return pd.DataFrame()

    if df1.empty:
        return df2.copy()

    if df2.empty:
        return df1.copy()

    # 先标准化列名（处理中文列名的情况），这样才能正确去重
    df1_norm = normalize_columns(df1)
    df2_norm = normalize_columns(df2)

    df = pd.concat([df1_norm, df2_norm], ignore_index=True)

    # 按问题单号去重（normalize后列名是英文number）
    if "number" in df.columns:
        df = df.drop_duplicates(subset=["number"], keep="first")

    return df.reset_index(drop=True)

def get_version_list(df: pd.DataFrame) -> List[str]:
    """获取所有有值的发现版本列表"""
    if df.empty or "from_version" not in df.columns:
        return []

    versions = df["from_version"].dropna()
    versions = versions[versions != ""]
    return sorted(versions.unique().tolist())

def filter_by_version(df: pd.DataFrame, version: Optional[str] = None) -> pd.DataFrame:
    """
    按发现版本过滤
    - version=None 或 "全部": 返回所有数据
    - version 有值: 返回 from_version <= 该版本 或 from_version为空 的数据
    """
    if df.empty:
        return df

    if version is None or version == "全部":
        return df

    # 获取所有版本并排序
    versions = df["from_version"].dropna()
    versions = versions[versions != ""]
    unique_versions = sorted(versions.unique().tolist(), reverse=True)

    if version not in unique_versions:
        return df

    # 找到选中版本的位置，返回该位置及之后的版本（更小的版本）
    version_idx = unique_versions.index(version)
    smaller_versions = unique_versions[version_idx:]

    # 返回更小版本 + 空版本的数据
    return df[
        (df["from_version"].isin(smaller_versions)) |
        (df["from_version"].isna()) |
        (df["from_version"] == "")
    ]