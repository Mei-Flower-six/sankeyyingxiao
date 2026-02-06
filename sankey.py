# sankey_traffic_streamlit.py
import pandas as pd
import plotly.graph_objects as go
import logging
import streamlit as st
from datetime import datetime

# ===================== 1. 页面配置 =====================
st.set_page_config(
    page_title="多站点流量-销量桑基图分析",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== 2. 全局配置 =====================
SITE_CONFIG = {
    "Amazon-US": {"cn_name": "亚马逊美国站", "color": "#87CEEB"},
    "Amazon-JP": {"cn_name": "亚马逊日本站", "color": "#FF6B6B"},
    "Amazon-UK": {"cn_name": "亚马逊英国站", "color": "#4ECDC4"},
    "Shopify": {"cn_name": "Shopify独立站", "color": "#DDA0DD"}
}

# 流量类型排序（包含Amazon页面总点击，与Excel值完全一致）
TRAFFIC_ORDER = [
    "Amazon站内广告",   # 1
    "Amazon-DSP",       # 2
    "Amazon自然流量",   # 3
    "Amazon-FB",        # 4
    "Amazon页面总点击", # 5 与Excel流量类型完全匹配
    "SP-GG",            # 6
    "SP-FB",            # 7
    "SP-自然",          # 8
    "SP-其他"           # 9
]

# 流量映射（确保Amazon页面总点击配置与Excel一致）
TRAFFIC_MAPPING = {
    "Amazon站内广告": {
        "group_id": "组1",
        "site": "Amazon-US",
        "nodes": {
            "exposure": "站内曝光",
            "level2_exposure": "Amazon-US曝光",
            "click": "站内点击",
            "level2_click": "Amazon-US点击",
            "sales": "站内销量",
            "level2_sales": "Amazon-US销量"
        }
    },
    "Amazon-DSP": {
        "group_id": "组2",
        "site": "Amazon-US",
        "nodes": {
            "exposure": "DSP曝光",
            "level2_exposure": "Amazon-US曝光",
            "click": "DSP点击",
            "level2_click": "Amazon-US点击",
            "sales": "DSP销量",
            "level2_sales": "Amazon-US销量"
        }
    },
    "Amazon自然流量": {
        "group_id": "组3",
        "site": "Amazon-US",
        "nodes": {
            "exposure": "Amazon自然曝光",
            "level2_exposure": "Amazon-US曝光",
            "click": "Amazon自然点击",
            "level2_click": "Amazon-US点击",
            "sales": "Amazon自然销量",
            "level2_sales": "Amazon-US销量"
        }
    },
    "Amazon-FB": {
        "group_id": "组4",
        "site": "Amazon-US",
        "nodes": {
            "exposure": "FB曝光",
            "level2_exposure": "Amazon-US曝光",
            "click": "FB点击",
            "level2_click": "Amazon-US点击",
            "sales": "FB销量",
            "level2_sales": "Amazon-US销量"
        }
    },
    # 核心修改：Amazon页面总点击配置（key与Excel流量类型完全一致）
    "Amazon页面总点击": {
        "group_id": "组5",
        "site": "Amazon-US",
        "nodes": {
            "exposure": "Amazon页面总点击曝光",
            "level2_exposure": "Amazon-US曝光",
            "click": "Amazon页面总点击",
            "level2_click": "Amazon-US点击",
            "sales": "Amazon页面总点击销量",
            "level2_sales": "Amazon-US销量"
        }
    },
    "SP-GG": {
        "group_id": "组6",
        "site": "Shopify",
        "nodes": {
            "exposure": "SP-GG曝光",
            "level2_exposure": "Shopify曝光",
            "click": "SP-GG点击",
            "level2_click": "Shopify点击",
            "sales": "SP-GG销量",
            "level2_sales": "Shopify销量"
        }
    },
    "SP-FB": {
        "group_id": "组7",
        "site": "Shopify",
        "nodes": {
            "exposure": "SP-FB曝光",
            "level2_exposure": "Shopify曝光",
            "click": "SP-FB点击",
            "level2_click": "Shopify点击",
            "sales": "SP-FB销量",
            "level2_sales": "Shopify销量"
        }
    },
    "SP-自然": {
        "group_id": "组8",
        "site": "Shopify",
        "nodes": {
            "exposure": "SP-自然曝光",
            "level2_exposure": "Shopify曝光",
            "click": "SP-自然点击",
            "level2_click": "Shopify点击",
            "sales": "SP-自然销量",
            "level2_sales": "Shopify销量"
        }
    },
    "SP-其他": {
        "group_id": "组9",
        "site": "Shopify",
        "nodes": {
            "exposure": "SP-其他曝光",
            "level2_exposure": "Shopify曝光",
            "click": "SP-其他点击",
            "level2_click": "Shopify点击",
            "sales": "SP-其他销量",
            "level2_sales": "Shopify销量"
        }
    }
}

# 分组颜色（包含组5：Amazon页面总点击）
GROUP_COLORS = {
    "组1": "#9290E6",  # 站内广告
    "组2": "#4ECDC4",  # DSP
    "组3": "#45B7D1",  # 自然流量
    "组4": "#96CEB4",  # FB
    "组5": "#6FA8DC",  # Amazon页面总点击（蓝色系匹配Amazon站点）
    "组6": "#FFA726",  # SP-GG
    "组7": "#AB47BC",  # SP-FB
    "组8": "#1C363F",  # SP-自然
    "组9": "#F00B0B",  # SP-其他
    **{site: SITE_CONFIG[site]["color"] for site in SITE_CONFIG},
    "总节点": "lightgray"
}

# 动态生成level2节点列表
LEVEL2_NODES = []
for traffic_type in TRAFFIC_MAPPING:
    cfg = TRAFFIC_MAPPING[traffic_type]
    LEVEL2_NODES.extend([
        cfg["nodes"]["level2_exposure"],
        cfg["nodes"]["level2_click"],
        cfg["nodes"]["level2_sales"]
    ])
LEVEL2_NODES = list(set(LEVEL2_NODES))

# 节点→流量类型映射
NODE_TO_TRAFFIC = {}
for traffic_type in TRAFFIC_MAPPING:
    cfg = TRAFFIC_MAPPING[traffic_type]
    unique_nodes = [
        traffic_type,
        cfg["nodes"]["exposure"],
        cfg["nodes"]["click"],
        cfg["nodes"]["sales"]
    ]
    for node in unique_nodes:
        NODE_TO_TRAFFIC[node] = traffic_type

# 无效流量类型过滤列表（已移除Amazon页面总点击）
INVALID_TRAFFIC_TYPES = ["总曝光", "总点击", "总销量"]

# ===================== 3. 读取Excel函数（核心修改：兼容数值空值+显示排查日志） =====================
@st.cache_data
def read_excel_generate_data(excel_path):
    try:
        df = pd.read_excel(excel_path)
        logger.info(f"成功读取Excel文件，数据行数：{len(df)}")
        # 新增：显示Excel列名和前2行，方便排查列名匹配问题
        st.success(f"✅ 成功读取Excel文件，数据行数：{len(df)}")
        st.info(f"📋 Excel列名：{', '.join(df.columns.tolist())}")
        st.info("🔍 Excel前2行数据预览：")
        st.dataframe(df.head(2).style.set_caption("Excel数据格式验证"))
        
    except Exception as e:
        logger.error(f"读取Excel失败：{str(e)}")
        st.error(f"❌ 读取Excel失败：{str(e)}")
        return pd.DataFrame()
    
    # 数据预处理：时间列处理
    if "时间" not in df.columns:
        st.error("❌ Excel缺少「时间」列，请检查列名")
        return pd.DataFrame()
    
    df["时间_str"] = df["时间"].astype(str)
    df["date"] = df["时间_str"].str.split(" ").str[0].str.replace("/", "-")
    df["date"] = df["date"].replace(["nan", "NaT", ""], pd.NaT)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # 新增：显示时间列处理结果，排查日期格式问题
    valid_date_count = df["date"].notna().sum()
    st.info(f"📅 时间列处理结果：有效日期行数{valid_date_count} / 总行数{len(df)}")
    if valid_date_count == 0:
        st.warning("⚠️ 未识别到有效日期，请检查Excel「时间」列格式（建议格式：2026/1/5）")

    # 检查核心数值列是否存在
    required_cols = ["流量类型", "曝光", "点击", "销量"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"❌ Excel缺少核心列：{', '.join(missing_cols)}，请补充后重新上传")
        return pd.DataFrame()

    data_raw = []
    skipped_count = 0  # 统计被跳过的行数
    for idx, row in df.iterrows():
        # 1. 过滤空日期
        if pd.isna(row["date"]):
            skipped_count +=1
            continue
        
        # 2. 过滤无效流量类型
        traffic_type = str(row["流量类型"]).strip()  # 去除空格，避免匹配失败
        if traffic_type in INVALID_TRAFFIC_TYPES:
            skipped_count +=1
            continue
        
        # 3. 过滤未配置的流量类型（并提示具体值）
        if traffic_type not in TRAFFIC_MAPPING:
            skipped_count +=1
            st.warning(f"⚠️ 第{idx+1}行：流量类型「{traffic_type}」未在代码中配置，已跳过")
            continue
        
        # 4. 过滤非法站点
        cfg = TRAFFIC_MAPPING[traffic_type]
        if cfg["site"] not in SITE_CONFIG:
            skipped_count +=1
            continue
        
        # 核心修改：兼容数值列空值/None（将None、空字符串转为0.0）
        exposure = pd.to_numeric(row["曝光"], errors="coerce") if (pd.notna(row["曝光"]) and str(row["曝光"]).strip() != "") else 0.0
        click = pd.to_numeric(row["点击"], errors="coerce") if (pd.notna(row["点击"]) and str(row["点击"]).strip() != "") else 0.0
        sales = pd.to_numeric(row["销量"], errors="coerce") if (pd.notna(row["销量"]) and str(row["销量"]).strip() != "") else 0.0
        date = row["date"].strftime("%Y-%m-%d")
        
        # 生成链路数据
        data_raw.extend([
            [traffic_type, cfg["nodes"]["exposure"], float(exposure), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["exposure"], cfg["nodes"]["level2_exposure"], float(exposure), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["level2_exposure"], "总曝光", float(exposure), date, cfg["group_id"], traffic_type],
            ["总曝光", cfg["nodes"]["click"], float(click), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["click"], cfg["nodes"]["level2_click"], float(click), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["level2_click"], "总点击", float(click), date, cfg["group_id"], traffic_type],
            ["总点击", cfg["nodes"]["sales"], float(sales), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["sales"], cfg["nodes"]["level2_sales"], float(sales), date, cfg["group_id"], traffic_type],
            [cfg["nodes"]["level2_sales"], "总销量", float(sales), date, cfg["group_id"], traffic_type]
        ])
    
    # 显示数据过滤统计，方便排查
    st.info(f"🔍 数据过滤统计：总行数{len(df)} → 跳过{skipped_count}行 → 有效链路数据{len(data_raw)}条")
    if len(data_raw) == 0:
        st.error("❌ 未生成有效链路数据，请根据上述提示检查Excel内容")
        return pd.DataFrame()
    
    # 最终数据处理
    result_df = pd.DataFrame(data_raw, columns=["source", "target", "value", "date", "group", "traffic_type"])
    result_df["date"] = pd.to_datetime(result_df["date"])
    result_df["value"] = pd.to_numeric(result_df["value"], errors="coerce").fillna(0.0)
    logger.info(f"生成链路数据条数：{len(result_df)}")
    return result_df

# ===================== 4. 应用标题 =====================
st.title("🌐 多站点流量-销量桑基图分析")
st.markdown("---")

# ===================== 5. 文件上传和数据加载 =====================
default_excel_path = "1.5-1.19流量数据统计.xlsx"
df = pd.DataFrame()

with st.sidebar:
    st.header("⚙️ 控制面板")
    # 文件上传
    uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx", "xls"])

# 确定Excel文件路径并加载数据
if uploaded_file is not None:
    EXCEL_PATH = uploaded_file
    df = read_excel_generate_data(EXCEL_PATH)
    st.sidebar.success(f"📂 已上传文件: {uploaded_file.name}")
else:
    # 本地测试默认文件
    try:
        df = read_excel_generate_data(default_excel_path)
        st.sidebar.info(f"📂 使用默认文件: {default_excel_path}")
    except Exception as e:
        st.sidebar.error(f"❌ 默认文件加载失败: {str(e)}")

# 提取Excel中的实际有效日期范围
default_start_date = datetime.strptime("2026-01-05", "%Y-%m-%d").date()
default_end_date = datetime.strptime("2026-01-19", "%Y-%m-%d").date()

if not df.empty and df["date"].notna().any():
    min_date = df["date"].min()
    max_date = df["date"].max()
    default_start_date = min_date.date()
    default_end_date = max_date.date()
    logger.info(f"自动提取Excel日期范围：{default_start_date} 至 {default_end_date}")
else:
    logger.warning("未提取到有效日期，使用兜底默认值")

# ===================== 6. 侧边栏其他控件 =====================
with st.sidebar:
    # 搜索区域（支持搜索Amazon页面总点击）
    search_keyword = st.text_input(
        "🔍 链路搜索（支持站点/流量类型关键词）",
        placeholder="输入关键词（如页面总点击/US/Shopify）",
        help="支持搜索「页面总点击」快速定位新增链路"
    )
    
    # 清空搜索按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空搜索", type="secondary", use_container_width=True):
            search_keyword = ""
            st.rerun()
    
    st.markdown("---")
    st.subheader("📅 日期范围")
    
    # 日期输入
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=default_start_date,
            help="默认显示Excel中的最早日期"
        )
    
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=default_end_date,
            help="默认显示Excel中的最晚日期"
        )
    
    # 日期验证
    if start_date > end_date:
        st.warning("⚠️ 开始日期不能晚于结束日期，已自动交换")
        start_date, end_date = end_date, start_date
    
    st.markdown("---")
    st.subheader("📏 缩放控制")
    
    # 缩放系数
    col1, col2 = st.columns(2)
    with col1:
        exposure_scale = st.number_input(
            "曝光链路缩放",
            min_value=0.01,
            max_value=10.0,
            value=0.5,
            step=0.05,
            help="调整曝光链路的宽度"
        )
    
    with col2:
        later_scale = st.number_input(
            "后续链路缩放",
            min_value=0.01,
            max_value=50.0,
            value=5.0,
            step=1.0,
            help="调整点击和销量链路的宽度"
        )
    
    st.markdown("---")
    st.info("💡 提示：点击图表节点可查看流入/流出数据及占比")

