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

        # 根据 source_type 决定是否带 assigned_domain
        if source_type == "with_assigned_domain":
            base_conditions["assigned_domain"] = {
                "value": [{"id": domain_id, "type": "Domain"}],
                "operator": "||",
                "convolution": "down"
            }

        return {
            "source_id": domain_id,
            "source_title": "Cloud Eye",
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

    def trigger_export(self, domain_id: int, source_type: str = "with_assigned_domain") -> Optional[int]:
        """触发导出，返回 file_id"""
        # 每次 export 前都先调用 GET 接口（浏览器行为）
        config_url = f"{self.base_url}/vision-excel/api/query/issue/download_item?domain_id={domain_id}&requestTag={int(time.time() * 1000)}"
        try:
            self.session.get(config_url, headers=self._get_headers(), timeout=30, verify=False)
            print(f"[Domain {domain_id}] GET download_item 完成")
        except Exception:
            pass

        url = f"{self.base_url}/vision-excel/api/export/issue/v2?requestTag={int(time.time() * 1000)}"
        payload = self.build_export_payload(domain_id, source_type)

        # 打印关键参数
        has_assigned = "assigned_domain" in payload.get("conditions", {})
        print(f"[Domain {domain_id}] 导出请求: source_type={source_type}, has_assigned_domain={has_assigned}")

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
                verify=False
            )

            if response.status_code != 200:
                print(f"[Domain {domain_id}] export 失败: HTTP {response.status_code}")
                return None

            data = response.json()
            if data.get("code") == 200:
                file_id = data.get("data", {}).get("id")
                print(f"[Domain {domain_id}] export 成功: file_id={file_id}")
                return file_id
            print(f"[Domain {domain_id}] export 失败: {data}")
            return None
        except Exception as e:
            print(f"[Domain {domain_id}] export 异常: {e}")
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
                verify=False
            )
            data = response.json()

            if data.get("code") == 200:
                result = data.get("data", {}).get("result", [])
                if result:
                    status = result[0].get("status")
                    print(f"[文件 {file_id}] 状态: {status}")
                    return status
            print(f"[文件 {file_id}] 查询失败: {data}")
            return None
        except Exception as e:
            print(f"[文件 {file_id}] 查询异常: {e}")
            return None

    def download_file(self, file_id: int, domain_id: int = 11) -> Optional[bytes]:
        """下载 Excel 文件"""
        url = f"{self.base_url}/vision-excel/api/download/workitem?id={file_id}"
        print(f"[文件 {file_id}] 下载 URL: {url}")
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=60,
                verify=False
            )
            print(f"[文件 {file_id}] 状态码: {response.status_code}, 大小: {len(response.content)}")
            # 200 和 201 都是成功响应
            if response.status_code in (200, 201) and not response.content.startswith(b'<'):
                return response.content
            print(f"[文件 {file_id}] 响应前100字节: {response.content[:100]}")
            return None
        except Exception as e:
            print(f"[文件 {file_id}] 异常: {e}")
            return None

    def wait_and_download(self, file_id: int, domain_id: int = 11, timeout: int = 120) -> Optional[bytes]:
        """轮询等待文件就绪后下载"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.query_file_status(file_id)

            if status == "FILE_STATUS_GENERATED":
                return self.download_file(file_id, domain_id)

            time.sleep(3)

        return None

    def fetch_data(self, domain_id: int = 11, source_type: str = "with_assigned_domain") -> Optional[bytes]:
        """完整流程：触发导出 → 等待 → 下载"""
        file_id = self.trigger_export(domain_id, source_type)
        if not file_id:
            return None

        return self.wait_and_download(file_id, domain_id)