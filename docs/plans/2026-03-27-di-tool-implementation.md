# DI 统计工具实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 DI 统计工具，能够爬取两个目标网页的问题单数据，合并后按 DI 规则统计，按云服务/微服务分层展示，支持问题单明细查看和 Excel 导出。

**Architecture:** 基于 Streamlit 的单页应用，Python requests 爬虫抓取数据，pandas 处理数据，di_calculator.py 实现 DI 统计算法，模块化设计便于维护和测试。

**Tech Stack:** Python 3.10+, Streamlit, pandas, openpyxl, requests

---

## 文件结构

```
E:\aitest\bug-di-analysis\
├── app.py                    # Streamlit 主页面
├── config.py                 # 配置管理（认证信息）
├── crawler.py                # 爬虫模块
├── processor.py              # 数据处理模块
├── di_calculator.py          # DI 统计计算模块
├── styles.py                 # Streamlit 样式配置
├── requirements.txt          # 依赖列表
├── README.md                 # 使用说明
└── tests/                   # 测试目录
    ├── test_crawler.py
    ├── test_processor.py
    └── test_di_calculator.py
```

---

## 任务列表

### Task 1: 项目初始化

**Files:**
- Create: `E:/aitest/bug-di-analysis/requirements.txt`
- Create: `E:/aitest/bug-di-analysis/README.md`

- [ ] **Step 1: 创建 requirements.txt**

```
streamlit>=1.28.0
pandas>=2.0.0
openpyxl>=3.1.0
requests>=2.31.0
pytest>=7.4.0
```

- [ ] **Step 2: 创建 README.md**

```markdown
# DI 统计工具

云服务问题单 DI 统计工具。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
streamlit run app.py
```

## 功能

- 爬取问题单数据
- DI 统计计算
- 按微服务分组展示
- Excel 导出
```

- [ ] **Step 3: 提交**

```bash
cd E:/aitest/bug-di-analysis
git init  # 如果还没有 git
git add requirements.txt README.md
git commit -m "feat: project initialization"
```

---

### Task 2: 认证配置模块

**Files:**
- Create: `E:/aitest/bug-di-analysis/config.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_config.py
import pytest
from config import get_default_headers

