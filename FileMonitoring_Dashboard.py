# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, timedelta
import pandas as pd
from st_keyup import st_keyup
import streamlit as st
from supabase import Client, create_client

# --- 1. CONFIG & STYLES ---
st.set_page_config(
    page_title="Sales Monitoring",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebarContent"] { padding-top: 0rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }
    .block-container { padding-top: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; padding-bottom: 0rem !important; }
    
    button[kind="primary"] { background-color: #28a745 !important; border-color: #28a745 !important; color: white !important; }
    .problem-item { font-size: 0.85rem; padding: 8px 10px; background-color: #fff5f5; border-left: 4px solid #ff4b4b; border-radius: 4px; margin-bottom: 6px; }
    footer { visibility: hidden; }

    /* ปรับแต่งปุ่ม Back to Main Page */
    div.stButton > button[key="back_to_welcome"] {
        background-color: #1e293b !important; color: white !important; border: none !important;
        border-radius: 6px !important; padding: 0.4rem 0.8rem !important;
        font-weight: 600 !important; font-size: 0.8rem !important; width: 100% !important; margin-top: 10px !important;
    }

    /* ปรับขนาดตัวอักษรในช่อง Input ของหน้า Config */
    div[data-testid="stExpander"] input { font-size: 0.9rem !important; }

    /* 🔴 ปรับคอลัมน์ที่ 2 (เปิด-ปิดร้าน) → เปิดเป็นสีแดง */
    [data-testid="stExpander"] [data-testid="column"]:nth-child(2) [data-testid="stToggle"] label:has(input:checked) > span:first-of-type {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
    }
    [data-testid="stExpander"] [data-testid="column"]:nth-child(2) input[type="checkbox"]:checked + span {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
    }

    /* 🔴 ปรับคอลัมน์ที่ 3 (เปิด-ปิดส่งยอด) → เปิดเป็นสีแดง */
    [data-testid="stExpander"] [data-testid="column"]:nth-child(3) [data-testid="stToggle"] label:has(input:checked) > span:first-of-type {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
    }
    [data-testid="stExpander"] [data-testid="column"]:nth-child(3) input[type="checkbox"]:checked + span {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
    }    
    </style>
    """,
    unsafe_allow_html=True,
)

# --- SUPABASE INITIALIZATION ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


@st.cache_resource
def init_supabase() -> Client:
  return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()

# --- BRAND LIST ---
BRAND_LIST = [
    "Eat Am Are",
    "JonesSalad",
    "Laem Charoen Seafood",
    "Saemaeul/BHC/Solsot",
    "Tenjo",
    "Senju",
    "Wisdom",
    "Seefah",
    "Bake Brother",
    "Ohsho",
    "ตั่วเปา",
    "Maesriruen",
    "You&I",
    "เสวย",
    "Shinkanzen",
    "Tudari",
    "Spaghetti",
    "DaddyDough",
    "DeanAndDeluca",
    "Missmamon&Taroto",
    "Lukkaithong",
    "Kaithong",
    "Shwepalin",
    "CocaSuki",
    "BaanSomtum",
    "HormCafe",
    "Bangkok Air",
    "Thammachart Seafood",
    "Bangkok Pulse",
]


# --- 2. DATA FETCHING (SUPABASE) ---
def get_config():
  try:
    response = (
        supabase.table("app_config")
        .select("config_data")
        .eq("id", "main_config")
        .execute()
    )
    if response.data:
      return response.data[0].get("config_data", {})
  except Exception as e:
    st.error(f"Error loading config from Supabase: {e}")
  return {}


def save_config(full_config):
  try:
    supabase.table("app_config").upsert(
        {"id": "main_config", "config_data": full_config}
    ).execute()
  except Exception as e:
    st.error(f"Error saving config to Supabase: {e}")


@st.cache_data(ttl=30)
def get_data_from_supabase(brand_name, year, month):
  try:
    start_date = f"{year}-{month:02d}-01"
    _, last_day = calendar.monthrange(year, month)
    end_date = f"{year}-{month:02d}-{last_day:02d} 23:59:59"

    response = (
        supabase.table("file_status")
        .select("*")
        .eq("brand_name", brand_name)
        .gte("sync_date", start_date)
        .lte("sync_date", end_date)
        .execute()
    )

    df = pd.DataFrame(response.data)
    if not df.empty:
      for col in ["status_code", "status_log", "status_realtime"]:
        if col in df.columns:
          df[col] = pd.to_numeric(df[col], errors="coerce")
      df["sync_date"] = pd.to_datetime(df["sync_date"])
      return df
  except Exception as e:
    st.error(f"Error fetching data from Supabase: {e}")
  return pd.DataFrame()


# --- 3. SIDEBAR ---
with st.sidebar:
  now = datetime.utcnow() + timedelta(hours=7)
  current_full_config = get_config()
  monitors_config = current_full_config.get("_monitors", {})

  def sort_brands_logic(b_name):
    return int(monitors_config.get(b_name, {}).get("order", 999))

  brand_keys = sorted(BRAND_LIST, key=sort_brands_logic)
  DEFAULT_COLORS = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0"]

  if "selected_brand" not in st.session_state:
    st.session_state.selected_brand = "🛑 SELECT BRAND 🛑"

  st.markdown(
      """
        <style>
        div[data-testid="stSidebar"] button[kind="secondary"] { padding: 1px 2px !important; min-height: 32px !important; font-size: 0.6rem !important; }
        div[data-testid="stSidebar"] button[kind="primary"] {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%) !important;
            border: none !important; color: #f1f5f9 !important; font-size: 0.75rem !important;
            font-weight: 600 !important; border-radius: 6px !important; padding: 6px 0 !important;
        }
        </style>
    """,
      unsafe_allow_html=True,
  )

  # 1. Date & Time card
  st.markdown(
      f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                    padding: 12px 15px; border-radius: 12px; margin-bottom: 10px; 
                    border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase; letter-spacing: 0.5px;">📅 Today</div>
                    <div style="font-size:0.95rem; font-weight:700; color:#f8fafc;">{now.strftime("%d %b %Y")}</div>
                </div>
                <div style="text-align: right; border-left: 1px solid rgba(148, 163, 184, 0.3); padding-left: 12px;">
                    <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase; letter-spacing: 0.5px;">🕒 Time</div>
                    <div style="font-size:1.1rem; font-weight:800; color:#38bdf8;">{now.strftime("%H:%M")}</div>
                </div>
            </div>
        </div>
    """,
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)

  view_mode = st.radio(
      "Display Mode",
      ["📋 History (Log)", "⚡ Real-time"],
      index=0,
      horizontal=True,
      label_visibility="collapsed",
  )
  st.markdown(
      "<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True
  )

  # 2. Brand selector
  st.markdown(
      "<div style='font-size:0.65rem; font-weight:600; color:#64748b;"
      " text-transform:uppercase; margin-bottom:4px;'>เลือกแบรนด์</div>",
      unsafe_allow_html=True,
  )

  selected_brand = st.session_state.selected_brand

  if selected_brand == "🛑 SELECT BRAND 🛑":
    display_brands = brand_keys
  else:
    display_brands = [selected_brand]

  for i, brand in enumerate(display_brands):
    original_idx = brand_keys.index(brand)
    cfg = monitors_config.get(brand, {})
    color = cfg.get("color", DEFAULT_COLORS[original_idx % len(DEFAULT_COLORS)])

    m1 = cfg.get("m1", "")
    m2 = cfg.get("m2", "")
    monitors_text = " / ".join([x for x in [m1, m2] if x]) or "—"

    # ดึง Config รายสาขามาเช็คว่าถูกปิดใช้งานทั้งหมดหรือไม่
    brand_shops_cfg = current_full_config.get(brand, {})
    is_all_disabled = False
    if brand_shops_cfg and isinstance(brand_shops_cfg, dict):
      all_disabled_checks = []
      for s_name, s_val in brand_shops_cfg.items():
        if isinstance(s_val, dict):
          all_disabled_checks.append(
              not s_val.get("active", True)
              and not s_val.get("sync_active", True)
          )
        else:
          all_disabled_checks.append(not s_val)

      if all_disabled_checks and all(all_disabled_checks):
        is_all_disabled = True

    is_active = selected_brand == brand
    bg = f"{color}25" if is_active else f"{color}10"
    border_w = "4px" if is_active else "2px"

    col_band, col_btn = st.columns([5, 1.2])
    with col_band:
      disabled_suffix = (
          ' <span style="color:#dc3545; font-size:0.75rem;'
          ' font-weight:700;">(ปิดการ Monitor ยอดขาย)</span>'
          if is_all_disabled
          else ""
      )

      st.markdown(
          f'<div style="border-left:{border_w} solid {color}; background:{bg};'
          " padding:4px 8px; border-radius:0 6px 6px 0; margin:2px"
          ' 0;"><div style="font-size:0.9rem;'
          f' font-weight:{"700" if is_active else "500"};'
          ' color:{"#0f172a" if is_active else "#475569"};'
          f' line-height:1.2;">{brand}{disabled_suffix}</div><div'
          f' style="font-size:0.75rem; color:{color};'
          f' font-weight:600;">{monitors_text}</div></div>',
          unsafe_allow_html=True,
      )
    with col_btn:
      btn_label = "▶" if selected_brand == "🛑 SELECT BRAND 🛑" else "🔄"
      if st.button(
          btn_label, key=f"brand_btn_{brand}", use_container_width=True
      ):
        st.session_state.selected_brand = brand
        st.rerun()
  selected_brand = st.session_state.selected_brand

  # 3. ปี / เดือน
  st.markdown("<div style='margin-top:5px'></div>", unsafe_allow_html=True)
  col_y, col_m = st.columns(2)
  with col_y:
    y = st.selectbox("ปี", [2025, 2026], index=1, key="sb_year")
  with col_m:
    month_list = list(calendar.month_name)[1:]
    m_name = st.selectbox(
        "เดือน", month_list, index=now.month - 1, key="sb_month"
    )
    m = month_list.index(m_name) + 1

  summary_placeholder = st.empty()
  st.markdown(
      "<hr style='border:none; border-top:1px solid #e2e8f0; margin:8px 0;'>",
      unsafe_allow_html=True,
  )

  # ── 4. Settings ──
  if selected_brand == "🛑 SELECT BRAND 🛑":
    with st.expander("👤 User Configuration", expanded=False):
      pwd = st.text_input(
          "กรอกรหัสผ่านเพื่อแก้ไข", type="password", key="admin_pwd"
      )
      if pwd == "SYN1234":
        st.success("Login Success")
        new_monitors = {}
        for i, brand in enumerate(BRAND_LIST):
          saved = monitors_config.get(brand, {})
          cfg_color = saved.get(
              "color", DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
          )
          cfg_order = saved.get("order", i + 1)

          st.markdown(
              f"<div style='border-left:4px solid {cfg_color};"
              " padding-left:7px; font-size:0.9rem; font-weight:700;"
              f" margin-top:10px; margin-bottom:5px;'>{brand}</div>",
              unsafe_allow_html=True,
          )

          c_ord, c1, c2, c3 = st.columns([0.7, 2, 2, 1])
          with c_ord:
            ord_val = st.number_input(
                "ลำดับ",
                value=int(cfg_order),
                min_value=1,
                step=1,
                key=f"mon_ord_{brand}",
                label_visibility="collapsed",
            )
          with c1:
            m1_val = st.text_input(
                "มือ1",
                value=saved.get("m1", ""),
                key=f"mon_m1_{brand}",
                label_visibility="collapsed",
                placeholder="มือ 1",
            )
          with c2:
            m2_val = st.text_input(
                "มือ2",
                value=saved.get("m2", ""),
                key=f"mon_m2_{brand}",
                label_visibility="collapsed",
                placeholder="มือ 2",
            )
          with c3:
            color_val = st.color_picker(
                "Color",
                value=cfg_color,
                key=f"mon_color_{brand}",
                label_visibility="collapsed",
            )

          new_monitors[brand] = {
              "m1": m1_val.strip(),
              "m2": m2_val.strip(),
              "color": color_val,
              "order": int(ord_val),
          }

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "💾 บันทึกการตั้งค่า",
            type="primary",
            use_container_width=True,
            key="save_brand_config",
        ):
          current_full_config["_monitors"] = new_monitors
          save_config(current_full_config)
          st.success("บันทึกสำเร็จ!")
          st.rerun()
      elif pwd != "":
        st.error("รหัสผ่านไม่ถูกต้อง")

