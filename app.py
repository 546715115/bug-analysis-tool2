# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from config import build_auth_headers
from crawler import BugCrawler
from processor import load_excel, merge_data, normalize_columns, get_version_list, filter_by_version
from di_calculator import (
    calculate_cloud_di, calculate_microservice_di, calculate_microservice_di_with_count,
    filter_production_issues, get_issue_detail_url, is_microservice
)
from styles import apply_custom_styles, render_qualified_badge

try:
    from st_aggrid import AgGrid, GridOptionsBuilder
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False

st.set_page_config(
    page_title="DI 统计工具",
    page_icon="📊",
    layout="wide"
)

apply_custom_styles()

st.markdown('<p class="main-title">📊 DI 统计工具</p>', unsafe_allow_html=True)


def aggrid_table(df: pd.DataFrame, columns: list = None, height: int = 300, page_size: int = 10):
    """
    使用 AgGrid 渲染可排序、分页、横向滚动的表格
    """
    if columns is None:
        columns = list(df.columns)

    if not AGGRID_AVAILABLE:
        st.dataframe(df[columns] if columns else df, hide_index=True, use_container_width=True, height=height)
        return

    display_cols = [c for c in columns if c in df.columns]
    if not display_cols:
        st.dataframe(df, hide_index=True, use_container_width=True, height=height)
        return

    # 使用 from_dataframe 方式构建
    gb = GridOptionsBuilder.from_dataframe(df[display_cols])

    # 分页配置
    gb.configure_pagination(
        paginationAutoPageSize=False,
        paginationPageSize=page_size,
        paginationPageSizeSelector=[10, 20, 50],
        enabled=True
    )

    # 启用侧边栏筛选面板
    gb.configure_side_bar(filters_panel=True)

    grid_options = gb.build()

    AgGrid(
        df[display_cols],
        gridOptions=grid_options,
        height=height,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        reload_data=True,
        enable_enterprise_modules=False
    )


def filter_by_di_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    按 DI 统计规则过滤问题单
    返回 DI > 0 的问题单
    """
    if df.empty:
        return df

    current_time = datetime.now()
    from di_calculator import calculate_di_for_issue
    df_result = df.copy()
    df_result["_di"] = df_result.apply(lambda row: calculate_di_for_issue(row, current_time), axis=1)
    df_result = df_result[df_result["_di"] > 0]
    df_result = df_result.drop(columns=["_di"])
    return df_result


def export_to_excel(df: pd.DataFrame, filename: str):
    """导出 DataFrame 为 Excel 文件，带表头筛选功能"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='问题单明细')
        worksheet = writer.sheets['问题单明细']
        worksheet.auto_filter.ref = worksheet.dimensions
    output.seek(0)
    return output.getvalue()


# 初始化 session state
if "df_raw" not in st.session_state:
    st.session_state.df_raw = pd.DataFrame()
if "df_processed" not in st.session_state:
    st.session_state.df_processed = pd.DataFrame()
if "selected_version" not in st.session_state:
    st.session_state.selected_version = "全部"
if "versions" not in st.session_state:
    st.session_state.versions = []
if "sidebar_expanded" not in st.session_state:
    st.session_state.sidebar_expanded = False


# 顶部工具栏
col_toolbar = st.columns([1, 10])
with col_toolbar[0]:
    if st.button("☰", help="展开/折叠侧边栏"):
        st.session_state.sidebar_expanded = not st.session_state.sidebar_expanded
        st.rerun()


def render_sidebar():
    """渲染侧边栏内容"""
    st.title("DI 统计工具")

    # API 导入（默认折叠）
    with st.expander("🔗 API 导入", expanded=False):
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

    # 导入 Excel（默认折叠）
    with st.expander("📁 导入 Excel", expanded=False):
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

    # 导出按钮
    st.divider()
    if st.button("📥 导出版本有效DI-Excel", use_container_width=True, type="primary"):
        if not st.session_state.df_raw.empty:
            st.session_state.show_export_dialog = True
        else:
            st.warning("暂无数据")

    if st.button("◀ 折叠侧边栏"):
        st.session_state.sidebar_expanded = False
        st.rerun()


# 根据侧边栏状态选择布局
if st.session_state.sidebar_expanded:
    # 侧边栏展开：左侧窄栏 + 右侧主内容
    with st.sidebar:
        render_sidebar()

    # 主页面内容
    main_content()
else:
    # 侧边栏折叠：只显示主页面内容
    main_content()


