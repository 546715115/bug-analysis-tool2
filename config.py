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