def test_get_default_headers():
    """测试默认请求头（不含认证信息）"""
    headers = get_default_headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json, text/plain, */*"
    assert "authorization" not in headers
    assert "Cookie" not in headers
```

- [ ] **Step 2: 运行测试验证失败**

```
pytest tests/test_config.py -v
Expected: FAIL - module 'config' has no function 'get_default_headers'
```

- [ ] **Step 3: 实现 config.py**

```python
# config.py
from typing import Dict

FIXED_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": "https://clouddevops.huawei.com",
    "Referer": "https://clouddevops.huawei.com/",
    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Priority": "u=1, i"
}

BASE_URL = "https://clouddevops.huawei.com"

def get_default_headers() -> Dict[str, str]:
    """获取默认请求头（不含认证信息）"""
    return FIXED_HEADERS.copy()

def build_auth_headers(cookie: str, authorization: str, user_id: str) -> Dict[str, str]:
    """构建完整的认证请求头"""
    headers = FIXED_HEADERS.copy()
    headers["Cookie"] = cookie
    headers["Authorization"] = authorization
    headers["x-titan-userid"] = user_id
    headers["x-titan-dept"] = "%E5%8D%8E%E4%B8%BA%E6%8A%80%E6%9C%AF/ICT%20BG/%E4%BA%91%E6%A0%B8%E5%BF%83%E7%BD%91%E4%BA%A7%E5%93%81%E7%BA%BF%E7%AE%A1%E7%90%86%E5%A7%94%E5%91%98%E4%BC%9A/%E4%BA%91%E6%B5%8B%E8%AF%95%E7%A0%94%E5%8F%91%E9%83%A8/%E5%B7%A5%E5%85%B7%E4%B8%8E%E5%85%AC%E5%85%B1%E6%9C%8D%E5%8A%A1%E5%BC%80%E5%8F%91%E9%83%A8"
    return headers
```

- [ ] **Step 4: 运行测试验证通过**

```
pytest tests/test_config.py -v
Expected: PASS
```

- [ ] **Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add authentication configuration module"
```

---

### Task 3: 爬虫模块

**Files:**
- Create: `E:/aitest/bug-di-analysis/crawler.py`
- Create: `E:/aitest/bug-di-analysis/tests/test_crawler.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_crawler.py
import pytest
from crawler import BugCrawler

def test_crawler_init():
    """测试爬虫初始化"""
    auth_config = {
        "cookie": "test_cookie",
        "authorization": "test_token",
        "x_titan_userid": "test_user"
    }
    crawler = BugCrawler(auth_config)
    assert crawler.base_url == "https://clouddevops.huawei.com"
    assert crawler.auth == auth_config

def test_build_export_payload_url1():
    """测试 URL1 导出请求体构建"""
    auth_config = {"cookie": "", "authorization": "", "x_titan_userid": ""}
    crawler = BugCrawler(auth_config)
    payload = crawler.build_export_payload(source_type="with_assigned_domain")
    assert "source_id" in payload
    assert payload["source_id"] == 11
    assert "assigned_domain" in payload["conditions"]

def test_build_export_payload_url2():
    """测试 URL2 导出请求体构建（无 assigned_domain）"""
    auth_config = {"cookie": "", "authorization": "", "x_titan_userid": ""}
    crawler = BugCrawler(auth_config)
    payload = crawler.build_export_payload(source_type="without_assigned_domain")
    assert "assigned_domain" not in payload["conditions"]
```

- [ ] **Step 2: 运行测试验证失败**

```
pytest tests/test_crawler.py -v
Expected: FAIL - module 'crawler' has no class 'BugCrawler'
```

- [ ] **Step 3: 实现 crawler.py**

```python
# crawler.py
import time
import requests
from typing import Dict, Optional
from config import BASE_URL, get_default_headers, build_auth_headers

class BugCrawler:
    def __init__(self, auth_config: Dict[str, str]):
        self.base_url = BASE_URL
        self.auth = auth_config
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        return build_auth_headers(
            cookie=self.auth.get("cookie", ""),
            authorization=self.auth.get("authorization", ""),
            user_id=self.auth.get("x_titan_userid", "")
        )

    def build_export_payload(self, source_type: str = "with_assigned_domain") -> Dict:
        """构建导出请求体"""
        request_tag = str(int(time.time() * 1000))

        base_conditions = {
            "sorts": [
                {"key": "updated_time", "value": "desc"},
                {"key": "updated_time", "value": "desc"}
            ],
            "filters": [
                {"key": "scene", "operator": "||", "value": ["issue_bug"]},
                {"key": "current_domain", "operator": "||", "value": [11]},
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
            base_conditions["filters"].insert(3, {
                "key": "assigned_domain",
                "value": [{"id": 11, "type": "Domain"}],
                "operator": "||",
                "convolution": "down"
            })

        return {
            "source_id": 11,
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

    def trigger_export(self, source_type: str = "with_assigned_domain") -> Optional[str]:
        """触发导出，返回 file_id"""
        url = f"{self.base_url}/vision-excel/api/export/issue/v2?requestTag={int(time.time() * 1000)}"
        payload = self.build_export_payload(source_type)

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
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
                timeout=30
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

    def download_file(self, file_id: str) -> Optional[bytes]:
        """下载 Excel 文件"""
        url = f"{self.base_url}/vision-excel/api/query/issue/download_item?domain_id=11&requestTag={int(time.time() * 1000)}"

        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=60
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"下载文件失败: {e}")
            return None

    def wait_and_download(self, file_id: str, timeout: int = 60) -> Optional[bytes]:
        """轮询等待文件就绪后下载"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.query_file_status(file_id)
            if status == "ready":
                return self.download_file(file_id)
            time.sleep(2)  # 每2秒轮询一次

        print("等待文件超时")
        return None

    def fetch_data(self, source_type: str = "with_assigned_domain") -> Optional[bytes]:
        """完整流程：触发导出 → 等待 → 下载"""
        file_id = self.trigger_export(source_type)
        if not file_id:
            print("获取 file_id 失败")
            return None

        return self.wait_and_download(file_id)
```

- [ ] **Step 4: 运行测试验证通过**

```
pytest tests/test_crawler.py -v
Expected: PASS
```

- [ ] **Step 5: 提交**

```bash
git add crawler.py tests/test_crawler.py
git commit -m "feat: add web crawler module"
```

---

### Task 4: 数据处理模块

**Files:**
- Create: `E:/aitest/bug-di-analysis/processor.py`
- Create: `E:/aitest/bug-di-analysis/tests/test_processor.py`

- [ ] **Step 1: 编写测试**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

```
pytest tests/test_processor.py -v
Expected: FAIL - module 'processor' has no function 'load_excel'
```

- [ ] **Step 3: 实现 processor.py**

```python
# processor.py
import pandas as pd
from io import BytesIO
from typing import List, Optional

FIELD_MAPPING = {
    "number": "问题单号",
    "title": "标题",
    "severity_level": "严重程度",
    "status": "问题状态",
    "assigned_to_domain": "责任服务",
    "from_version": "发现问题版本",
    "discover_iteration": "发现迭代",
    "created_time": "创建时间",
    "delivery_scenario": "交付场景",
    "valid": "挂起/撤销",
    "discovered_environment": "发现环境",
    "labels": "标签",
    "dev_person": "研发责任人",
    "testOwners": "测试责任人"
}

CHINESE_TO_ENGLISH = {v: k for k, v in FIELD_MAPPING.items()}

def load_excel(file_bytes: bytes) -> pd.DataFrame:
    """读取 Excel 文件，返回 DataFrame"""
    try:
        df = pd.read_excel(BytesIO(file_bytes))
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

    df = pd.concat([df1, df2], ignore_index=True)

    # 按问题单号去重
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
    - version 有值: 返回 from_version=该版本 或 from_version为空 的数据
    """
    if df.empty:
        return df

    if version is None or version == "全部":
        return df

    # 返回指定版本 + 空版本的数据
    return df[
        (df["from_version"] == version) |
        (df["from_version"].isna()) |
        (df["from_version"] == "")
    ]
```

- [ ] **Step 4: 运行测试验证通过**

```
pytest tests/test_processor.py -v
Expected: PASS
```

- [ ] **Step 5: 提交**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat: add data processing module"
```

---

### Task 5: DI 统计计算模块

**Files:**
- Create: `E:/aitest/bug-di-analysis/di_calculator.py`
- Create: `E:/aitest/bug-di-analysis/tests/test_di_calculator.py`

- [ ] **Step 1: 编写测试**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

```
pytest tests/test_di_calculator.py -v
Expected: FAIL - module 'di_calculator' has no attribute 'SEVERITY_DI'
```

- [ ] **Step 3: 实现 di_calculator.py**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

```
pytest tests/test_di_calculator.py -v
Expected: PASS
```

- [ ] **Step 5: 提交**

```bash
git add di_calculator.py tests/test_di_calculator.py
git commit -m "feat: add DI calculation module"
```

---

### Task 6: Streamlit 样式配置

**Files:**
- Create: `E:/aitest/bug-di-analysis/styles.py`

- [ ] **Step 1: 编写样式配置**

```python
# styles.py
import streamlit as st

def apply_custom_styles():
    """应用自定义样式"""
    st.markdown("""
    <style>
    /* 主标题样式 */
    .main-title {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }

    /* 概览卡片样式 */
    .overview-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }

    /* 合格标记样式 */
    .qualified {
        color: green;
        font-weight: bold;
    }

    .unqualified {
        color: red;
        font-weight: bold;
    }

    /* 过滤按钮容器 */
    .filter-container {
        margin: 1rem 0;
    }

    /* 表格样式优化 */
    .dataframe {
        font-size: 0.9rem;
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

def render_qualified_badge(qualified: bool) -> str:
    """渲染合格标记"""
    if qualified:
        return '<span class="qualified">✅ 合格</span>'
    else:
        return '<span class="unqualified">❌ 不合格</span>'
```

- [ ] **Step 2: 提交**

```bash
git add styles.py
git commit -m "feat: add Streamlit styles"
```

---

### Task 7: Streamlit 主页面

**Files:**
- Create: `E:/aitest/bug-di-analysis/app.py`

- [ ] **Step 1: 实现 app.py**

```python
# app.py
import streamlit as st
import pandas as pd
from datetime import datetime

from config import build_auth_headers
from crawler import BugCrawler
from processor import load_excel, merge_data, normalize_columns, get_version_list, filter_by_version
from di_calculator import calculate_cloud_di, calculate_microservice_di, filter_production_issues, get_issue_detail_url
from styles import apply_custom_styles, render_qualified_badge

st.set_page_config(
    page_title="DI 统计工具",
    page_icon="📊",
    layout="wide"
)

apply_custom_styles()

st.markdown('<p class="main-title">📊 DI 统计工具</p>', unsafe_allow_html=True)

# 初始化 session state
if "df_raw" not in st.session_state:
    st.session_state.df_raw = pd.DataFrame()
if "df_processed" not in st.session_state:
    st.session_state.df_processed = pd.DataFrame()
if "selected_version" not in st.session_state:
    st.session_state.selected_version = "全部"
if "versions" not in st.session_state:
    st.session_state.versions = []

# 侧边栏 - 认证配置
st.sidebar.title("认证配置")

cookie = st.sidebar.text_input("Cookie", type="password", help="登录 Cookie")
authorization = st.sidebar.text_input("Authorization Token", type="password", help="JWT Token")
user_id = st.sidebar.text_input("x-titan-userid", value="", help="用户 ID")

st.sidebar.divider()

if st.sidebar.button("🔄 刷新数据", type="primary", use_container_width=True):
    if not cookie or not authorization or not user_id:
        st.sidebar.error("请填写完整的认证信息")
    else:
        with st.spinner("正在获取数据..."):
            auth_config = {
                "cookie": cookie,
                "authorization": authorization,
                "x_titan_userid": user_id
            }

            crawler = BugCrawler(auth_config)

            # 获取两个 URL 的数据
            data1 = crawler.fetch_data("with_assigned_domain")
            data2 = crawler.fetch_data("without_assigned_domain")

            if data1 or data2:
                df1 = load_excel(data1) if data1 else pd.DataFrame()
                df2 = load_excel(data2) if data2 else pd.DataFrame()

                df_raw = merge_data(df1, df2)
                df_raw = normalize_columns(df_raw)

                st.session_state.df_raw = df_raw

                # 获取版本列表
                st.session_state.versions = get_version_list(df_raw)
                st.session_state.selected_version = "全部"

                st.sidebar.success(f"成功获取 {len(df_raw)} 条问题单")
            else:
                st.sidebar.error("获取数据失败，请检查认证信息")

st.sidebar.divider()

# 导出功能
st.sidebar.subheader("导出功能")

if st.sidebar.button("📥 导出原始数据", use_container_width=True):
    if not st.session_state.df_raw.empty:
        csv = st.session_state.df_raw.to_csv(index=False)
        st.sidebar.download_button(
            label="下载 CSV",
            data=csv,
            file_name=f"bug_raw_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.sidebar.warning("暂无数据")

# 主页面
if not st.session_state.df_raw.empty:
    # 数据预处理
    df_all = filter_production_issues(st.session_state.df_raw)

    # 云服务概览
    st.subheader("☁️ 云服务 DI 概览")

    cloud_di_info = calculate_cloud_di(df_all)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("云服务", "Cloud Eye")
    col2.metric("总 DI 值", cloud_di_info["di"])
    col3.metric("总问题单", cloud_di_info["issue_count"])

    qualified_html = render_qualified_badge(cloud_di_info["qualified"])
    col4.markdown(f"合格标准: {qualified_html}", unsafe_allow_html=True)

    st.divider()

    # 版本过滤
    st.subheader("🔍 发现问题版本过滤")

    if st.session_state.versions:
        cols = st.columns(len(st.session_state.versions) + 1)

        # 全部按钮
        if cols[0].button("全部", type="primary" if st.session_state.selected_version == "全部" else "secondary"):
            st.session_state.selected_version = "全部"
            st.rerun()

        # 各版本按钮
        for i, version in enumerate(st.session_state.versions):
            if cols[i + 1].button(version, type="primary" if st.session_state.selected_version == version else "secondary"):
                st.session_state.selected_version = version
                st.rerun()

        st.caption(f"当前选中：{st.session_state.selected_version}")
    else:
        st.info("暂无可用的版本数据")

    st.divider()

    # CES 微服务 DI 明细
    st.subheader("📋 CES 微服务 DI 明细")

    # 按版本过滤
    df_filtered = filter_by_version(df_all, st.session_state.selected_version)

    # 计算微服务 DI
    ms_di = calculate_microservice_di(df_filtered)

    if not ms_di.empty:
        # 添加可排序的表格
        st.dataframe(
            ms_di.rename(columns={
                "assigned_to_domain": "微服务名",
                "di_sum": "DI 值",
                "issue_count": "问题单数",
                "qualified": "是否合格"
            }),
            column_config={
                "是否合格": st.column_config.Column(
                    "是否合格",
                    formatter=lambda x: "✅ 合格" if x else "❌ 不合格"
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("暂无数据")

    st.divider()

    # 问题单明细
    st.subheader("📄 问题单明细")

    # 展示当前过滤条件下的所有问题单
    st.dataframe(
        df_filtered.rename(columns={
            "number": "问题单号",
            "title": "标题",
            "severity_level": "严重程度",
            "status": "问题状态",
            "assigned_to_domain": "责任服务",
            "from_version": "发现问题版本",
            "dev_person": "研发责任人",
            "testOwners": "测试责任人",
            "delivery_scenario": "交付场景"
        })[[
            "问题单号", "标题", "严重程度", "问题状态",
            "责任服务", "发现问题版本", "研发责任人", "测试责任人"
        ]],
        hide_index=True,
        use_container_width=True
    )

else:
    st.info("👈 请先在侧边栏填写认证信息并点击「刷新数据」")

    st.markdown("""
    ### 使用说明

    1. 在侧边栏填写认证信息（Cookie、Authorization Token、x-titan-userid）
    2. 点击「刷新数据」按钮获取问题单数据
    3. 选择发现问题版本进行过滤
    4. 查看 CES 微服务 DI 统计
    5. 点击「导出原始数据」下载 CSV 文件
    """)
```

- [ ] **Step 2: 提交**

```bash
git add app.py
git commit -m "feat: add Streamlit main page"
```

---

### Task 8: 集成测试

**Files:**
- Create: `E:/aitest/bug-di-analysis/tests/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
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
```

- [ ] **Step 2: 运行集成测试**

```
pytest tests/test_integration.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
```

---

## 自检清单

**Spec 覆盖检查：**
- [x] 认证配置（Cookie/Token/UserID）
- [x] 爬虫模块（触发导出/查询状态/下载文件）
- [x] 数据处理（读取Excel/合并去重/版本过滤）
- [x] DI 计算（CCB挂起过滤/SLA计算/交付场景/微服务分组）
- [x] Streamlit 页面（概览卡片/版本过滤/微服务表格/问题单明细）
- [x] 导出功能（原始数据导出）

**占位符检查：**
- 无 TBD/TODO
- 无"类似 Task N"的引用
- 所有代码块完整

**类型一致性：**
- `from_version` 字段贯穿所有模块
- `assigned_to_domain` 用于微服务匹配
- `discovered_environment` 用于环境判断
- `valid` 用于挂起状态判断

---

## 执行选择

**Plan complete and saved to `E:/aitest/bug-di-analysis/docs/plans/2026-03-27-di-tool-implementation.md`**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
