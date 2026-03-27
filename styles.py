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
