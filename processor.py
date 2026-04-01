# processor.py
import pandas as pd
from datetime import datetime, timedelta
from calendar import monthrange
from io import BytesIO
from typing import List, Optional, Tuple, Dict

FIELD_MAPPING = {
    "number": ["问题单号", "问题编号"],
    "title": ["标题", "问题标题"],
    "severity_level": ["严重程度"],
    "status": ["问题状态", "状态"],
    "assigned_to_domain": ["责任服务", "负责域"],
    "from_version": ["发现问题版本"],
    "discover_iteration": ["发现迭代"],
    "created_time": ["问题创建时间"],
    "stage": ["问题阶段"],
    "discovered_time": ["发现时间"],
    "delivery_scenario": ["交付场景"],
    "valid": ["挂起/撤销"],
    "discovered_environment": ["发现环境"],
    "labels": ["标签"],
    "dev_person": ["责任人"],
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

    # discovered_time 使用 created_time 的值
    if "created_time" in result_df.columns:
        result_df["discovered_time"] = result_df["created_time"]

    # Excel status 标准化（值映射）
    # Excel的问题状态值可能包含：待修复、待验收、待确认、定位中、修复
    # 需要映射为di_calculator期望的status值
    if "status" in result_df.columns:
        status_map = {
            "待提交": "待提交",
            "定位中": "定位中",
            "修复": "修复",
            "待验收": "待验收",
            "待确认": "待确认",
            "已关闭": "已关闭",
            "open": "定位中",
            "closed": "已关闭",
            "修复中": "修复",
        }
        result_df["status"] = result_df["status"].map(status_map).fillna(result_df["status"])

    # Excel stage 标准化（值映射）
    # Excel的问题阶段值：待修复、修复中、测试、修复完成
    # 需要映射为di_calculator期望的stage值
    if "stage" in result_df.columns:
        stage_map = {
            "待修复": "待修复",
            "修改中": "修复中",
            "修复中": "修复中",
            "测试": "修复测试",
            "修复完成": "修复完成",
        }
        result_df["stage"] = result_df["stage"].map(stage_map).fillna(result_df["stage"])

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


# ============== 图表相关函数 ==============

def get_month_range(year: int, month: int) -> Tuple[datetime, datetime]:
    """
    根据年份和月份获取日期范围

    Args:
        year: 年份
        month: 月份（1-12）

    Returns:
        (start_date, end_date) 元组，月初 00:00:00 到月末 23:59:59
    """
    # 月初到月末
    _, last_day = monthrange(year, month)
    start_date = datetime(year, month, 1, 0, 0, 0)
    end_date = datetime(year, month, last_day, 23, 59, 59)

    return start_date, end_date


def get_chart_data(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    获取图表所需的数据（已筛选的数据）

    Args:
        df: 已按微服务过滤的数据

    Returns:
        {
            "monthly": 月度分布 DataFrame (columns: ["月份", "问题单数"]),
            "severity": 严重程度分布 DataFrame (columns: ["severity_level", "数量"]),
            "environment": 环境分布 DataFrame (columns: ["discovered_environment", "数量"])
        }
    """
    if df.empty:
        return {
            "monthly": pd.DataFrame(columns=["月份", "问题单数"]),
            "severity": pd.DataFrame(columns=["severity_level", "数量"]),
            "environment": pd.DataFrame(columns=["discovered_environment", "数量"])
        }

    # 1. 月度分布数据（柱状图：展示本月、上月、上上月、>3个月、>6个月）
    monthly_data_list = []
    df_for_charts = df.copy()
    now = datetime.now()

    # 计算本月、上月、上上月的年份和月份（支持跨年）
    current_year = now.year
    current_month = now.month

    # 月度桶：本月、上月、上上月
    month_list = []
    for i in range(3):
        target_month = current_month - i
        target_year = current_year
        while target_month < 1:
            target_month += 12
            target_year -= 1
        month_list.append((target_year, target_month, f"{target_month}月"))

    # >3个月：往前3个月（4-6个月前）
    months_3m = []
    for i in range(3, 6):
        target_month = current_month - i
        target_year = current_year
        while target_month < 1:
            target_month += 12
            target_year -= 1
        months_3m.append((target_year, target_month))

    # >6个月：7个月前及更早
    months_6m = []
    for i in range(6, 13):
        target_month = current_month - i
        target_year = current_year
        while target_month < 1:
            target_month += 12
            target_year -= 1
        months_6m.append((target_year, target_month))

    # 月度桶和>3个月、>6个月使用相同的数据副本，避免重复计算
    if not df_for_charts.empty and "discovered_time" in df_for_charts.columns:
        df_temp = df_for_charts.copy()
        df_temp = df_temp.reset_index(drop=True)
        df_temp["discovered_time_dt"] = pd.to_datetime(df_temp["discovered_time"], errors="coerce")
        dt_series = df_temp["discovered_time_dt"]

        # 已统计的日期索引集合
        counted_indices = set()

        # 月度桶
        for year, month, month_label in month_list:
            start_date, end_date = get_month_range(year, month)
            mask = (
                (dt_series >= start_date) &
                (dt_series <= end_date)
            )
            count = mask.sum()
            monthly_data_list.append({"月份": month_label, "问题单数": int(count)})
            counted_indices.update(df_temp[mask].index.tolist())

        # >3个月
        mask_3m = pd.Series([False] * len(df_temp), index=df_temp.index)
        for year, month in months_3m:
            start_date, end_date = get_month_range(year, month)
            mask_3m |= (
                (dt_series >= start_date) &
                (dt_series <= end_date)
            )
        # 排除已统计的
        mask_3m = mask_3m & ~df_temp.index.isin(counted_indices)
        count_3m = mask_3m.sum()
        monthly_data_list.append({"月份": ">3个月", "问题单数": int(count_3m)})
        counted_indices.update(df_temp[mask_3m].index.tolist())

        # >6个月：包括指定月份范围的 + discovered_time 为空的
        mask_6m = pd.Series([False] * len(df_temp), index=df_temp.index)
        for year, month in months_6m:
            start_date, end_date = get_month_range(year, month)
            mask_6m |= (
                (dt_series >= start_date) &
                (dt_series <= end_date)
            )
        # 排除已统计的
        mask_6m = mask_6m & ~df_temp.index.isin(counted_indices)
        # discovered_time 为空的也计入 >6个月
        null_mask = dt_series.isna()
        count_6m = mask_6m.sum() + null_mask.sum()
        monthly_data_list.append({"月份": ">6个月", "问题单数": int(count_6m)})
    else:
        count_3m = 0
        count_6m = 0

    monthly_df = pd.DataFrame(monthly_data_list)

    # 2. 严重程度分布
    df_for_severity = df.copy()
    if not df_for_severity.empty and "severity_level" in df_for_severity.columns:
        severity_df = df_for_severity.groupby("severity_level").size().reset_index(name="数量")
        # 按致命>严重>一般>提示排序
        severity_order = {"致命": 0, "严重": 1, "一般": 2, "提示": 3}
        severity_df["排序"] = severity_df["severity_level"].map(severity_order).fillna(99)
        severity_df = severity_df.sort_values("排序").drop(columns=["排序"])
    else:
        severity_df = pd.DataFrame(columns=["severity_level", "数量"])

    # 3. 环境分布
    df_for_env = df.copy()
    if not df_for_env.empty and "discovered_environment" in df_for_env.columns:
        env_df = df_for_env.groupby("discovered_environment").size().reset_index(name="数量")
    else:
        env_df = pd.DataFrame(columns=["discovered_environment", "数量"])

    return {
        "monthly": monthly_df,
        "severity": severity_df,
        "environment": env_df
    }