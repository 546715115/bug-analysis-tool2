# styles.py
import streamlit as st

def apply_custom_styles():
    """应用自定义样式 - 极简商务风格"""
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }
    html, body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI'; color: #111827; }
    #MainMenu, footer, .stDeployButton, div[data-testid="stToolbar"] { display: none !important; }
    .stApp > header:first-of-type { display: none !important; }
    .stApp { padding-top: 0 !important; }
    .top-nav { background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .nav-logo { display: flex; align-items: center; gap: 12px; color: white; font-size: 1.25rem; font-weight: 700; }
    .nav-logo-icon { width: 36px; height: 36px; background: rgba(255,255,255,0.2); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
    .nav-title { color: white; font-size: 1.1rem; font-weight: 600; }
    .main-content { padding: 32px; background-color: #F8FAFC; min-height: calc(100vh - 68px); }
    .metric-card { background: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); border: 1px solid #E5E7EB; height: 100%; }
    .metric-label { color: #6B7280; font-size: 0.875rem; font-weight: 500; margin-bottom: 8px; text-transform: uppercase; }
    .metric-value { color: #1E3A8A; font-size: 2.2rem; font-weight: 700; line-height: 1.2; }
    .card-container { background: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05); border: 1px solid #E5E7EB; margin-bottom: 24px; }
    .section-title { color: #1E3A8A; font-size: 1.1rem; font-weight: 700; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #E5E7EB; display: flex; align-items: center; gap: 8px; }
    .stButton > button { border-radius: 10px; font-weight: 600; padding: 10px 20px; }
    [data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E5E7EB; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #F3F4F6; border-radius: 4px; }
    ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 4px; }
    hr { border: none; height: 1px; background: #E5E7EB; margin: 24px 0; }
    .qualified { color: #059669; font-weight: 700; }
    .unqualified { color: #DC2626; font-weight: 700; }
    .stAlert { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)


def render_qualified_badge(qualified: bool) -> str:
    """渲染合格标记"""
    if qualified:
        return '<span class="qualified">✅ 合格</span>'
    else:
        return '<span class="unqualified">❌ 不合格</span>'


def render_badge(status: str) -> str:
    """渲染状态徽章"""
    status_map = {
        "已关闭": {"bg": "#6B7280", "color": "white"},
        "待提交": {"bg": "#F59E0B", "color": "white"},
        "待确认": {"bg": "#3B82F6", "color": "white"},
        "待修复": {"bg": "#EF4444", "color": "white"},
        "待验收": {"bg": "#8B5CF6", "color": "white"},
        "定位中": {"bg": "#6366F1", "color": "white"},
        "修复": {"bg": "#10B981", "color": "white"},
    }
    style = status_map.get(status, {"bg": "#9CA3AF", "color": "white"})
    return f'<span style="background-color:{style["bg"]};color:{style["color"]};border-radius:12px;padding:2px 10px;font-size:12px;font-weight:600;">{status}</span>'
