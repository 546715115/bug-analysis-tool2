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