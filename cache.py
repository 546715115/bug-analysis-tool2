# cache.py
import os
import pickle
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
MAX_CACHE_COUNT = 3


def get_cache_dir() -> str:
    """获取缓存目录路径"""
    return CACHE_DIR


def ensure_cache_dir() -> None:
    """确保缓存目录存在"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def generate_cache_filename(import_type: str) -> str:
    """生成带来源前缀的时间戳文件名"""
    now = datetime.now()
    prefix = f"{import_type}-" if import_type else ""
    return f"{prefix}{now.strftime('%Y%m%d%H%M%S')}.pkl"


def save_cache(df_raw: pd.DataFrame, versions: List[str], import_type: str = "") -> Tuple[bool, str]:
    """
    保存当前数据到缓存

    Args:
        df_raw: 合并去重后的原始数据
        versions: 版本列表
        import_type: 数据来源类型，"api" 或 "excel"，用于文件名前缀

    Returns:
        (success, message)
    """
    try:
        ensure_cache_dir()

        # 清理超过上限的旧缓存
        enforce_cache_limit()

        # 生成文件名（带来源前缀）
        filename = generate_cache_filename(import_type)
        filepath = os.path.join(CACHE_DIR, filename)

        # 构建缓存数据
        cache_data = {
            "df_raw": df_raw,
            "versions": versions,
            "cached_at": datetime.now()
        }

        # 保存
        with open(filepath, "wb") as f:
            pickle.dump(cache_data, f)

        return True, f"缓存成功: {filename}"
    except Exception as e:
        return False, f"缓存失败: {str(e)}"


def load_cache(filename: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    加载指定缓存文件

    Args:
        filename: 缓存文件名

    Returns:
        (success, message, cache_data)
    """
    try:
        filepath = os.path.join(CACHE_DIR, filename)
        if not os.path.exists(filepath):
            return False, "缓存文件不存在", None

        with open(filepath, "rb") as f:
            cache_data = pickle.load(f)

        return True, "加载成功", cache_data
    except Exception as e:
        return False, f"加载失败: {str(e)}", None


def list_caches() -> List[Dict]:
    """
    获取所有缓存文件列表（按时间倒序）

    Returns:
        [{"filename": str, "import_type": str, "cached_at": datetime, "df_rows": int}, ...]
    """
    try:
        ensure_cache_dir()
        files = os.listdir(CACHE_DIR)

        caches = []
        for f in files:
            if f.endswith(".pkl"):
                filepath = os.path.join(CACHE_DIR, f)
                try:
                    with open(filepath, "rb") as file:
                        data = pickle.load(file)
                    cached_at = data.get("cached_at", datetime.fromtimestamp(os.path.getmtime(filepath)))
                    df_rows = len(data.get("df_raw", pd.DataFrame()))
                    # 解析文件名前缀作为 import_type
                    if f.startswith("api-") or f.startswith("excel-"):
                        import_type = f.split("-", 1)[0]
                    else:
                        import_type = ""
                    caches.append({
                        "filename": f,
                        "import_type": import_type,
                        "cached_at": cached_at,
                        "df_rows": df_rows
                    })
                except Exception:
                    # 跳过损坏的文件
                    continue

        # 按时间倒序排序
        caches.sort(key=lambda x: x["cached_at"], reverse=True)
        return caches
    except Exception:
        return []


def delete_cache(filename: str) -> Tuple[bool, str]:
    """
    删除指定缓存文件

    Args:
        filename: 缓存文件名

    Returns:
        (success, message)
    """
    try:
        filepath = os.path.join(CACHE_DIR, filename)
        if not os.path.exists(filepath):
            return False, "缓存文件不存在"

        os.remove(filepath)
        return True, f"删除成功: {filename}"
    except Exception as e:
        return False, f"删除失败: {str(e)}"


def enforce_cache_limit() -> None:
    """强制执行缓存上限（最多3份），删除最旧的"""
    caches = list_caches()
    if len(caches) >= MAX_CACHE_COUNT:
        # 删除最旧的
        oldest = caches[-1]
        delete_cache(oldest["filename"])