# ===================== 7. 数据验证 =====================
if df.empty:
    st.error("❌ 无有效数据可展示，请根据上方提示检查Excel文件后重新上传")
    st.stop()

# ===================== 8. 数据筛选和处理 =====================
# 显示数据摘要
with st.expander("📊 数据摘要", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_records = len(df)
        st.metric("总链路记录数", total_records)
    
    with col2:
        traffic_types = df["traffic_type"].nunique()
        st.metric("有效流量类型数", traffic_types)
    
    with col3:
        total_exposure = df[df["source"].str.contains("曝光")]["value"].sum()
        st.metric("总曝光量", f"{total_exposure:,.0f}")
    
    with col4:
        total_sales = df[df["source"].str.contains("销量")]["value"].sum()
        st.metric("总销量", f"{total_sales:,.0f}")

# 数据筛选聚合
start_date_dt = pd.Timestamp(start_date)
end_date_dt = pd.Timestamp(end_date)
filtered_df = df[(df["date"] >= start_date_dt) & (df["date"] <= end_date_dt)]
aggregated_df = filtered_df.groupby(["source", "target", "group", "traffic_type"], as_index=False)["value"].sum()
aggregated_df = aggregated_df[aggregated_df["value"] > 0]

# ===================== 9. 生成节点列表 =====================
# 拆分Amazon和Shopify流量类型
Amazon_TRAFFIC = [t for t in TRAFFIC_ORDER if TRAFFIC_MAPPING[t]["site"] == "Amazon-US"]
Shopify_TRAFFIC = [t for t in TRAFFIC_ORDER if TRAFFIC_MAPPING[t]["site"] == "Shopify"]

# Amazon组节点（包含页面总点击）
Amazon_flow_sources = Amazon_TRAFFIC
Amazon_exposure_nodes = [TRAFFIC_MAPPING[t]["nodes"]["exposure"] for t in Amazon_TRAFFIC]
Amazon_level2_exposure = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_exposure"] for t in Amazon_TRAFFIC]))
Amazon_click_nodes = [TRAFFIC_MAPPING[t]["nodes"]["click"] for t in Amazon_TRAFFIC]
Amazon_level2_click = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_click"] for t in Amazon_TRAFFIC]))
Amazon_sales_nodes = [TRAFFIC_MAPPING[t]["nodes"]["sales"] for t in Amazon_TRAFFIC]
Amazon_level2_sales = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_sales"] for t in Amazon_TRAFFIC]))

# Shopify组节点
Shopify_flow_sources = Shopify_TRAFFIC
Shopify_exposure_nodes = [TRAFFIC_MAPPING[t]["nodes"]["exposure"] for t in Shopify_TRAFFIC]
Shopify_level2_exposure = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_exposure"] for t in Shopify_TRAFFIC]))
Shopify_click_nodes = [TRAFFIC_MAPPING[t]["nodes"]["click"] for t in Shopify_TRAFFIC]
Shopify_level2_click = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_click"] for t in Shopify_TRAFFIC]))
Shopify_sales_nodes = [TRAFFIC_MAPPING[t]["nodes"]["sales"] for t in Shopify_TRAFFIC]
Shopify_level2_sales = list(set([TRAFFIC_MAPPING[t]["nodes"]["level2_sales"] for t in Shopify_TRAFFIC]))

# 总节点
total_nodes = ["总曝光", "总点击", "总销量"]

# 拼接所有节点（Amazon在前，Shopify在后）
all_nodes = (
    Amazon_flow_sources + Amazon_exposure_nodes + Amazon_level2_exposure + 
    total_nodes[:1] +  # 总曝光
    Amazon_click_nodes + Amazon_level2_click + 
    total_nodes[1:2] +  # 总点击
    Amazon_sales_nodes + Amazon_level2_sales + 
    Shopify_flow_sources + Shopify_exposure_nodes + Shopify_level2_exposure + 
    Shopify_click_nodes + Shopify_level2_click + 
    Shopify_sales_nodes + Shopify_level2_sales + 
    total_nodes[2:]  # 总销量
)

node_ids = {node: idx for idx, node in enumerate(all_nodes)}

# ===================== 10. 节点统计 =====================
node_stats = {}
for node in all_nodes:
    incoming = aggregated_df[aggregated_df["target"] == node]["value"].sum()
    outgoing = aggregated_df[aggregated_df["source"] == node]["value"].sum()
    node_stats[node] = (incoming, outgoing)

# 总节点数值（用于计算占比）
total_node_values = {
    "总曝光": node_stats.get("总曝光", (0, 0))[0],
    "总点击": node_stats.get("总点击", (0, 0))[0],
    "总销量": node_stats.get("总销量", (0, 0))[0]
}

# 节点自定义数据（包含占比）
node_customdata = []
for node in all_nodes:
    incoming = node_stats[node][0]
    outgoing = node_stats[node][1]
    ratio = ""
    
    if node not in ["总曝光", "总点击", "总销量"]:
        if "曝光" in node and total_node_values["总曝光"] > 0:
            ratio = f"占总曝光：{round((outgoing / total_node_values['总曝光']) * 100, 2)}%"
        elif "点击" in node and total_node_values["总点击"] > 0:
            ratio = f"占总点击：{round((outgoing / total_node_values['总点击']) * 100, 2)}%"
        elif "销量" in node and total_node_values["总销量"] > 0:
            ratio = f"占总销量：{round((outgoing / total_node_values['总销量']) * 100, 2)}%"
    
    node_customdata.append((incoming, outgoing, ratio))

# ===================== 11. 搜索关键词匹配 =====================
search_keyword = search_keyword.strip().lower() if isinstance(search_keyword, str) else ""
matched_traffic_types = []

if not search_keyword:
    matched_traffic_types = TRAFFIC_ORDER
else:
    # 匹配站点或流量类型
    matched_sites = [site for site in SITE_CONFIG if search_keyword in site.lower() or search_keyword in SITE_CONFIG[site]["cn_name"].lower()]
    if matched_sites:
        matched_traffic_types = [t for t in TRAFFIC_ORDER if TRAFFIC_MAPPING[t]["site"] in matched_sites]
    else:
        matched_traffic_types = [t for t in TRAFFIC_ORDER if search_keyword in t.lower()]

# 匹配节点列表
matched_nodes = []
for traffic_type in matched_traffic_types:
    cfg = TRAFFIC_MAPPING[traffic_type]
    matched_nodes.extend([
        traffic_type,
        cfg["nodes"]["exposure"],
        cfg["nodes"]["click"],
        cfg["nodes"]["sales"],
        cfg["nodes"]["level2_exposure"],
        cfg["nodes"]["level2_click"],
        cfg["nodes"]["level2_sales"]
    ])
matched_nodes = list(set(matched_nodes))

# ===================== 12. 生成链路 =====================
total_incoming = aggregated_df.groupby("target")["value"].sum().to_dict()
exposure_link = [
    (s, TRAFFIC_MAPPING[s]["nodes"]["exposure"]) for s in TRAFFIC_ORDER
] + [
    (TRAFFIC_MAPPING[s]["nodes"]["exposure"], TRAFFIC_MAPPING[s]["nodes"]["level2_exposure"]) for s in TRAFFIC_ORDER
] + [
    (TRAFFIC_MAPPING[s]["nodes"]["level2_exposure"], "总曝光") for s in TRAFFIC_ORDER
]

link_sources = []
link_targets = []
link_values = []
link_customdata = []
link_colors = []

for _, row in aggregated_df.iterrows():
    source = row["source"]
    target = row["target"]
    original_val = row["value"]
    group = row["group"]
    traffic_type = row["traffic_type"]
    
    # 链路匹配与缩放
    is_matched = traffic_type in matched_traffic_types
    is_exposure = (source, target) in exposure_link
    base_scaled_val = original_val * (exposure_scale if is_exposure else later_scale)
    final_val = base_scaled_val if is_matched else base_scaled_val * 0.05
    
    # 计算占比
    target_total = total_incoming.get(target, 1)
    ratio = round((original_val / target_total) * 100, 2)
    
    # 链路颜色
    final_color = GROUP_COLORS[group] if is_matched else "rgba(200, 200, 200, 0.2)"
    
    # 收集链路数据
    link_sources.append(node_ids[source])
    link_targets.append(node_ids[target])
    link_values.append(final_val)
    link_colors.append(final_color)
    link_customdata.append([source, target, original_val, ratio])

# ===================== 13. 节点颜色 =====================
node_color_list = []
for node in all_nodes:
    if node in matched_nodes:
        if node in NODE_TO_TRAFFIC:
            traffic_type = NODE_TO_TRAFFIC[node]
            node_color = GROUP_COLORS[TRAFFIC_MAPPING[traffic_type]["group_id"]]
        else:
            node_color = GROUP_COLORS.get(
                next((site for site in SITE_CONFIG if site in node), "总节点"),
                "lightgray"
            )
    else:
        node_color = "rgba(200, 200, 200, 0.2)"
    node_color_list.append(node_color)

# ===================== 14. 绘制桑基图 =====================
fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=20,
        thickness=30,
        line=dict(color="black", width=1),
        label=all_nodes,
        color=node_color_list,
        hovertemplate="%{label}<br>流入：%{customdata[0]:.0f}<br>流出：%{customdata[1]:.0f}<br>%{customdata[2]}<extra></extra>",
        customdata=node_customdata
    ),
    link=dict(
        source=link_sources,
        target=link_targets,
        value=link_values,
        color=link_colors,
        hovertemplate="%{customdata[0]}→%{customdata[1]}<br>原始数值：%{customdata[2]:.0f}<br>占%{customdata[1]}总流入：%{customdata[3]:.2f}%<extra></extra>",
        customdata=link_customdata
    )
)])

