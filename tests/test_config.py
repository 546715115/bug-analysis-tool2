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