def main_content():
    """主页面内容"""

    # 导出弹窗
    if st.session_state.get("show_export_dialog", False):
        @st.dialog("导出问题单数据")
        def export_dialog():
            """导出数据弹窗"""
            st.write("### 导出条件筛选")

            # 获取所有数据（经过 CCB 过滤）
            df_all = filter_production_issues(st.session_state.df_raw)

            # 版本过滤
            version_options = ["全部"] + sorted(st.session_state.versions) if st.session_state.versions else ["全部"]
            export_version = st.selectbox(
                "选择发现问题版本",
                options=version_options,
                index=0,
                help="筛选特定版本的问题单"
            )

            # 先按版本过滤
            if export_version == "全部":
                df_export = df_all.copy()
            else:
                df_export = filter_by_version(df_all, export_version)

            # CES 微服务过滤
            ces_list = df_export["assigned_to_domain"].dropna().unique()
            ces_options = ["全部"] + sorted([str(ms) for ms in ces_list if is_microservice(ms)])
            export_ms = st.selectbox(
                "选择 CES 微服务",
                options=ces_options,
                index=0,
                help="筛选特定微服务的问题单"
            )

            # 按微服务过滤
            if export_ms != "全部":
                df_export = df_export[df_export["assigned_to_domain"] == export_ms]

            # 按 DI 统计规则过滤
            current_time = datetime.now()
            from di_calculator import calculate_di_for_issue
            df_export["_di"] = df_export.apply(lambda row: calculate_di_for_issue(row, current_time), axis=1)
            df_export = df_export[df_export["_di"] > 0]
            df_export = df_export.drop(columns=["_di"])

            # 按问题单号排序
            if "number" in df_export.columns:
                df_export = df_export.sort_values("number", ascending=True)

            # 生成文件名
            version_str = export_version if export_version != "全部" else "全部版本"
            ms_str = export_ms if export_ms != "全部" else "全部微服务"
            now = datetime.now()
            # 微服务选项直接替换"CES微服务"占位
            filename = f"发现问题版本{version_str}-{ms_str}-{now.strftime('%Y/%m/%d/%H/%M')}.xlsx"

            st.write(f"符合条件的问题单：**{len(df_export)}** 条")

            if st.button("📥 确认下载", type="primary"):
                if not df_export.empty:
                    excel_data = export_to_excel(df_export, filename)
                    st.download_button(
                        label="点击下载",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("没有符合条件的数据")

            if st.button("返回"):
                st.session_state.show_export_dialog = False
                st.rerun()

        export_dialog()

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

        # 计算微服务 DI（包含按 DI 规则过滤后的问题单数）
        ms_di = calculate_microservice_di_with_count(df_filtered)

        if not ms_di.empty:
            # 转换布尔值为文字
            display_df = ms_di.rename(columns={
                "assigned_to_domain": "微服务名",
                "di_sum": "DI 值",
                "issue_count": "问题单数",
            })
            display_df["是否合格"] = display_df["qualified"].apply(lambda x: "✅ 合格" if x else "❌ 不合格")
            display_df = display_df.drop(columns=["qualified"])

            aggrid_table(display_df, ["微服务名", "DI 值", "问题单数", "是否合格"], height=300)

            # 问题单明细（按微服务筛选，可折叠）
            with st.expander("🔍 按微服务查看问题单详情"):
                if "assigned_to_domain" in df_filtered.columns:
                    microservices = df_filtered["assigned_to_domain"].dropna().unique()
                    ces_microservices = [ms for ms in microservices if is_microservice(ms)]
                    selected_ms = st.selectbox("选择微服务", options=list(ces_microservices))
                    if selected_ms:
                        ms_issues = df_filtered[df_filtered["assigned_to_domain"] == selected_ms]
                        # 按 DI 规则过滤
                        ms_issues_filtered = filter_by_di_rules(ms_issues)
                        ms_display = ms_issues_filtered[["number", "title", "severity_level", "status"]].copy()
                        ms_display.columns = ["问题单号", "标题", "严重程度", "状态"]
                        aggrid_table(ms_display, height=300)
        else:
            st.info("暂无数据")

        st.divider()

        # 问题单明细
        st.subheader("📄 问题单明细")

        # 按 DI 规则过滤
        df_di_filtered = filter_by_di_rules(df_filtered)

        # 英文到中文的显示映射
        en_to_cn_display = {
            "number": "问题单号",
            "title": "标题",
            "severity_level": "严重程度",
            "status": "问题状态",
            "stage": "问题阶段",
            "assigned_to_domain": "责任服务",
            "from_version": "发现问题版本",
            "dev_person": "研发责任人",
            "testOwners": "测试责任人",
            "delivery_scenario": "交付场景"
        }

        # 尝试把英文列名转中文，如果原列名是中文直接用
        col_rename = {}
        display_cols = []
        for en, cn in en_to_cn_display.items():
            if en in df_di_filtered.columns:
                col_rename[en] = cn
                display_cols.append(cn)
            elif cn in df_di_filtered.columns:
                display_cols.append(cn)

        df_display = df_di_filtered.rename(columns=col_rename) if col_rename else df_di_filtered

        # 显示可用的列
        cols_to_show = [c for c in display_cols if c in df_display.columns]
        if cols_to_show:
            aggrid_table(df_display[cols_to_show], height=400)
        else:
            st.dataframe(df_display, hide_index=True, use_container_width=True)

    else:
        st.info("👈 请先点击左上角 ☰ 按钮展开侧边栏，导入数据")

        st.markdown("""
        ### 使用说明

        1. 点击左上角 **☰** 按钮展开侧边栏
        2. 在侧边栏选择 **API导入** 或 **导入Excel**
        3. 选择发现问题版本进行过滤
        4. 查看 CES 微服务 DI 统计
        5. 点击 **📥 导出版本有效DI-Excel** 下载筛选后的数据
        """)
