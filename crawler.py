# crawler.py
import time
import requests
import urllib3
from typing import Dict, Optional
from config import BASE_URL, get_default_headers, build_auth_headers

# 禁用 SSL 证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BugCrawler:
    def __init__(self, auth_config: Dict[str, str], domain_ids: list = None):
        self.base_url = BASE_URL
        self.auth = auth_config
        self.session = requests.Session()
        # 默认支持 domain 11 和 33921，可配置
        self.domain_ids = domain_ids or [11, 33921]

    def fetch_all_domains(self) -> Optional[bytes]:
        """爬取所有 domain 的数据并合并"""
        all_data = []
        for domain_id in self.domain_ids:
            data = self.fetch_data(domain_id)
            if data:
                all_data.append(data)
        return all_data if all_data else None

    def _get_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        return build_auth_headers(
            cookie=self.auth.get("cookie", ""),
            authorization=self.auth.get("authorization", ""),
            user_id=self.auth.get("x_titan_userid", "")
        )

    def build_export_payload(self, domain_id: int, source_type: str = "with_assigned_domain") -> Dict:
        """构建导出请求体"""
        request_tag = str(int(time.time() * 1000))

        base_conditions = {
            "sorts": [
                {"key": "updated_time", "value": "desc"},
                {"key": "updated_time", "value": "desc"}
            ],
            "filters": [
                {"key": "scene", "operator": "||", "value": ["issue_bug"]},
                {"key": "current_domain", "operator": "||", "value": [domain_id]},
                {"key": "status", "operator": "||", "value": [
                    "ISSUE_STATUS_SUBMIT",
                    "ISSUE_STATUS_ANALYSIS",
                    "ISSUE_STATUS_FIXING",
                    "ISSUE_STATUS_VERIFYING",
                    "ISSUE_STATUS_REGRESSION_TEST",
                    "ISSUE_STATUS_RETURNED"
                ]},
                {"key": "category", "operator": "||", "value": ["04000001", "04000002", "04000003"]}
            ],
            "with_children": True,
            "view": "receive",
            "data_type": "tree"
        }

        if source_type == "with_assigned_domain":
            base_conditions["assigned_domain"] = {
                "value": [{"id": domain_id, "type": "Domain"}],
                "operator": "||",
                "convolution": "down"
            }

        return {
            "source_id": domain_id,
            "source_title": f"Domain {domain_id}",
            "source_type": "Domain",
            "language": "zh",
            "exportSize": 120,
            "conditions": base_conditions,
            "select": [
                "number", "title", "valid", "found_in_domain", "discovered_environment",
                "assigned_to_domain", "repair_plan", "raised_by", "head_owner",
                "current_owner", "discovered_stage", "severity_level", "online_sources",
                "stage", "status", "discovered_time", "discover_iteration", "labels",
                "issue_closed_way", "testOwners", "root_cause", "operate_record",
                "created_time", "ISSUE_STATUS_SUBMIT", "ISSUE_STATUS_ANALYSIS",
                "ISSUE_STAGE_PLANNING", "ISSUE_STATUS_FIXING", "ISSUE_STAGE_CODE",
                "ISSUE_STAGE_TEST", "ISSUE_STAGE_DONE", "ISSUE_STATUS_VERIFYING",
                "ISSUE_STATUS_RETURNED", "remark", "dev_person", "delivery_scenario", "from_version"
            ],
            "request_tag": request_tag,
            "fieldId": [1, 2, 4, 5, 6, 7, 264, 9, 11, 12, 14, 15, 17, 18, 19, 24, 263, 27, 34, 268, 67, 68, 48, 39, 40, 41, 42, 43, 44, 45, 46, 47, 474]
        }

    def trigger_export(self, domain_id: int, source_type: str = "with_assigned_domain") -> Optional[str]:
        """触发导出，返回 file_id"""
        url = f"{self.base_url}/vision-excel/api/export/issue/v2?requestTag={int(time.time() * 1000)}"
        payload = self.build_export_payload(domain_id, source_type)

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
                verify=False  # 禁用 SSL 证书验证（公司内网环境）
            )
            response.raise_for_status()
            data = response.json()
            # 解析响应获取 file_id
            if data.get("code") == 0 or data.get("success"):
                return data.get("data", {}).get("file_id")
            return None
        except Exception as e:
            print(f"触发导出失败: {e}")
            return None

    def query_file_status(self, file_id: int) -> Optional[str]:
        """查询文件状态"""
        url = f"{self.base_url}/vision-excel/api/query/file_download_record?requestTag={int(time.time() * 1000)}"

        try:
            response = self.session.post(
                url,
                json={"filters": [{"key": "id", "operator": "||", "value": [file_id]}]},
                headers=self._get_headers(),
                timeout=30,
                verify=False  # 禁用 SSL 证书验证
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                records = data.get("data", [])
                if records:
                    return records[0].get("status")
            return None
        except Exception as e:
            print(f"查询文件状态失败: {e}")
            return None

    def download_file(self, file_id: str, domain_id: int = 11) -> Optional[bytes]:
        """下载 Excel 文件"""
        url = f"{self.base_url}/vision-excel/api/query/issue/download_item?domain_id={domain_id}&requestTag={int(time.time() * 1000)}"

        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=60,
                verify=False  # 禁用 SSL 证书验证
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"下载文件失败: {e}")
            return None

    def wait_and_download(self, file_id: str, domain_id: int = 11, timeout: int = 60) -> Optional[bytes]:
        """轮询等待文件就绪后下载"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.query_file_status(file_id)
            if status == "ready":
                return self.download_file(file_id, domain_id)
            time.sleep(2)  # 每2秒轮询一次

        print("等待文件超时")
        return None

    def fetch_data(self, domain_id: int = 11, source_type: str = "with_assigned_domain") -> Optional[bytes]:
        """完整流程：触发导出 → 等待 → 下载"""
        file_id = self.trigger_export(domain_id, source_type)
        if not file_id:
            print(f"获取 file_id 失败 (domain {domain_id})")
            return None

        return self.wait_and_download(file_id, domain_id)