# --- 4. MAIN CONTENT ---
if selected_brand == "🛑 SELECT BRAND 🛑":
  st.markdown(
      """
        <style>
        [data-testid="stAppViewBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
        .full-screen-welcome {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            height: 100vh; width: 100%; display: flex; flex-direction: column;
            justify-content: center; align-items: center; color: white; text-align: center;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1); padding: 60px; border-radius: 40px;
        }
        </style>
        <div class="full-screen-welcome">
            <div class="glass-card">
                <div style="font-size: 5rem; margin-bottom: 20px;">📈</div>
                <h1 style="font-size: 4rem; font-weight: 800;">Sales Monitoring System</h1>
                <p style="font-size: 1.2rem; opacity: 0.7;">History&Realtime Tracking Dashboard (Supabase Powered)</p>
            </div>
        </div>
    """,
      unsafe_allow_html=True,
  )
  st.stop()

# --- 5. DASHBOARD VIEW ---
header_mode_suffix = (
    "(Real-time)" if "⚡ Real-time" in view_mode else "(History Log)"
)
st.markdown(
    "### 📊 Sales Monitoring Heatmap :"
    f" {selected_brand} <small style='color:#666;"
    f" font-size:14px;'>{header_mode_suffix}</small>",
    unsafe_allow_html=True,
)

