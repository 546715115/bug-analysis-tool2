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

# Domain 配置
st.sidebar.subheader("Domain 配置")
domain_input = st.sidebar.text_input(
    "Domain ID 列表",
    value="11, 33921",
    help="多个 Domain 用逗号分隔，如: 11, 33921"
)

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

            # 解析 domain IDs
            try:
                domain_ids = [int(d.strip()) for d in domain_input.split(",") if d.strip()]
            except ValueError:
                st.sidebar.error("Domain ID 格式错误，请输入数字，用逗号分隔")
                domain_ids = []

            if domain_ids:
                crawler = BugCrawler(auth_config, domain_ids=domain_ids)

                # 获取所有 domain 的数据
                all_dfs = []
                for domain_id in domain_ids:
                    st.sidebar.info(f"正在获取 Domain {domain_id}...")
                    print(f"\n========== 开始获取 Domain {domain_id} ==========")

                    # 获取两种条件的数据并合并
                    data1 = crawler.fetch_data(domain_id, "with_assigned_domain")
                    print(f"[Domain {domain_id}] with_assigned_domain data1: {len(data1) if data1 else 0} bytes")

                    if data1:
                        df1 = load_excel(data1)
                        print(f"[Domain {domain_id}] df1 行数: {len(df1)}")
                    else:
                        df1 = pd.DataFrame()

                    data2 = crawler.fetch_data(domain_id, "without_assigned_domain")
                    print(f"[Domain {domain_id}] without_assigned_domain data2: {len(data2) if data2 else 0} bytes")

                    if data2:
                        df2 = load_excel(data2)
                        print(f"[Domain {domain_id}] df2 行数: {len(df2)}")
                    else:
                        df2 = pd.DataFrame()

                    merged = merge_data(df1, df2)
                    print(f"[Domain {domain_id}] 合并后行数: {len(merged)}")

                    if not merged.empty:
                        merged["_source_domain"] = domain_id  # 标记数据来源
                        all_dfs.append(merged)
                        print(f"[Domain {domain_id}] 添加到结果集")
                    else:
                        print(f"[Domain {domain_id}] 警告: 数据为空")

                if all_dfs:
                    df_raw = pd.concat(all_dfs, ignore_index=True)
                    print(f"\n所有 Domain 合并后总行数: {len(df_raw)}")

                    df_raw = normalize_columns(df_raw)
                    print(f"标准化列名后列名: {list(df_raw.columns)}")

                    st.session_state.df_raw = df_raw

                    # 获取版本列表
                    st.session_state.versions = get_version_list(df_raw)
                    print(f"发现版本列表: {st.session_state.versions}")
                    st.session_state.selected_version = "全部"

                    st.sidebar.success(f"成功获取 {len(df_raw)} 条问题单 (来自 {len(domain_ids)} 个 Domain)")
                else:
                    print("错误: 所有 Domain 数据都为空")
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
    st.subheader("🔍 发 现 问 题 版 本 过 滤")

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