# di_calculator.py
import pandas as pd
from typing import Dict, Optional

# DI 权重配置
SEVERITY_DI = {
    "致命": 10,
    "严重": 3,
    "一般": 1,
    "提示": 0.1
}

# SLA 阈值（天）
SLA_THRESHOLDS = {
    "致命": 7,
    "严重": 14,
    "一般": 30,
    "提示": 30
}

# 合格标准阈值
QUALIFICATION_THRESHOLDS = {
    "云服务": 20,
    "微服务": 5
}

# CES 微服务列表（模糊匹配）
CES_MICROSERVICES = [
    "CES告警",
    "CES公共开发",
    "CES",
    "CES监控",
    "CES Agent",
    "CES API",
    "CES测试",
    "CES资料",
    "CES运维变更",
    "CES-Console"
]

# 生产环境状态（待验收/修复完成不算 DI）
PRODUCTION_EXCLUDED_STATUS = ["待验收", "修复完成"]

# 生产环境状态（定位中/修复中按 SLA 计算）
PRODUCTION_SLA_STATUS = ["定位中", "修复中"]

# 生产环境状态（待提交按创建时间）
PRODUCTION_SUBMIT_STATUS = ["待提交"]

# 交付场景（门禁不算）
DELIVERY_EXCLUDED = ["HCS"]

def get_severity_di(severity: str) -> float:
    """获取严重程度对应的 DI 权重"""
    return SEVERITY_DI.get(severity, 0)

def get_sla_threshold(severity: str) -> int:
    """获取严重程度对应的 SLA 阈值（天）"""
    return SLA_THRESHOLDS.get(severity, 30)

def is_microservice(name: str) -> bool:
    """判断是否为 CES 微服务（模糊匹配）"""
    if not name or pd.isna(name):
        return False

    name_str = str(name)
    for ms in CES_MICROSERVICES:
        if ms in name_str or name_str in ms:
            return True
    return False

def filter_production_issues(df: pd.DataFrame) -> pd.DataFrame:
    """
    CCB 挂起过滤
    - 非生产环境 + 挂起 → 剔除
    - 生产环境 → 保留
    """
    if df.empty:
        return df

    result = df.copy()

    # 非生产环境且挂起/撤销的问题单剔除
    mask = (
        (result.get("discovered_environment") == "非生产环境") &
        (result.get("valid") == "挂起")
    )
    result = result[~mask]

    return result

def apply_delivery_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """
    交付场景处理
    - HCS → DI 不算
    - 其他/空 → 正常算
    """
    if df.empty or "delivery_scenario" not in df.columns:
        return df

    result = df.copy()

    # 为 HCS 的问题单设置 DI=0
    hcs_mask = result["delivery_scenario"] == "HCS"
    result.loc[hcs_mask, "_di_contribution"] = 0

    return result

def calculate_di_for_issue(severity: str) -> float:
    """计算单个问题的 DI 值"""
    return get_severity_di(severity)

def calculate_cloud_di(df: pd.DataFrame) -> Dict:
    """计算云服务级别 DI"""
    if df.empty:
        return {"di": 0, "issue_count": 0, "qualified": True}

    total_di = 0
    for _, row in df.iterrows():
        total_di += calculate_di_for_issue(row.get("severity_level", ""))

    issue_count = len(df)
    qualified = total_di < QUALIFICATION_THRESHOLDS["云服务"]

    return {
        "di": round(total_di, 1),
        "issue_count": issue_count,
        "qualified": qualified
    }

def calculate_microservice_di(df: pd.DataFrame) -> pd.DataFrame:
    """按微服务分组统计 DI"""
    if df.empty or "assigned_to_domain" not in df.columns:
        return pd.DataFrame()

    # 只保留 CES 微服务
    ces_df = df[df["assigned_to_domain"].apply(is_microservice)].copy()

    if ces_df.empty:
        return pd.DataFrame(columns=["assigned_to_domain", "di_sum", "issue_count", "qualified"])

    # 按责任服务分组
    grouped = ces_df.groupby("assigned_to_domain")

    results = []
    for domain, group in grouped:
        di_sum = sum(calculate_di_for_issue(row.get("severity_level", "")) for _, row in group.iterrows())
        issue_count = len(group)
        qualified = di_sum < QUALIFICATION_THRESHOLDS["微服务"]

        results.append({
            "assigned_to_domain": domain,
            "di_sum": round(di_sum, 1),
            "issue_count": issue_count,
            "qualified": qualified
        })

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("di_sum", ascending=False)
    return result_df.reset_index(drop=True)

def get_issue_detail_url(issue_number: str) -> str:
    """生成问题单详情跳转链接"""
    return f"https://clouddevops.huawei.com/#/bug/{issue_number}"