col_sort_radio, col_info_show = st.columns([1.5, 2.5])

with col_sort_radio:
  st.markdown(
      "<div style='font-size:0.85rem; font-weight:600; color:#1e293b;"
      " margin-top:5px;'>🔀 จัดเรียงลำดับข้อมูลตาม:</div>",
      unsafe_allow_html=True,
  )
  sort_choice = st.radio(
      "Sort Order Choices",
      ["รหัสสาขา (Shop Code)", "ชื่อสาขา (Shop Name)"],
      index=0,
      horizontal=True,
      label_visibility="collapsed",
      key=f"sort_choice_{selected_brand}",
  )

with col_info_show:
  st.markdown(
      "<div style='font-size:0.85rem; font-weight:600; color:#1e293b;"
      " margin-top:5px;'>🗄️ Database Source:</div>",
      unsafe_allow_html=True,
  )
  st.code(
      f"Supabase Table: file_status [Brand: {selected_brand}]", language="text"
  )

# 📥 ดึงข้อมูลจาก Supabase
full_df = get_data_from_supabase(selected_brand, y, m)

# กรองตัดร้านที่รหัสขึ้นต้นด้วย EAT ออกหากเป็นแบรนด์ Laem Charoen Seafood
if selected_brand == "Laem Charoen Seafood" and not full_df.empty:
  if "shop_code" in full_df.columns:
    full_df = full_df[
        ~full_df["shop_code"].astype(str).str.startswith("EAT")
    ]
  elif "shop_id" in full_df.columns:
    full_df = full_df[~full_df["shop_id"].astype(str).str.startswith("EAT")]

