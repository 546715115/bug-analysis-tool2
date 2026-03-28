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
    page_title="CES DI 统计工具",
    page_icon="📊",
    layout="wide"
)

apply_custom_styles()

st.markdown('<p class="main-title">📊 CES DI 统计工具</p>', unsafe_allow_html=True)


def aggrid_table(df: pd.DataFrame, columns: list = None, height: int = 300, page_size: int = 10, link_column: str = None, all_columns: list = None, table_key: str = "default", pagination: bool = True):
    """
    使用 AgGrid 渲染可排序、分页、横向滚动的表格

    Args:
        df: DataFrame 数据
        columns: 默认显示的列（按从左到右顺序）
        height: 表格高度
        page_size: 默认每页条数
        link_column: 问题单号列名，用于生成"查看详情"按钮
        all_columns: 所有可选的列名列表（中文，用于字段选择器）
        table_key: 表格唯一标识，用于区分不同表格的列选择状态
        pagination: 是否启用分页，False则显示所有行
    """
    if columns is None:
        columns = list(df.columns)

    display_cols = [c for c in columns if c in df.columns]
    if not display_cols:
        st.dataframe(df, hide_index=True, use_container_width=True, height=height)
        return

    # 初始化列选择状态
    session_key = f"table_cols_{table_key}"
    dict_key = f"{session_key}_dict"
    list_key = session_key

    if session_key not in st.session_state:
        st.session_state[session_key] = display_cols.copy()

    # 如果有可选列配置，添加⚙️按钮
    if all_columns:
        col_left, col_right = st.columns([1, 1])
        with col_left:
            with st.popover("⚙️ 字段选择", help="点击选择展示哪些字段"):
                if list_key not in st.session_state:
                    st.session_state[list_key] = display_cols.copy()
                if dict_key not in st.session_state:
                    st.session_state[dict_key] = {col: (col in display_cols) for col in all_columns}

                with st.form(key=f"form_{session_key}"):
                    st.markdown("**选择展示字段**")
                    st.markdown("---")
                    for col in all_columns:
                        is_checked = st.checkbox(col, value=st.session_state[dict_key].get(col, False), key=f"{session_key}_{col}")
                        st.session_state[dict_key][col] = is_checked

                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("确认", type="primary", use_container_width=True)
                    with col2:
                        reset = st.form_submit_button("恢复默认", use_container_width=True)

                    if submitted:
                        new_list = [col for col in all_columns if st.session_state[dict_key].get(col, False)]
                        st.session_state[list_key] = new_list
                        st.rerun()
                    if reset:
                        st.session_state[dict_key] = {col: (col in display_cols) for col in all_columns}
                        st.rerun()

        display_cols = [c for c in st.session_state[list_key] if c in df.columns]
        if not display_cols:
            st.warning("请至少选择一个展示字段")
            return

    df_display = df[display_cols].copy()

    # 如果有链接列，使用 st.dataframe + column_config.LinkColumn 实现可点击链接
    if link_column and link_column in df.columns:
        from streamlit import column_config

        # 构建 column_config 字典，设置固定列宽以支持横向滚动
        column_configs = {}
        for col in display_cols:
            # 根据列名设置合适的宽度
            if "标题" in col:
                column_configs[col] = column_config.TextColumn(col, width="large")
            elif "单号" in col or "版本" in col:
                column_configs[col] = column_config.TextColumn(col, width="medium")
            else:
                column_configs[col] = column_config.TextColumn(col, width="small")

        # 添加链接列，使用 LinkColumn
        df_display["问题详情链接"] = df[link_column].apply(
            lambda x: f"https://clouddevops.huawei.com/#/bug/{x}"
        )
        column_configs["问题详情链接"] = column_config.LinkColumn("问题详情链接", display_text="查看详情", width="small")

        # 按选择的列排序 df_display
        final_cols = [c for c in display_cols if c in df_display.columns and c != "问题详情链接"]
        final_cols.append("问题详情链接")
        df_display = df_display[final_cols]

        st.dataframe(df_display, column_config=column_configs, hide_index=True, use_container_width=True, height=height)
        return

    # 没有链接列，使用 AgGrid
    if not AGGRID_AVAILABLE:
        st.dataframe(df_display, hide_index=True, use_container_width=True, height=height)
        return

    gb = GridOptionsBuilder.from_dataframe(df_display)

    # 配置分页
    if pagination:
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=page_size
        )

    grid_options = gb.build()

    # 分页设置
    if pagination:
        grid_options['pagination'] = True
        grid_options['paginationPageSize'] = page_size
        grid_options['suppressPaginationPanel'] = False
        grid_options['paginationPageSizeSelector'] = [10, 20, 50, 100]
    else:
        grid_options['pagination'] = False
        grid_options['suppressPaginationPanel'] = True

    # 列宽自适应
    grid_options['autoSizeColumns'] = True

    AgGrid(
        df_display,
        gridOptions=grid_options,
        height=height,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        reload_data=True,
        enable_enterprise_modules=False,
        unsafe_allow_html=True,
        enableCellHtml=True
    )

    # 添加CSS让表格内容和表头居中
    st.markdown("""
    <style>
    .ag-cell {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    .ag-header-cell {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 添加CSS让表格内容和表头居中
    st.markdown("""
    <style>
    .ag-cell {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    .ag-header-cell {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    </style>
    """, unsafe_allow_html=True)


# 英文到中文的列名映射（用于导出，保持与导入格式一致）
EN_TO_CN_MAPPING = {
    "number": "问题单号",
    "title": "标题",
    "severity_level": "严重程度",
    "status": "问题状态",
    "stage": "问题阶段",
    "assigned_to_domain": "责任服务",
    "from_version": "发现问题版本",
    "discover_iteration": "发现迭代",
    "created_time": "创建时间",
    "discovered_time": "发现时间",
    "delivery_scenario": "交付场景",
    "valid": "挂起/撤销",
    "discovered_environment": "发现环境",
    "labels": "标签",
    "dev_person": "研发责任人",
    "testOwners": "测试责任人",
}


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
    """导出 DataFrame 为 Excel 文件，带表头筛选功能，列名转中文"""
    output = BytesIO()

    # 复制数据，避免修改原 DataFrame
    df_export = df.copy()

    # 将英文列名转成中文（与导入格式一致）
    # 如果列名已经是中文则不转换
    rename_map = {}
    for col in df_export.columns:
        if col in EN_TO_CN_MAPPING:
            rename_map[col] = EN_TO_CN_MAPPING[col]
        # 如果列名是中文但不在映射中（如 API 导入返回中文列名），保留原名

    df_export = df_export.rename(columns=rename_map)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='问题单明细')
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
# 侧边栏状态：导入成功后折叠
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = False

# 如果侧边栏已折叠，提供一个按钮让用户可以重新展开
if st.session_state.sidebar_collapsed:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stMainBlockContainer"] {width: 100% !important;}
    </style>
    """, unsafe_allow_html=True)
    # 添加一个展开侧边栏的按钮
    if st.button("☰ 展开侧边栏"):
        st.session_state.sidebar_collapsed = False
        st.rerun()


def render_sidebar():
    """渲染侧边栏内容"""
    st.title("CES DI 统计工具")

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
                            st.session_state.sidebar_collapsed = True
                            st.rerun()
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
                                st.session_state.sidebar_collapsed = True
                                st.rerun()
                            else:
                                st.error("Excel 数据为空")
                        else:
                            st.error("没有可加载的数据")
                    except Exception as e:
                        st.error(f"加载失败: {e}")

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

            # 版本搜索过滤
            st.markdown("**发现问题版本**")
            version_search = st.text_input("搜索版本", value="", placeholder="输入版本名称搜索...", key="version_search")
            version_options = ["全部"] + sorted(st.session_state.versions) if st.session_state.versions else ["全部"]
            if version_search:
                version_filtered = [v for v in version_options if version_search.lower() in v.lower()]
            else:
                version_filtered = version_options
            export_version = st.selectbox(
                "选择发现问题版本",
                options=version_filtered if version_filtered else ["无匹配结果"],
                index=0,
                help="筛选特定版本的问题单",
                label_visibility="collapsed"
            )

            # 先按版本过滤
            if export_version == "全部":
                df_export = df_all.copy()
            else:
                df_export = filter_by_version(df_all, export_version)

            # CES 微服务搜索过滤
            st.markdown("**CES 微服务**")
            ces_list = df_export["assigned_to_domain"].dropna().unique()
            ces_options = ["全部"] + sorted([str(ms) for ms in ces_list if is_microservice(ms)])
            ces_search = st.text_input("搜索微服务", value="", placeholder="输入微服务名称搜索...", key="ces_search")
            if ces_search:
                ces_filtered = [c for c in ces_options if ces_search.lower() in c.lower()]
            else:
                ces_filtered = ces_options
            export_ms = st.selectbox(
                "选择 CES 微服务",
                options=ces_filtered if ces_filtered else ["无匹配结果"],
                index=0,
                help="筛选特定微服务的问题单",
                label_visibility="collapsed"
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
        ms_di_all = calculate_microservice_di_with_count(df_all)
        # 合格标准：云服务 DI < 20 且 所有微服务 DI < 5
        all_microservices_qualified = ms_di_all["qualified"].all() if not ms_di_all.empty else True
        overall_qualified = cloud_di_info["qualified"] and all_microservices_qualified

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("云服务", "Cloud Eye")
        col2.metric("总有效DI值", cloud_di_info["di"])
        col3.metric("总问题单", cloud_di_info["issue_count"])

        # 合格标准和导出按钮都在第四列
        with col4:
            # 第一行：合格标准
            with st.popover("合格标准", use_container_width=True):
                st.markdown("**合格标准：**")
                st.markdown("云服务 DI < 20 **且** 微服务 DI < 5，同时满足方为合格")
                st.markdown("")
                # SLA阈值和DI权重左右排列
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**SLA 阈值（天）**")
                    st.markdown("致命：7 天")
                    st.markdown("严重：14 天")
                    st.markdown("一般：30 天")
                    st.markdown("提示：30 天")
                with col_right:
                    st.markdown("**DI 权重**")
                    st.markdown("致命：10")
                    st.markdown("严重：3")
                    st.markdown("一般：1")
                    st.markdown("提示：0.1")
                st.markdown("")
                # 生产环境和非生产环境规则表格
                st.markdown("**DI 统计规则**")
                table_html = """
                <table style='width:100%; border-collapse: collapse; font-size: 0.85em;'>
                <thead>
                <tr style='background-color: #f0f0f0;'>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>问题单状态</th>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: center;'>生产环境DI</th>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产环境DI</th>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: center;'>备注</th>
                </tr>
                </thead>
                <tbody>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>待提交/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>/</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>待确认/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>/</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>定位中/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>/</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>待修复/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产按SLA超期计算</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>修复/修复中</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产按SLA超期计算</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>修复/修复测试</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产按SLA超期计算</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>修复/修复完成</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产按SLA超期计算</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>待验收/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>非生产按SLA超期计算</td></tr>
                <tr><td style='padding: 8px; border: 1px solid #ddd;'>已关闭/空</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>不统计</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>/</td></tr>
                </tbody>
                </table>
                """
                st.markdown(table_html, unsafe_allow_html=True)
            # 第二行：导出按钮
            if st.button("📥 导出版本有效DI-Excel", use_container_width=True):
                if not st.session_state.df_raw.empty:
                    st.session_state.show_export_dialog = True

        st.divider()

        # 版本过滤
        st.subheader("🔍 发 现 问 题 版 本")

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

            # 版本筛选后显示合格状态（仅在有筛选时显示）
            if st.session_state.selected_version != "全部":
                df_filtered_check = filter_by_version(df_all, st.session_state.selected_version)
                cloud_di_filtered = calculate_cloud_di(df_filtered_check)
                ms_di_filtered = calculate_microservice_di_with_count(df_filtered_check)
                all_ms_qualified = ms_di_filtered["qualified"].all() if not ms_di_filtered.empty else True
                filtered_qualified = cloud_di_filtered["qualified"] and all_ms_qualified
                badge_html = render_qualified_badge(filtered_qualified)
                st.markdown(f"<span style='font-size: 1.2em;'>{badge_html}</span>", unsafe_allow_html=True)
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

            # 过滤空行（只保留有微服务名的行）
            display_df = display_df[display_df["微服务名"].notna() & (display_df["微服务名"] != "")]

            # 添加总计行
            total_di = display_df["DI 值"].sum()
            total_issues = display_df["问题单数"].sum()
            # 合格标准：所有微服务 DI < 5 才合格
            all_qualified = display_df["是否合格"].apply(lambda x: "✅" in x).all()
            total_qualified = "✅ 合格" if all_qualified else "❌ 不合格"

            total_row = pd.DataFrame([{
                "微服务名": "总计",
                "DI 值": round(total_di, 1),
                "问题单数": total_issues,
                "是否合格": total_qualified
            }])
            display_df = pd.concat([display_df, total_row], ignore_index=True)

            aggrid_table(display_df, ["微服务名", "DI 值", "问题单数", "是否合格"], height=300, pagination=False)

            # 微服务查看问题单详情（作为独立区块）
            st.subheader("🔍 微服务查看问题单详情")

            if "assigned_to_domain" in df_filtered.columns:
                microservices = df_filtered["assigned_to_domain"].dropna().unique()
                ces_microservices = [ms for ms in microservices if is_microservice(ms)]
                selected_ms = st.selectbox("选择微服务", options=list(ces_microservices))
                if selected_ms:
                    ms_issues = df_filtered[df_filtered["assigned_to_domain"] == selected_ms]
                    # 按 DI 规则过滤
                    ms_issues_filtered = filter_by_di_rules(ms_issues)
                    ms_display = ms_issues_filtered[["number", "discovered_environment", "title", "severity_level", "status"]].copy()
                    ms_display.columns = ["问题单号", "问题单环境", "标题", "严重程度", "状态"]
                    # 按严重程度排序：致命 > 严重 > 一般 > 提示
                    severity_order = {"致命": 0, "严重": 1, "一般": 2, "提示": 3}
                    ms_display["_severity_order"] = ms_display["严重程度"].map(severity_order).fillna(99)
                    ms_display = ms_display.sort_values("_severity_order")
                    ms_display = ms_display.drop(columns=["_severity_order"])
                    # 微服务查看问题单详情可选字段
                    ms_detail_all_cols = ["问题单号", "问题单环境", "标题", "严重程度", "状态", "责任服务", "研发责任人", "测试责任人", "发现问题版本", "发现时间", "交付场景"]
                    aggrid_table(ms_display, ["问题单号", "问题单环境", "标题", "严重程度", "状态"], height=300, link_column="问题单号", all_columns=ms_detail_all_cols, table_key="ms_detail")
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
            "discovered_environment": "问题单环境",
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

        # 按严重程度排序：致命 > 严重 > 一般 > 提示
        severity_order = {"致命": 0, "严重": 1, "一般": 2, "提示": 3}
        df_display["_severity_order"] = df_display["严重程度"].map(severity_order).fillna(99)
        df_display = df_display.sort_values("_severity_order")
        df_display = df_display.drop(columns=["_severity_order"])

        # 显示可用的列（按问题单号、环境、标题、严重程度、状态顺序）
        ordered_cols = ["问题单号", "问题单环境", "标题", "严重程度", "问题状态", "问题阶段", "责任服务", "发现问题版本", "研发责任人", "测试责任人", "交付场景"]
        cols_to_show = [c for c in ordered_cols if c in df_display.columns]
        # 问题单明细可选字段
        issue_detail_all_cols = ["问题单号", "问题单环境", "标题", "严重程度", "问题状态", "问题阶段", "责任服务", "发现问题版本", "研发责任人", "测试责任人", "交付场景", "挂起/撤销", "标签", "发现迭代", "创建时间", "发现时间"]
        if cols_to_show:
            aggrid_table(df_display[cols_to_show], cols_to_show, height=400, link_column="问题单号", all_columns=issue_detail_all_cols, table_key="issue_detail")
        else:
            st.dataframe(df_display, hide_index=True, use_container_width=True)

    else:
        st.info("👈 请先在左侧展开侧边栏，导入数据")

        st.markdown("""
        ### 使用说明

        1. 在左侧侧边栏选择 **API导入** 或 **导入Excel**
        2. 选择发现问题版本进行过滤
        3. 查看 CES 微服务 DI 统计
        4. 点击 **📥 导出版本有效DI-Excel** 下载筛选后的数据
        """)


# 渲染侧边栏
with st.sidebar:
    render_sidebar()

# 主页面内容
main_content()

