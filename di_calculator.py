# di_calculator.py
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple

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

# 交付场景（HCS 不算 DI）
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
    CCB 挂起过滤（预处理阶段）
    - 非生产环境 + 挂起 → 剔除
    - 生产环境 → 保留

    注意：此函数仅处理 CCB 挂起规则
    状态规则（哪些状态算DI）在 calculate_di_for_issue 中单独处理
    """
    if df.empty:
        return df

    result = df.copy()

    # 非生产环境且挂起/撤销的问题单剔除
    mask = (
        (result.get("discovered_environment") == "非生产环境") &
        (result.get("valid") == "挂起")
    )
    result = result.loc[~mask]

    return result


def is_delivery_excluded(delivery_scenario: str) -> bool:
    """判断交付场景是否排除 DI 计算"""
    if pd.isna(delivery_scenario) or str(delivery_scenario).strip() == "":
        return False  # 空 = 正常算
    return str(delivery_scenario) in DELIVERY_EXCLUDED


def should_count_di(status: str, stage: str, discovered_environment: str) -> Tuple[bool, str]:
    """
    判断问题单是否应该统计 DI

    Returns:
        (should_count, reason)
    """
    if pd.isna(status):
        return False, "status为空"

    status = str(status).strip()
    stage = str(stage).strip() if not pd.isna(stage) else ""
    env = str(discovered_environment).strip() if not pd.isna(discovered_environment) else ""

    # 非生产环境
    if env == "非生产环境":
        # 待提交/空 → 不统计
        if status == "待提交" and stage == "":
            return False, "非生产-待提交"
        # 已关闭/空 → 不统计
        if status == "已关闭" and stage == "":
            return False, "非生产-已关闭"
        # 待确认/空 → 统计
        if status == "待确认" and stage == "":
            return True, "非生产-待确认"
        # 定位中/空 → 统计
        if status == "定位中" and stage == "":
            return True, "非生产-定位中"
        # 修复/待修复 → 统计
        if status == "修复" and stage == "待修复":
            return True, "非生产-待修复"
        # 修复/修复中 → 统计
        if status == "修复" and stage == "修复中":
            return True, "非生产-修复中"
        # 修复/修复测试 → 统计
        if status == "修复" and stage == "修复测试":
            return True, "非生产-修复测试"
        # 修复/修复完成 → 统计
        if status == "修复" and stage == "修复完成":
            return True, "非生产-修复完成"
        # 待验收/空 → 统计
        if status == "待验收" and stage == "":
            return True, "非生产-待验收"
        # 其他情况 → 不统计
        return False, "非生产-其他"

    # 生产环境
    if env == "生产环境":
        # 待提交/空 → 不统计
        if status == "待提交" and stage == "":
            return False, "生产-待提交"
        # 待验收/空 → 不统计
        if status == "待验收" and stage == "":
            return False, "生产-待验收"
        # 已关闭/空 → 不统计
        if status == "已关闭" and stage == "":
            return False, "生产-已关闭"
        # 修复/修复完成 → 不统计
        if status == "修复" and stage == "修复完成":
            return False, "生产-修复完成"
        # 待确认/空 → 统计
        if status == "待确认" and stage == "":
            return True, "生产-待确认"
        # 定位中/空 → 统计
        if status == "定位中" and stage == "":
            return True, "生产-定位中"
        # 修复/待修复 → 统计
        if status == "修复" and stage == "待修复":
            return True, "生产-待修复"
        # 修复/修复中 → 统计
        if status == "修复" and stage == "修复中":
            return True, "生产-修复中"
        # 修复/修复测试 → 统计
        if status == "修复" and stage == "修复测试":
            return True, "生产-修复测试"
        # 其他情况 → 不统计
        return False, "生产-其他"

    # 环境为空或其他未知情况
    # 已关闭状态，无论环境如何都不统计
    if status == "已关闭":
        return False, "环境未知-已关闭"
    # 其他状态，环境未知时默认统计
    return True, "环境未知-统计"


def calculate_di_for_issue(row: pd.Series, current_time: datetime) -> float:
    """
    计算单个问题单的 DI 值

    规则：
    1. 判断是否统计 DI（根据 status + stage + discovered_environment）
    2. 判断是否 SLA 超期（当前时间 - 发现时间 > 阈值）
    3. 判断交付场景（HCS 不算）
    """
    severity = row.get("severity_level", "")
    status = row.get("status", "")
    stage = row.get("stage", "")
    discovered_env = row.get("discovered_environment", "")
    discovered_time = row.get("discovered_time", None)
    delivery_scenario = row.get("delivery_scenario", "")

    # 1. 判断是否应该统计
    should_count, reason = should_count_di(status, stage, discovered_env)
    if not should_count:
        return 0.0

    # 2. 交付场景判断
    if is_delivery_excluded(delivery_scenario):
        return 0.0

    # 3. SLA 超期判断
    threshold = get_sla_threshold(severity)

    # 如果没有发现时间，无法判断 SLA，默认按超期处理（算 DI）
    if pd.isna(discovered_time) or str(discovered_time).strip() == "":
        # 无法判断 SLA，默认算 DI
        return get_severity_di(severity)

    # 解析发现时间
    try:
        if isinstance(discovered_time, str):
            # 尝试解析字符串时间
            discovered_dt = pd.to_datetime(discovered_time)
        else:
            discovered_dt = discovered_time

        days_elapsed = (current_time - discovered_dt).total_seconds() / (24 * 3600)

        if days_elapsed > threshold:
            return get_severity_di(severity)
        else:
            return 0.0  # SLA 未超期
    except Exception:
        # 解析失败，默认算 DI
        return get_severity_di(severity)


def calculate_cloud_di(df: pd.DataFrame) -> Dict:
    """计算云服务级别 DI"""
    if df.empty:
        return {"di": 0, "issue_count": 0, "qualified": True, "debug": {"di_0": 0, "di_gt_0": 0}}

    # 只保留 CES 微服务计算 DI
    ces_df = df[df["assigned_to_domain"].apply(is_microservice)].copy()

    current_time = datetime.now()
    total_di = 0
    issue_count = len(df)  # 总问题单统计所有数据
    debug_counts = {"di_0": 0, "di_gt_0": 0}

    for _, row in ces_df.iterrows():
        di = calculate_di_for_issue(row, current_time)
        total_di += di
        if di > 0:
            debug_counts["di_gt_0"] += 1
        else:
            debug_counts["di_0"] += 1

    qualified = total_di < QUALIFICATION_THRESHOLDS["云服务"]

    return {
        "di": round(total_di, 1),
        "issue_count": issue_count,
        "qualified": qualified,
        "debug": debug_counts
    }


def calculate_microservice_di(df: pd.DataFrame) -> pd.DataFrame:
    """按微服务分组统计 DI"""
    if df.empty or "assigned_to_domain" not in df.columns:
        return pd.DataFrame()

    # 只保留 CES 微服务
    ces_df = df[df["assigned_to_domain"].apply(is_microservice)].copy()

    if ces_df.empty:
        return pd.DataFrame(columns=["assigned_to_domain", "di_sum", "issue_count", "qualified"])

    current_time = datetime.now()

    # 按责任服务分组
    grouped = ces_df.groupby("assigned_to_domain")

    results = []
    for domain, group in grouped:
        di_sum = sum(calculate_di_for_issue(row, current_time) for _, row in group.iterrows())
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


def calculate_microservice_di_with_count(df: pd.DataFrame) -> pd.DataFrame:
    """
    按微服务分组统计 DI
    问题单数 = 按 DI 统计规则过滤后的问题单数（DI > 0）
    """
    if df.empty or "assigned_to_domain" not in df.columns:
        return pd.DataFrame()

    # 只保留 CES 微服务
    ces_df = df[df["assigned_to_domain"].apply(is_microservice)].copy()

    if ces_df.empty:
        return pd.DataFrame(columns=["assigned_to_domain", "di_sum", "issue_count", "qualified"])

    current_time = datetime.now()

    # 按责任服务分组
    grouped = ces_df.groupby("assigned_to_domain")

    results = []
    for domain, group in grouped:
        # 计算每个问题单的 DI
        di_list = [calculate_di_for_issue(row, current_time) for _, row in group.iterrows()]
        di_sum = sum(di_list)
        # 问题单数 = DI > 0 的问题单数
        issue_count = sum(1 for d in di_list if d > 0)
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