# 图表标题（包含搜索关键词）
title_text = f"多站点流量转化路径（{start_date} 至 {end_date}）"
if search_keyword:
    title_text += f" | 高亮：{search_keyword}"

fig.update_layout(
    title_text=title_text,
    font_size=12,
    autosize=True,
    margin=dict(l=20, r=20, t=50, b=20),
    font=dict(family="Microsoft YaHei"),
    height=800
)

# 显示图表
st.plotly_chart(fig, use_container_width=True, height=800)

# ===================== 15. 数据显示区域 =====================
with st.expander("📋 查看详细数据", expanded=False):
    tab1, tab2, tab3 = st.tabs(["原始链路数据", "流量类型统计", "站点配置"])
    
    with tab1:
        st.dataframe(filtered_df.head(100).style.set_caption("筛选后的前100条链路数据"))
    
    with tab2:
        # 流量类型汇总统计
        traffic_summary = filtered_df.groupby("traffic_type").agg({
            "value": ["sum", "count"]
        }).round(2)
        traffic_summary.columns = ["总数值", "记录数"]
        st.dataframe(traffic_summary.style.set_caption("各流量类型数据统计"))
    
    with tab3:
        # 站点配置与流量类型分布
        st.subheader("站点配置详情")
        site_df = pd.DataFrame([
            {"站点标识": site, "中文名称": info["cn_name"], "颜色代码": info["color"]}
            for site, info in SITE_CONFIG.items()
        ])
        st.dataframe(site_df)
        
        st.subheader("流量类型分布")
        traffic_dist = pd.DataFrame([
            {"流量类型": t, "所属站点": TRAFFIC_MAPPING[t]["site"], "分组ID": TRAFFIC_MAPPING[t]["group_id"]}
            for t in TRAFFIC_ORDER
        ])
        st.dataframe(traffic_dist)

# ===================== 16. 页脚信息 =====================
st.markdown("---")
st.caption(f"📅 数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 操作提示：1. 上传Excel后可查看数据排查日志；2. 搜索「页面总点击」可快速定位新增链路")