if not full_df.empty:
  id_col = (
      "shop_id"
      if "shop_id" in full_df.columns
      else ("shop_code" if "shop_code" in full_df.columns else "")
  )

  if id_col:
    full_df["final_shop_code"] = (
        full_df[id_col]
        .astype(str)
        .replace(["0", "0.0", "nan", "None", "<NA>"], "")
    )
  else:
    full_df["final_shop_code"] = ""

  valid_codes = full_df[full_df["final_shop_code"] != ""].drop_duplicates(
      "shop_name"
  )
  name_to_code_map = dict(
      zip(valid_codes["shop_name"], valid_codes["final_shop_code"])
  )

  def make_label(shop_name):
    code = name_to_code_map.get(shop_name, "")
    return f"[{code}] {shop_name}" if code else f"[0] {shop_name}"

  shops = sorted([
      str(s).strip()
      for s in full_df["shop_name"].unique()
      if s and str(s).strip() != "nan"
  ])

  shops_display_dict = {s: make_label(s) for s in shops}
  brand_settings = current_full_config.get(selected_brand, {})

  def get_sort_key(shop_name):
    if "รหัสสาขา" in sort_choice:
      code = name_to_code_map.get(shop_name, "")
      return (0, code) if code else (1, shop_name)
    else:
      return (0, shop_name)

  shops = sorted(shops, key=get_sort_key)

  # Sidebar Expander จัดการ เปิด/ปิดร้าน
  with st.sidebar:
    st.markdown("---")
    with st.expander("🚫 จัดการ เปิด/ปิด / ดึงยอด สาขา", expanded=False):
      search_query = (
          st_keyup("🔍 ค้นหาสาขา...", key=f"keyup_search_{selected_brand}")
          .strip()
          .lower()
      )

      updated_settings = {}
      for s in shops:
        old_val = brand_settings.get(s, True)
        if isinstance(old_val, dict):
          updated_settings[s] = {
              "active": old_val.get("active", True),
              "sync_active": old_val.get("sync_active", True),
          }
        else:
          updated_settings[s] = {"active": old_val, "sync_active": old_val}

      master_act_key = f"master_act_{selected_brand}"
      master_sync_key = f"master_sync_{selected_brand}"

      def on_master_act_change():
        for s in shops:
          st.session_state[f"tog_act_{selected_brand}_{s}"] = st.session_state[
              master_act_key
          ]

      def on_master_sync_change():
        for s in shops:
          st.session_state[f"tog_sync_{selected_brand}_{s}"] = (
              st.session_state[master_sync_key]
          )

      all_act_on = all(
          st.session_state.get(
              f"tog_act_{selected_brand}_{s}", updated_settings[s]["active"]
          )
          for s in shops
      )
      all_sync_on = all(
          st.session_state.get(
              f"tog_sync_{selected_brand}_{s}",
              updated_settings[s]["sync_active"],
          )
          for s in shops
      )

      col_m_name, col_m_act, col_m_sync = st.columns([1.8, 1.1, 1.1])
      col_m_name.markdown(
          "<div style='font-size: 0.75rem; font-weight: bold; color: #1e293b;"
          " padding-top: 4px;'>🔔 เปิด/ปิด ทั้งหมด</div>",
          unsafe_allow_html=True,
      )
      col_m_act.toggle(
          "All Act",
          value=all_act_on,
          key=master_act_key,
          on_change=on_master_act_change,
          label_visibility="collapsed",
      )
      col_m_sync.toggle(
          "All Sync",
          value=all_sync_on,
          key=master_sync_key,
          on_change=on_master_sync_change,
          label_visibility="collapsed",
      )

      st.markdown(
          "<hr style='margin: 8px 0; border: none; border-top: 1px dashed"
          " #cbd5e1;'>",
          unsafe_allow_html=True,
      )
      st.markdown(
          """
                <div style="display: flex; background-color: #f1f5f9; padding: 6px 4px; border-radius: 6px; margin-bottom: 8px; font-size: 0.75rem; font-weight: bold; color: #475569;">
                    <div style="flex: 1.8;">📍 รหัส & ชื่อสาขา</div>
                    <div style="flex: 1.1; text-align: center;">เปิด-ปิดร้าน</div>
                    <div style="flex: 1.1; text-align: center;">เปิด-ปิดส่งยอด</div>
                </div>
            """,
          unsafe_allow_html=True,
      )

      filtered_shops = (
          [
              s
              for s in shops
              if search_query in shops_display_dict.get(s, s).lower()
          ]
          if search_query
          else shops
      )

      for shop in filtered_shops:
        display_shop_name = (
            shops_display_dict.get(shop, shop).replace("--", "").strip()
        )
        col_name, col_act, col_sync = st.columns([1.8, 1.1, 1.1])

        col_name.markdown(
            f"<div style='font-size: 0.8rem; font-weight: 500; padding-top:"
            f" 2px; color: #1e293b;'>{display_shop_name}</div>",
            unsafe_allow_html=True,
        )

        t_active_key = f"tog_act_{selected_brand}_{shop}"
        if t_active_key not in st.session_state:
          st.session_state[t_active_key] = updated_settings[shop]["active"]
        val_active = col_act.toggle(
            "Active", key=t_active_key, label_visibility="collapsed"
        )

        t_sync_key = f"tog_sync_{selected_brand}_{shop}"
        if t_sync_key not in st.session_state:
          st.session_state[t_sync_key] = updated_settings[shop]["sync_active"]
        val_sync = col_sync.toggle(
            "Sync", key=t_sync_key, label_visibility="collapsed"
        )

        updated_settings[shop] = {
            "active": val_active,
            "sync_active": val_sync,
        }
        st.markdown(
            "<div style='margin: 4px 0; border-bottom: 1px solid"
            " #f1f5f9;'></div>",
            unsafe_allow_html=True,
        )

      if st.button(
          "💾 บันทึกการตั้งค่าสาขา",
          type="primary",
          use_container_width=True,
          key="save_shops",
      ):
        final_settings = {}
        for s in shops:
          final_settings[s] = {
              "active": st.session_state.get(
                  f"tog_act_{selected_brand}_{s}",
                  updated_settings[s]["active"],
              ),
              "sync_active": st.session_state.get(
                  f"tog_sync_{selected_brand}_{s}",
                  updated_settings[s]["sync_active"],
              ),
          }
        current_full_config[selected_brand] = final_settings
        save_config(current_full_config)
        st.success("บันทึกเรียบร้อย!")
        st.rerun()

    if st.button(
        "🔙 Back to Main Page", key="back_to_welcome", use_container_width=True
    ):
      st.session_state.selected_brand = "🛑 SELECT BRAND 🛑"
      st.rerun()

  # Grid โครงสร้างตาราง Heatmap
  _, last_day = calendar.monthrange(y, m)
  days = list(range(1, last_day + 1))

  grid_index_labels = [shops_display_dict[s] for s in shops]
  grid_df = pd.DataFrame("N/A", index=grid_index_labels, columns=days)

  if not full_df.empty:
    full_df["Day"] = full_df["sync_date"].dt.day
    for shop in shops:
      s_cfg = brand_settings.get(shop, True)
      is_active = (
          s_cfg.get("active", True) if isinstance(s_cfg, dict) else s_cfg
      )
      if not is_active:
        grid_df.loc[shops_display_dict[shop]] = "DISABLED"

    for _, row in full_df.iterrows():
      s, d = row["shop_name"], row["Day"]
      if s in shops_display_dict:
        display_label = shops_display_dict[s]
        st_code = (
            row.get("status_realtime", row.get("status_code", 0))
            if "⚡ Real-time" in view_mode
            else row.get("status_log", row.get("status_code", 0))
        )

        if (
            display_label in grid_df.index
            and grid_df.at[display_label, d] != "DISABLED"
        ):
          grid_df.at[display_label, d] = (
              "✅"
              if st_code == 2
              else "⚠️" if st_code == 1 else "❌" if st_code == 0 else "N/A"
          )

  active_shops = [
      s
      for s in shops
      if (
          brand_settings.get(s, True).get("active", True)
          if isinstance(brand_settings.get(s, True), dict)
          else brand_settings.get(s, True)
      )
  ]
  active_grid_labels = [
      shops_display_dict[s] for s in active_shops if s in shops_display_dict
  ]
  active_grid = (
      grid_df.loc[active_grid_labels] if active_shops else pd.DataFrame()
  )

  # สรุปผลสถิติ
  with summary_placeholder.container():
    monitor_info = monitors_config.get(selected_brand, {})
    m1_n, m2_n = monitor_info.get("m1", ""), monitor_info.get("m2", "")
    if m1_n or m2_n:
      parts = [
          f"มือ{i+1}: <b>{p}</b>"
          for i, p in enumerate([x for x in [m1_n, m2_n] if x])
      ]
      st.markdown(
          '<div style="font-size:0.75rem; color:#555;'
          f' margin-bottom:4px;">👤 Monitor: {" | ".join(parts)}</div>',
          unsafe_allow_html=True,
      )

    st.info(f"Monitor: **{len(active_shops)}** / **{len(shops)}** สาขา")
    if not active_grid.empty:
      prob_count = active_grid.isin(["⚠️", "❌"]).any(axis=1).sum()
      col1, col2 = st.columns(2)
      col1.metric("ปกติ ✅", len(active_shops) - prob_count)
      col2.metric("ปัญหา ⚠️/❌", prob_count)

      prob_sum = (active_grid == "❌").sum(axis=1) + (
          active_grid == "⚠️"
      ).sum(axis=1)
      top_prob = prob_sum[prob_sum > 0].sort_values(ascending=False).head(3)
      if not top_prob.empty:
        st.markdown("---")
        st.write("**⚠️ สาขาที่พบปัญหาบ่อยเดือนนี้:**")
        for shop_label, count in top_prob.items():
          st.markdown(
              f'<div class="problem-item"><b>{shop_label}</b><br><span'
              ' style="color:#d32f2f; font-size:0.75rem;">พบปัญหา'
              f" {int(count)} ครั้ง</span></div>",
              unsafe_allow_html=True,
          )

  def apply_style(val):
    if val == "✅":
      return "background-color: #d4edda; color: #155724;"
    if val == "⚠️":
      return "background-color: #fff3cd; color: #856404;"
    if val == "❌":
      return "background-color: #f8d7da; color: #721c24;"
    if val == "DISABLED":
      return "background-color: #6c757d; color: transparent;"
    return "color: #ced4da; font-size: 10px;"

  st.dataframe(
      grid_df.style.map(apply_style),
      use_container_width=True,
      height=800,
      column_config={
          d: st.column_config.Column(width=35) for d in days
      },
  )
else:
  st.warning("⚠️ ไม่พบข้อมูลสำหรับแบรนด์นี้ในฐานข้อมูล Supabase")