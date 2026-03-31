# crawler.py
import time
import requests
import urllib3
from typing import Dict, Optional, List
from config import BASE_URL, get_default_headers, build_auth_headers

# 禁用 SSL 证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Status 映射
STATUS_MAPPING = {
    "ISSUE_STATUS_SUBMIT": "待提交",
    "ISSUE_STATUS_ANALYSIS": "定位中",
    "ISSUE_STATUS_FIXING": "修复",
    "ISSUE_STATUS_VERIFYING": "待验收",
    "ISSUE_STATUS_REGRESSION_TEST": "已关闭",
    "ISSUE_STATUS_RETURNED": "待确认",
}

# Stage 映射
STAGE_MAPPING = {
    "ISSUE_STAGE_PLANNING": "待修复",
    "ISSUE_STAGE_CODE": "修复中",
    "ISSUE_STAGE_TEST": "修复测试",
    "ISSUE_STAGE_DONE": "修复完成",
}

# Severity 映射
SEVERITY_MAPPING = {
    "04003001": "提示",
    "04003002": "一般",
    "04003003": "严重",
    "04003004": "致命",
}


class BugCrawler:
    def __init__(self, auth_config: Dict[str, str], domain_ids: list = None):
        self.base_url = BASE_URL
        self.auth = auth_config
        self.session = requests.Session()
        self.domain_ids = domain_ids or [11, 33921]

    def _get_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        return build_auth_headers(
            cookie=self.auth.get("cookie", ""),
            authorization=self.auth.get("authorization", ""),
            user_id=self.auth.get("x_titan_userid", "")
        )

    def _build_payload(self, domain_id: int, page: int = 1, page_size: int = 100) -> Dict:
        """构建查询请求体"""
        return {
            "sorts": [
                {"key": "updated_time", "value": "desc"},
                {"key": "updated_time", "value": "desc"}
            ],
            "filters": [
                {
                    "key": "scene",
                    "operator": "||",
                    "value": ["issue_bug"]
                },
                {
                    "key": "current_domain",
                    "operator": "||",
                    "value": [domain_id]
                },
                {
                    "key": "status",
                    "operator": "||",
                    "value": [
                        "ISSUE_STATUS_SUBMIT",
                        "ISSUE_STATUS_ANALYSIS",
                        "ISSUE_STATUS_FIXING",
                        "ISSUE_STATUS_VERIFYING",
                        "ISSUE_STATUS_REGRESSION_TEST",
                        "ISSUE_STATUS_RETURNED"
                    ]
                },
                {
                    "key": "assigned_domain",
                    "value": [
                        {"id": domain_id, "type": "Domain"}
                    ],
                    "operator": "||",
                    "convolution": "down"
                },
                {
                    "key": "category",
                    "operator": "||",
                    "value": ["04000001", "04000002", "04000003"]
                }
            ],
            "pagination": {
                "current_page": page,
                "page_size": str(page_size)
            },
            "with_children": True,
            "view": "receive",
            "data_type": "tree",
            "request_tag": int(time.time() * 1000)
        }

    def _parse_issue(self, item: Dict) -> Dict:
        """解析单条问题单数据"""
        # 处理 status 和 stage
        api_status = item.get("status", "")
        api_stage = item.get("stage", "") or ""

        # 获取 status 映射
        status_text = STATUS_MAPPING.get(api_status, api_status)

        # 如果是 FIXING 状态，需要结合 stage 确定 stage 的中文值
        # status 保持为 "修复"，stage 映射为中文
        stage = ""
        if api_status == "ISSUE_STATUS_FIXING" and api_stage:
            stage = STAGE_MAPPING.get(api_stage, api_stage)

        # 处理 severity
        severity_code = item.get("severity", "")
        severity = SEVERITY_MAPPING.get(severity_code, severity_code)

        # 处理责任服务
        assigned_domain = item.get("assigned_domain", {})
        assigned_to_domain = assigned_domain.get("title", "") if assigned_domain else ""

        # 处理发现环境（优先使用 titleZh 中文，fallback 到 title）
        discovered_env = item.get("discovered_environment", {}) or {}
        discovered_environment = discovered_env.get("titleZh", "") or discovered_env.get("title", "")

        # 处理研发责任人（优先使用 current_owners，fallback 到 develop_owners）
        current_owners = item.get("current_owners", []) or []
        develop_owners = item.get("develop_owners", []) or []
        owners = current_owners if current_owners else develop_owners
        dev_person = owners[0].get("name", "") if owners else ""

        # 处理测试责任人
        test_owners = item.get("test_owners", []) or []
        test_owners_text = test_owners[0].get("name", "") if test_owners else ""

        # 处理发现问题版本
        from_version = item.get("fromVersion", {}) or {}
        from_version_text = from_version.get("title", "") or from_version.get("number", "")

        # 处理有效标志
        valid = item.get("valid")
        valid_text = "挂起" if valid == 0 else ("有效" if valid == 1 else "")

        return {
            "number": item.get("number", ""),
            "title": item.get("title", ""),
            "severity_level": severity,
            "status": status_text,
            "stage": stage,
            "assigned_to_domain": assigned_to_domain,
            "from_version": from_version_text,
            "discover_iteration": item.get("iteration", ""),
            "created_time": item.get("created_time", ""),
            "discovered_time": item.get("updated_time", ""),  # 使用 updated_time 作为 discovered_time
            "delivery_scenario": item.get("deliveryScenario", ""),
            "valid": valid_text,
            "discovered_environment": discovered_environment,
            "labels": ",".join([lbl.get("name", "") for lbl in item.get("labels", []) if lbl]),
            "dev_person": dev_person,
            "testOwners": test_owners_text,
        }

    def fetch_page(self, domain_id: int, page: int = 1, page_size: int = 100) -> Optional[Dict]:
        """查询单页数据"""
        url = f"{self.base_url}/vision-defect-management/api/query/issues"
        payload = self._build_payload(domain_id, page, page_size)

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
                verify=False
            )

            if response.status_code != 200:
                print(f"[Domain {domain_id}] 请求失败: HTTP {response.status_code}")
                return None

            data = response.json()
            if data.get("code") == 200:
                return data.get("data", {})
            print(f"[Domain {domain_id}] 查询失败: {data}")
            return None
        except Exception as e:
            print(f"[Domain {domain_id}] 查询异常: {e}")
            return None

    def fetch_all_data(self, domain_id: int) -> Optional[List[Dict]]:
        """查询单个 domain 的所有数据（分页）"""
        all_issues = []
        page = 1
        page_size = 100
        total_records = 0

        while True:
            result_data = self.fetch_page(domain_id, page, page_size)
            if not result_data:
                break

            result_list = result_data.get("result", [])
            pagination = {
                "total_records": result_data.get("total_records", 0),
                "total_pages": result_data.get("total_pages", 1),
                "current_page": result_data.get("current_page", 1),
            }

            if page == 1:
                total_records = pagination["total_records"]
                print(f"[Domain {domain_id}] 总记录数: {total_records}, 总页数: {pagination['total_pages']}")

            for item in result_list:
                parsed = self._parse_issue(item)
                all_issues.append(parsed)

            if page >= pagination["total_pages"]:
                break

            page += 1

        print(f"[Domain {domain_id}] 获取到 {len(all_issues)} 条数据")
        return all_issues if all_issues else None

    def fetch_all_domains(self) -> Optional[List[Dict]]:
        """爬取所有 domain 的数据并合并"""
        all_data = []
        for domain_id in self.domain_ids:
            domain_data = self.fetch_all_data(domain_id)
            if domain_data:
                all_data.extend(domain_data)
        return all_data if all_data else None
