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

# 侧边栏
st.sidebar.title("DI 统计工具")

# API 导入（可折叠）
with st.sidebar.expander("🔗 API 导入", expanded=True):
    cookie = st.text_input("Cookie", type="password", help="登录 Cookie")
    authorization = st.text_input("Authorization Token", type="password", help="JWT Token")
    user_id = st.text_input("x-titan-userid", value="", help="用户 ID")
    domain_input = st.text_input(
        "Domain ID 列表",
        value="11, 33921",
        help="多个 Domain 用逗号分隔，如: 11, 33921"
    )

    if st.button("🔍 分析数据", type="primary", use_container_width=True):
        if not cookie or not authorization or not user_id:
            st.error("请填写完整的认证信息")
        else:
            with st.spinner("正在获取数据..."):
                auth_config = {
                    "cookie": cookie,
                    "authorization": authorization,
                    "x_titan_userid": user_id
                }

                try:
                    domain_ids = [int(d.strip()) for d in domain_input.split(",") if d.strip()]
                except ValueError:
                    st.error("Domain ID 格式错误，请输入数字，用逗号分隔")
                    domain_ids = []

                if domain_ids:
                    crawler = BugCrawler(auth_config, domain_ids=domain_ids)

                    all_dfs = []
                    for domain_id in domain_ids:
                        print(f"\n========== 开始获取 Domain {domain_id} ==========")

                        print(f"[Domain {domain_id}] 第1次导出: with_assigned_domain")
                        data1 = crawler.fetch_data(domain_id, "with_assigned_domain")
                        df1 = load_excel(data1) if data1 else pd.DataFrame()
                        print(f"[Domain {domain_id}] 第1次结果: bytes={len(data1) if data1 else 0}, df1行数={len(df1)}")

                        print(f"[Domain {domain_id}] 第2次导出: without_assigned_domain")
                        data2 = crawler.fetch_data(domain_id, "without_assigned_domain")
                        df2 = load_excel(data2) if data2 else pd.DataFrame()
                        print(f"[Domain {domain_id}] 第2次结果: bytes={len(data2) if data2 else 0}, df2行数={len(df2)}")

                        merged = merge_data(df1, df2)
                        print(f"[Domain {domain_id}] 合并后总行数: {len(merged)}")

                        if not merged.empty:
                            merged["_source_domain"] = domain_id
                            all_dfs.append(merged)

                    if all_dfs:
                        df_raw = pd.concat(all_dfs, ignore_index=True)
                        df_raw = normalize_columns(df_raw)
                        st.session_state.df_raw = df_raw
                        st.session_state.versions = get_version_list(df_raw)
                        st.session_state.selected_version = "全部"
                        st.success(f"成功获取 {len(df_raw)} 条问题单 (来自 {len(domain_ids)} 个 Domain)")
                    else:
                        st.error("获取数据失败，请检查认证信息或 API 参数")

# 导入 Excel（可折叠）
with st.sidebar.expander("📁 导入 Excel", expanded=True):
    uploaded_files = []
    for i in range(3):
        key = f"excel_file_{i}"
        label = f"Excel 文件 {i+1}" + ("（必选）" if i == 0 else "（可选）")
        uploaded = st.file_uploader(label, type=["xlsx"], key=key)
        if uploaded:
            uploaded_files.append(uploaded)

    if st.button("📂 加载 Excel", type="primary", use_container_width=True):
        if not uploaded_files:
            st.error("请至少导入一个 Excel 文件")
        else:
            with st.spinner("正在加载 Excel..."):
                try:
                    all_dfs = []
                    for f in uploaded_files:
                        df = load_excel(f.getvalue())
                        if not df.empty:
                            all_dfs.append(df)
                            print(f"Excel {f.name} 行数: {len(df)}")

                    if all_dfs:
                        merged = all_dfs[0]
                        for i in range(1, len(all_dfs)):
                            merged = merge_data(merged, all_dfs[i])
                        print(f"合并后行数: {len(merged)}")

                        if not merged.empty:
                            merged = normalize_columns(merged)
                            st.session_state.df_raw = merged
                            st.session_state.versions = get_version_list(merged)
                            st.session_state.selected_version = "全部"
                            st.success(f"成功加载 {len(merged)} 条数据")
                        else:
                            st.error("Excel 数据为空")
                    else:
                        st.error("没有可加载的数据")
                except Exception as e:
                    st.error(f"加载失败: {e}")

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
    st.caption("💡 云服务 DI < 20 合格；微服务 DI < 5 合格")

    st.divider()

    # 版本过滤
    st.subheader("🔍 发 现 问 题 版 本 过 滤")

    if st.session_state.versions:
        version_options = ["全部"] + sorted(st.session_state.versions)
        selected = st.selectbox(
            "选择版本",
            options=version_options,
            index=version_options.index(st.session_state.selected_version) if st.session_state.selected_version in version_options else 0,
            label_visibility="collapsed"
        )
        if selected != st.session_state.selected_version:
            st.session_state.selected_version = selected
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
        # 转换布尔值为文字
        display_df = ms_di.rename(columns={
            "assigned_to_domain": "微服务名",
            "di_sum": "DI 值",
            "issue_count": "问题单数",
        })
        display_df["是否合格"] = display_df["qualified"].apply(lambda x: "✅ 合格" if x else "❌ 不合格")
        display_df = display_df.drop(columns=["qualified"])

        # 可排序表格
        st.dataframe(
            display_df,
            column_config={
                "是否合格": st.column_config.Column("是否合格")
            },
            hide_index=True,
            use_container_width=True,
            height=300
        )

        # 问题单明细（按微服务筛选，可折叠）
        with st.expander("🔍 按微服务查看问题单详情"):
            if "assigned_to_domain" in df_filtered.columns:
                microservices = df_filtered["assigned_to_domain"].dropna().unique()
                selected_ms = st.selectbox("选择微服务", options=list(microservices))
                if selected_ms:
                    ms_issues = df_filtered[df_filtered["assigned_to_domain"] == selected_ms]
                    st.dataframe(ms_issues[["number", "title", "severity_level", "status"]].rename(columns={
                        "number": "问题单号", "title": "标题", "severity_level": "严重程度", "status": "状态"
                    }), hide_index=True, use_container_width=True)
    else:
        st.info("暂无数据")

    st.divider()

    # 问题单明细
    st.subheader("📄 问题单明细")

    # 打印实际列名用于调试
    print(f"df_filtered 列名: {list(df_filtered.columns)}")

    # 英文到中文的显示映射
    en_to_cn_display = {
        "number": "问题单号",
        "title": "标题",
        "severity_level": "严重程度",
        "status": "问题状态",
        "assigned_to_domain": "责任服务",
        "from_version": "发现问题版本",
        "dev_person": "研发责任人",
        "testOwners": "测试责任人",
        "delivery_scenario": "交付场景"
    }

    # 尝试把英文列名转中文，如果原列名是中文直接用
    display_cols = []
    col_rename = {}
    for en, cn in en_to_cn_display.items():
        if en in df_filtered.columns:
            col_rename[en] = cn
            display_cols.append(cn)
        elif cn in df_filtered.columns:
            display_cols.append(cn)

    # 只选择存在的列
    available_cols = [c for c in display_cols if c in df_filtered.columns or c in col_rename.values()]
    df_display = df_filtered.rename(columns=col_rename) if col_rename else df_filtered

    # 显示可用的列
    cols_to_show = [c for c in display_cols if c in df_display.columns]
    if cols_to_show:
        st.dataframe(
            df_display[cols_to_show],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.dataframe(df_display, hide_index=True, use_container_width=True)

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