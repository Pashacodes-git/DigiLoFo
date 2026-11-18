import base64
import os
import streamlit as st

from database import (
    initialize_database,
    register_student,
    verify_login,
    create_student_session,
    verify_student_session,
    delete_student_session,
    add_item,
    get_items,
    get_open_found_items,
    get_dashboard_stats,
    get_campus_hotspots,
    update_item_status,
    add_claim,
    get_claims,
    get_user_claims,
    update_claim_status,
    verify_and_handover_item,
    find_possible_matches,
)

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="DigiLoFo | Woxsen University",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

initialize_database()

# --------------------------------------------------
# Woxsen Campus Background & Crisp Glassmorphism
# --------------------------------------------------
bg_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png")
if os.path.exists(bg_file_path):
    with open(bg_file_path, "rb") as f:
        bg_base64 = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bg_base64}");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-color: #080E18;
        }}
        /* Clean Spacious Frosted Glass Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: rgba(12, 22, 36, 0.88) !important;
            border: 1px solid rgba(8, 126, 139, 0.3) !important;
            border-radius: 14px !important;
            backdrop-filter: blur(12px) !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45) !important;
            padding: 10px !important;
        }}
        /* Crisp High-Contrast Typography */
        p, span, label, div {{
            color: #F1F5F9 !important;
        }}
        h1, h2, h3, h4 {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }}
        /* Form Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {{
            background-color: #0A1322 !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
        }}
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------
# Session State & Student Auto-Login
# --------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    session_token = st.query_params.get("session")
    if session_token:
        resumed_student = verify_student_session(session_token)
        if resumed_student:
            st.session_state.user = resumed_student
        else:
            if "session" in st.query_params:
                del st.query_params["session"]

if "current_page" not in st.session_state:
    st.session_state.current_page = "Overview"

if "report_preselect_type" not in st.session_state:
    st.session_state.report_preselect_type = "Lost Item"

if "just_reported_item_id" not in st.session_state:
    st.session_state.just_reported_item_id = None


def set_page(page_name, report_type=None):
    st.session_state.current_page = page_name
    if report_type:
        st.session_state.report_preselect_type = report_type


def process_uploaded_image(file_obj, max_size=(800, 800)):
    """
    Optimizes and compresses an uploaded image to keep database size efficient.
    Returns bytes or None.
    """
    if file_obj is None:
        return None
    try:
        from PIL import Image
        import io
        img = Image.open(file_obj)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82, optimize=True)
        return buf.getvalue()
    except Exception:
        try:
            return file_obj.getvalue()
        except Exception:
            return None


# --------------------------------------------------
# Authentication Screen (Logged Out)
# --------------------------------------------------
if st.session_state.user is None:
    left_col, right_col = st.columns([1.1, 1], gap="large")

    with left_col:
        st.caption("WOXSEN UNIVERSITY · CAMPUS PORTAL")
        st.title("🔎 DigiLoFo")
        st.subheader("Helping campus belongings find their way back.")
        st.write(
            "DigiLoFo is the central digital platform for Woxsen University "
            "students and staff to report lost personal items, share found belongings, "
            "and track claims securely within our campus community."
        )

        with st.container(border=True):
            st.markdown("### :blue-background[🏛️ Campus Security & Trust]")
            st.markdown(
                "- **Domain Verified:** Exclusively accessible to students with `@woxsen.edu.in` accounts.\n"
                "- **Zero-Trust Pickup PIN:** Physical custody handover requires a 4-digit code generated upon claim approval.\n"
                "- **Privacy Shield:** Personal contact numbers and claim identifiers are kept private.\n"
                "- **Admin Verified:** Belongings are officially vetted by campus authorities before status closure."
            )

        st.caption("Developed by Team Table Flippers · Woxsen University ELP Project")

    with right_col:
        with st.container(border=True):
            auth_tabs = st.tabs(["🔐 Sign In", "📝 Create Student Account"])

            # Sign In
            with auth_tabs[0]:
                st.subheader("Sign in to DigiLoFo")
                st.caption("Use your university credentials to access the portal.")

                with st.form("signin_form"):
                    signin_email = st.text_input(
                        "Woxsen Email",
                        placeholder="yourname@woxsen.edu.in",
                    )
                    signin_password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="••••••••••••",
                    )
                    signin_submitted = st.form_submit_button(
                        "Sign In",
                        type="primary",
                        use_container_width=True,
                    )

                if signin_submitted:
                    clean_in_email = signin_email.strip().lower()
                    if not clean_in_email or not signin_password:
                        st.error("Please enter both your email and password.")
                    elif "@" not in clean_in_email:
                        st.error("Please enter a valid email address.")
                    else:
                        logged_in_user = verify_login(clean_in_email, signin_password)
                        if logged_in_user:
                            st.session_state.user = logged_in_user
                            st.session_state.current_page = "Overview"

                            if logged_in_user["role"] == "student":
                                token = create_student_session(logged_in_user["id"])
                                st.query_params["session"] = token
                            else:
                                if "session" in st.query_params:
                                    del st.query_params["session"]

                            st.rerun()
                        else:
                            st.error("Invalid email or password.")

            # Create Student Account
            with auth_tabs[1]:
                st.subheader("Register as Student")
                st.caption("Student accounts require a valid @woxsen.edu.in email address.")

                with st.form("signup_form"):
                    reg_name = st.text_input(
                        "Full Name",
                        placeholder="e.g. Rahul Sharma",
                    )
                    reg_email = st.text_input(
                        "Woxsen Email",
                        placeholder="e.g. rahul.sharma@woxsen.edu.in",
                    )
                    reg_password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Minimum 10 characters",
                    )
                    reg_password_confirm = st.text_input(
                        "Confirm Password",
                        type="password",
                        placeholder="Re-type password",
                    )
                    reg_submitted = st.form_submit_button(
                        "Create Student Account",
                        type="primary",
                        use_container_width=True,
                    )

                if reg_submitted:
                    clean_name = reg_name.strip()
                    clean_email = reg_email.strip().lower()

                    if not clean_name or not clean_email or not reg_password:
                        st.error("Please complete all required fields.")
                    elif len(clean_name) > 100:
                        st.error("Full name must be 100 characters or fewer.")
                    elif not clean_email.endswith("@woxsen.edu.in") or "@" not in clean_email or clean_email.startswith("@"):
                        st.error("Student registration requires an email ending in @woxsen.edu.in.")
                    elif len(reg_password) < 10:
                        st.error("Password must be at least 10 characters long.")
                    elif len(reg_password) > 128:
                        st.error("Password cannot exceed 128 characters.")
                    elif reg_password != reg_password_confirm:
                        st.error("Passwords do not match.")
                    else:
                        success, message = register_student(
                            clean_name,
                            clean_email,
                            reg_password,
                        )
                        if success:
                            st.success("Account created successfully! You can now Sign In.")
                        else:
                            st.error(message)

        st.info("ℹ️ Student accounts cannot choose admin privileges. Admin accounts are pre-configured.")
    st.stop()


# --------------------------------------------------
# Top Spacious Navigation Header (Clean & Uncongested)
# --------------------------------------------------
user = st.session_state.user
is_admin = user.get("role") == "admin"
current_user_role = user.get("role", "student")

# Top Header Card
with st.container(border=True):
    col_brand, col_nav, col_user = st.columns([1.6, 5.0, 1.4], vertical_alignment="center")

    with col_brand:
        st.markdown("## 🔎 **DigiLoFo**")
        st.caption("WOXSEN UNIVERSITY · ELP")

    with col_nav:
        nav_options = [
            "🏠 Overview",
            "📢 Report Item",
            "🔎 Browse Items",
            "🤝 Claim / Track",
            "✨ Matches",
            "📍 Campus Hubs",
        ]
        if is_admin:
            nav_options.append("⚙️ Admin Suite")

        # Map display labels to internal page keys
        label_to_key = {
            "🏠 Overview": "Overview",
            "📢 Report Item": "Report Item",
            "🔎 Browse Items": "Browse Items",
            "🤝 Claim / Track": "Claim Item",
            "✨ Matches": "Possible Matches",
            "📍 Campus Hubs": "Campus Hubs",
            "⚙️ Admin Suite": "Admin",
        }
        key_to_label = {v: k for k, v in label_to_key.items()}

        current_label = key_to_label.get(st.session_state.current_page, "🏠 Overview")

        chosen_label = st.segmented_control(
            "Navigation Menu",
            options=nav_options,
            default=current_label,
            label_visibility="collapsed",
            key="top_navbar_segmented",
        )

        if chosen_label and label_to_key[chosen_label] != st.session_state.current_page:
            st.session_state.current_page = label_to_key[chosen_label]
            st.rerun()

    with col_user:
        u_info, u_logout = st.columns([1.8, 1.2], vertical_alignment="center")
        with u_info:
            role_badge = ":blue-background[🛡️ Admin]" if is_admin else ":green-background[🎓 Student]"
            st.markdown(f"**{user['name'].split()[0]}** {role_badge}")
        with u_logout:
            if st.button("Logout", key="top_logout_btn", use_container_width=True):
                token = st.query_params.get("session")
                if token:
                    delete_student_session(token)
                    del st.query_params["session"]
                st.session_state.user = None
                st.session_state.current_page = "Overview"
                st.rerun()

st.write("")

# --------------------------------------------------
# Screen 1: Dashboard / Overview
# --------------------------------------------------
if st.session_state.current_page == "Overview":
    with st.container(border=True):
        st.caption("WOXSEN UNIVERSITY · DIGITAL LOST & FOUND")
        st.title("A little help goes a long way.")
        st.write(
            "One centralized campus platform to report lost belongings, share found items, "
            "and securely coordinate handover with one-time verification PINs."
        )

    st.write("")

    # Live Metric Cards
    stats = get_dashboard_stats()
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        with st.container(border=True):
            st.caption("📊 TOTAL REPORTS")
            st.header(f"{stats['total']}")
            st.caption("All-time logged")
    with m2:
        with st.container(border=True):
            st.caption("⏳ OPEN REPORTS")
            st.header(f"{stats['open']}")
            st.caption("Pending recovery")
    with m3:
        with st.container(border=True):
            st.caption("🔴 LOST ITEMS")
            st.header(f"{stats['lost']}")
            st.caption("Currently missing")
    with m4:
        with st.container(border=True):
            st.caption("🟢 FOUND ITEMS")
            st.header(f"{stats['found']}")
            st.caption("In custody")
    with m5:
        with st.container(border=True):
            st.caption("🎯 RECOVERY RATE")
            st.header(f"{stats['recovery_rate']}%")
            st.caption(f"{stats['recovered']} items returned")

    st.write("")

    # Quick Actions
    st.subheader("⚡ Quick Actions")
    act_col1, act_col2 = st.columns(2)

    with act_col1:
        with st.container(border=True):
            st.markdown("### 📢 Lost Something?")
            st.write(
                "Create a lost-item report with a detailed description and the last known location."
            )
            st.write("")
            if st.button("Report a Lost Item →", type="primary", use_container_width=True, key="quick_btn_lost"):
                set_page("Report Item", "Lost Item")
                st.rerun()

    with act_col2:
        with st.container(border=True):
            st.markdown("### 🤝 Found Something?")
            st.write(
                "Report a found item so its rightful owner has a better chance of recovering it."
            )
            st.write("")
            if st.button("Report a Found Item →", type="secondary", use_container_width=True, key="quick_btn_found"):
                set_page("Report Item", "Found Item")
                st.rerun()

    st.write("")
    st.divider()

    # Recent Reports Section
    rec_head, rec_action = st.columns([4, 1])
    with rec_head:
        st.subheader("🕒 Recent Campus Reports")
    with rec_action:
        if st.button("View All Items →", key="view_all_items_btn", use_container_width=True):
            st.session_state.current_page = "Browse Items"
            st.rerun()

    all_items = get_items()

    if not all_items:
        with st.container(border=True):
            st.info("📦 No items have been reported yet. Reports will appear here once submitted.")
    else:
        recent_items = all_items[:4]
        for item in recent_items:
            with st.container(border=True):
                c_title, c_badge = st.columns([4, 1])
                with c_title:
                    st.subheader(f"{item[2]} · #{item[0]}")
                    st.caption(f"📂 **{item[3]}**  •  📍 **{item[5]}**  •  📅 **{item[6]}**")
                with c_badge:
                    if item[1] == "LOST":
                        st.markdown(":red-background[**LOST**]")
                    else:
                        st.markdown(":green-background[**FOUND**]")

                    if item[7] == "Open":
                        st.caption("Status: :orange[**Open**]")
                    else:
                        st.caption("Status: :green[**Recovered**]")

                has_img = len(item) > 9 and item[9] is not None
                if has_img:
                    img_c, desc_c = st.columns([1, 4])
                    with img_c:
                        st.image(item[9], use_container_width=True)
                    with desc_c:
                        st.write(item[4])
                else:
                    st.write(item[4])


# --------------------------------------------------
# Screen 2: Report Item
# --------------------------------------------------
elif st.session_state.current_page == "Report Item":
    st.caption("CAMPUS REPORTING")
    st.title("📢 Create an Item Report")
    st.write("Add enough detail to help someone recognise the item.")

    with st.container(border=True):
        default_index = 0 if st.session_state.report_preselect_type == "Lost Item" else 1

        with st.form("create_report_form"):
            report_type_choice = st.radio(
                "Report Type",
                ["Lost Item", "Found Item"],
                index=default_index,
                horizontal=True,
            )

            col_name, col_cat = st.columns(2)
            with col_name:
                item_name = st.text_input(
                    "Item Name",
                    placeholder="e.g. Black water bottle, Blue Umbrella, Casio Calculator",
                )
            with col_cat:
                category = st.selectbox(
                    "Category",
                    [
                        "Electronics",
                        "ID Card",
                        "Books & Stationery",
                        "Clothing",
                        "Bags",
                        "Keys",
                        "Accessories",
                        "Other",
                    ],
                )

            item_desc = st.text_area(
                "Description",
                placeholder="Include color, brand, distinctive stickers, scratches, or identifying features.",
                help="Do not include passwords, banking info, or government ID numbers.",
            )

            col_loc, col_date = st.columns(2)
            with col_loc:
                item_loc = st.selectbox(
                    "Primary Campus Location",
                    [
                        "Vithal Gandhi Library",
                        "Rise Cafe",
                        "Race",
                        "Blu Embers",
                        "SOAD",
                        "SOB",
                        "SOL",
                        "Admin Block and New Block",
                        "Block A",
                        "Block B",
                        "All Tower area",
                        "Ink And Water",
                        "SportX",
                        "Oval",
                        "Others",
                    ],
                )
            with col_date:
                item_date = st.date_input("Date Lost or Found")

            uploaded_photo = st.file_uploader(
                "Upload Item Photo (Optional)",
                type=["png", "jpg", "jpeg", "webp"],
                help="A clear photo significantly improves the chances of matching and verifying the item.",
            )

            st.write("")
            submit_report = st.form_submit_button(
                "Submit Report",
                type="primary",
                use_container_width=True,
            )

        if submit_report:
            clean_item_name = item_name.strip()
            clean_item_desc = item_desc.strip()
            clean_item_loc = item_loc.strip()

            if not clean_item_name:
                st.error("Please enter the item name.")
            elif len(clean_item_name) > 100:
                st.error("Item name must be 100 characters or fewer.")
            elif not clean_item_desc:
                st.error("Please provide a description.")
            elif len(clean_item_desc) > 1000:
                st.error("Description must be 1000 characters or fewer.")
            elif not clean_item_loc:
                st.error("Please provide the campus location.")
            else:
                db_type = "LOST" if report_type_choice == "Lost Item" else "FOUND"
                img_bytes = process_uploaded_image(uploaded_photo)
                new_item_id = add_item(
                    report_type=db_type,
                    title=clean_item_name,
                    category=category,
                    description=clean_item_desc,
                    location=clean_item_loc,
                    date_lost_found=str(item_date),
                    image_data=img_bytes,
                )
                st.session_state.just_reported_item_id = new_item_id
                st.success(f"Your {report_type_choice} has been logged as Report #{new_item_id}!")

    if st.session_state.just_reported_item_id:
        instant_matches = find_possible_matches(item_id=st.session_state.just_reported_item_id)
        if instant_matches:
            with st.container(border=True):
                st.markdown("### ⚡ **Instant Match Alert!**")
                st.write(
                    "Our rule-based engine immediately detected possible counterpart reports "
                    "already logged on campus for this item:"
                )
                for im in instant_matches:
                    st.info(
                        f"🎯 **Potential Counterpart Found!**\n\n"
                        f"• Lost Item: **{im['lost_title']}** at {im['lost_location']}\n\n"
                        f"• Found Item: **{im['found_title']}** at {im['found_location']}\n\n"
                        f"• Match Confidence Score: **{im['score']} pts**"
                    )
                if st.button("View Full Matches in Detail →", key="btn_go_matches"):
                    st.session_state.current_page = "Possible Matches"
                    st.rerun()


# --------------------------------------------------
# Screen 3: Browse Items
# --------------------------------------------------
elif st.session_state.current_page == "Browse Items":
    st.caption("CAMPUS DIRECTORY")
    st.title("🔎 Explore Reported Items")
    st.write("Search campus reports and narrow the results with filters.")

    all_items = get_items()

    with st.container(border=True):
        search_col, type_col, stat_col = st.columns([2, 1, 1])
        with search_col:
            search_query = st.text_input(
                "Search",
                placeholder="Try a name, category, description, or location",
                key="browse_query_input",
            )
        with type_col:
            type_filter = st.selectbox(
                "Report Type",
                ["All", "Lost Items", "Found Items"],
                key="browse_type_select",
            )
        with stat_col:
            status_filter = st.selectbox(
                "Status",
                ["All", "Open", "Recovered"],
                key="browse_status_select",
            )

    filtered = []
    for item in all_items:
        i_id, i_type, i_title, i_cat, i_desc, i_loc, i_date, i_stat = item[:8]
        combined_text = f"{i_title} {i_desc} {i_loc} {i_cat}".lower()

        matches_search = search_query.strip().lower() in combined_text
        matches_type = (
            type_filter == "All"
            or (type_filter == "Lost Items" and i_type == "LOST")
            or (type_filter == "Found Items" and i_type == "FOUND")
        )
        matches_status = status_filter == "All" or i_stat == status_filter

        if matches_search and matches_type and matches_status:
            filtered.append(item)

    st.write("")

    if not all_items:
        with st.container(border=True):
            st.info("📦 No items have been reported yet.")
    elif not filtered:
        with st.container(border=True):
            st.warning("🔍 No reports match those filters. Try clearing your search keywords.")
    else:
        st.caption(f"Showing **{len(filtered)}** campus report(s)")
        for item in filtered:
            with st.container(border=True):
                head_col, status_col = st.columns([4, 1])
                with head_col:
                    st.subheader(f"{item[2]} · #{item[0]}")
                    st.caption(f"📂 **{item[3]}**  •  📍 **{item[5]}**  •  📅 **{item[6]}**")
                with status_col:
                    if item[1] == "LOST":
                        st.markdown(":red-background[**LOST**]")
                    else:
                        st.markdown(":green-background[**FOUND**]")

                    if item[7] == "Open":
                        st.caption("Status: :orange[**Open**]")
                    else:
                        st.caption("Status: :green[**Recovered**]")

                has_img = len(item) > 9 and item[9] is not None
                if has_img:
                    img_c, desc_c = st.columns([1, 4])
                    with img_c:
                        st.image(item[9], use_container_width=True)
                    with desc_c:
                        st.write(item[4])
                else:
                    st.write(item[4])


# --------------------------------------------------
# Screen 4: Claim Item & Track Claims
# --------------------------------------------------
elif st.session_state.current_page == "Claim Item":
    st.caption("RECOVERY VERIFICATION & ZERO-TRUST HANDOVER")
    st.title("🤝 Claim Found Belongings & Track Status")
    st.write(
        "Submit a claim for an item found on campus. Once approved by the administrator, "
        "a secure **4-digit Pickup PIN** will be issued to physically retrieve your item."
    )

    claim_tabs = st.tabs(["📝 Submit New Claim", "🔐 My Active Claims & Pickup PINs"])

    # Tab 1: Submit New Claim
    with claim_tabs[0]:
        open_found = get_open_found_items()

        if not open_found:
            with st.container(border=True):
                st.info("📦 There are no open found-item reports available to claim right now.")
        else:
            item_options = {
                f"#{item[0]} — {item[2]} ({item[3]} at {item[5]})": item[0]
                for item in open_found
            }

            with st.container(border=True):
                with st.form("submit_claim_form"):
                    selected_label = st.selectbox(
                        "Found Item",
                        list(item_options.keys()),
                        help="Select the found item you want to claim.",
                    )
                    claimant_contact = st.text_input(
                        "Contact Details",
                        placeholder="Phone number or hostel room number",
                    )
                    claim_reason = st.text_area(
                        "How Can You Identify This Item?",
                        placeholder="Share distinguishing details (e.g. stickers, lock screen photo, brand markings, contents inside).",
                        help="Share distinguishing details. Do not include passwords or sensitive ID numbers.",
                    )
                    st.write("")
                    submit_claim = st.form_submit_button(
                        "Submit Claim for Review",
                        type="primary",
                        use_container_width=True,
                    )

                if submit_claim:
                    clean_contact = claimant_contact.strip()
                    clean_reason = claim_reason.strip()

                    if not clean_contact:
                        st.error("Please provide your contact details.")
                    elif len(clean_contact) > 100:
                        st.error("Contact details must be 100 characters or fewer.")
                    elif not clean_reason:
                        st.error("Please explain how you can identify this item.")
                    elif len(clean_reason) > 1000:
                        st.error("Explanation must be 1000 characters or fewer.")
                    else:
                        selected_item_id = item_options[selected_label]
                        add_claim(
                            item_id=selected_item_id,
                            claimant_name=user["name"],
                            claimant_contact=clean_contact,
                            claim_reason=clean_reason,
                            claimant_email=user["email"],
                        )
                        st.success("✅ Claim submitted! Track your approval and Pickup PIN in the next tab.")
                        st.rerun()

    # Tab 2: Track Claims & View Secure Pickup PIN
    with claim_tabs[1]:
        my_claims = get_user_claims(user["email"])
        if not my_claims:
            with st.container(border=True):
                st.info("You haven't submitted any claims yet.")
        else:
            st.caption(f"Showing {len(my_claims)} claim(s) associated with {user['email']}")
            for clm in my_claims:
                c_id, itm_id, itm_title, itm_loc, c_status, c_pin, c_date = clm
                with st.container(border=True):
                    col_det, col_pin = st.columns([2.5, 1.5], vertical_alignment="center")
                    with col_det:
                        st.subheader(f"Claim #{c_id} for '{itm_title}'")
                        st.caption(f"Item #{itm_id}  •  📍 Custody Hub: {itm_loc}  •  📅 Submitted: {c_date}")

                        if c_status == "Pending":
                            st.markdown("Status: :orange-background[**⏳ Under Admin Review**]")
                            st.caption("An administrator is reviewing your identification evidence.")
                        elif c_status == "Approved":
                            st.markdown("Status: :green-background[**✅ Approved — Ready for Pickup**]")
                            st.caption("Show the Pickup PIN on the right to the Custody Desk to claim your item.")
                        elif c_status == "Handed Over":
                            st.markdown("Status: :blue-background[**🎉 Handed Over & Closed**]")
                            st.caption("Physical custody verified and complete.")
                        else:
                            st.markdown("Status: :red-background[**❌ Rejected**]")
                            st.caption("Insufficient proof of ownership.")

                    with col_pin:
                        if c_status == "Approved" and c_pin:
                            with st.container(border=True):
                                st.caption("🔐 PHYSICAL PICKUP PIN")
                                st.header(f"`{c_pin}`")
                                st.caption("Show this code to Campus Security")
                        elif c_status == "Handed Over":
                            st.success("Item Recovered ✓")


# --------------------------------------------------
# Screen 5: Possible Matches
# --------------------------------------------------
elif st.session_state.current_page == "Possible Matches":
    st.caption("DETERMINISTIC HEURISTIC ENGINE")
    st.title("✨ Rule-Based Possible Matches")
    st.write(
        "DigiLoFo compares open lost and found reports using weighted factor analysis: "
        "Category (+2), Location substring proximity (+2), and Common descriptive keyword overlap (+1 to +5). "
        "These are suggestions, not confirmed matches."
    )

    matches = find_possible_matches()

    if not matches:
        with st.container(border=True):
            st.info("💡 No possible matches found yet. New reports may trigger suggestions.")
    else:
        st.caption(f"**{len(matches)}** potential match suggestion(s) discovered.")
        for match in matches:
            with st.container(border=True):
                st.subheader("💡 Potential Match Pair")
                lost_c, found_c = st.columns(2)

                with lost_c:
                    with st.container(border=True):
                        st.markdown(":red-background[**LOST REPORT**]")
                        st.markdown(f"**#{match['lost_id']} — {match['lost_title']}**")
                        st.caption(f"📂 {match['lost_category']}  •  📍 {match['lost_location']}")
                        if match.get("lost_image"):
                            st.image(match["lost_image"], caption="Lost Item Photo", use_container_width=True)

                with found_c:
                    with st.container(border=True):
                        st.markdown(":green-background[**FOUND REPORT**]")
                        st.markdown(f"**#{match['found_id']} — {match['found_title']}**")
                        st.caption(f"📂 {match['found_category']}  •  📍 {match['found_location']}")
                        if match.get("found_image"):
                            st.image(match["found_image"], caption="Found Item Photo", use_container_width=True)

                st.write(f"📊 **Rule-based composite match score:** :blue-background[**{match['score']} pts**] (Threshold: 3 pts)")
                st.warning("⚠️ Physical ownership must be verified via Claim PIN before release.")


# --------------------------------------------------
# Screen 6: Campus Drop-off Hubs & Analytics
# --------------------------------------------------
elif st.session_state.current_page == "Campus Hubs":
    st.caption("CAMPUS INFRASTRUCTURE & ANALYTICS")
    st.title("📍 Campus Custody Hubs & Hotspots")
    st.write(
        "Physical drop-off points where found belongings are held securely, "
        "along with real-time reporting trends across Woxsen University."
    )

    hub_col, chart_col = st.columns([1.2, 1], gap="large")

    with hub_col:
        st.subheader("🏛️ Official Drop-off & Custody Desks")
        st.write("Found an item? Drop it off at any of these designated campus locations:")

        hubs = [
            ("Central Library Reception Desk", "Ground Floor, Vithal Gandhi Building", "Mon-Sat: 08:30 - 21:00", "Books, Electronics, Stationery"),
            ("Campus Security Main Gate 1", "Main Campus Entrance", "24 / 7 Operations", "ID Cards, Keys, Wallets"),
            ("Student Affairs Helpdesk", "Admin Building Block B", "Mon-Fri: 09:00 - 17:30", "Valuables, Smart Watches, Laptops"),
            ("Cafeteria Manager Counter", "Central Dining Hall 1", "07:30 - 22:30", "Water Bottles, Umbrellas, Lunchboxes"),
        ]

        for h_name, h_loc, h_hrs, h_items in hubs:
            with st.container(border=True):
                st.markdown(f"**{h_name}**")
                st.caption(f"📍 Location: {h_loc}\n\n🕒 Timings: {h_hrs}\n\n📦 Typical Items: {h_items}")

    with chart_col:
        st.subheader("📊 Campus Incident Hotspots")
        hotspots = get_campus_hotspots()

        st.caption("Most Frequent Lost & Found Locations:")
        for loc, cnt in hotspots["locations"]:
            st.write(f"• **{loc}**: `{cnt} reports`")

        st.divider()

        st.caption("Reports Breakdown by Category:")
        for cat, cnt in hotspots["categories"]:
            st.write(f"• **{cat}**: `{cnt} items`")


# --------------------------------------------------
# Screen 7: Administrator Dashboard (Admin Only)
# --------------------------------------------------
elif st.session_state.current_page == "Admin":
    if not is_admin:
        st.error("Unauthorized access. Administrator privileges required.")
        st.stop()

    st.caption("CAMPUS POLICE & ADMINISTRATION")
    st.title("⚙️ Administrator Control Center")
    st.write("Manage report statuses, review ownership claims, and verify physical pickup PINs.")

    admin_tabs = st.tabs(["🛡️ Pending Claims", "🔐 PIN Handover Verification", "🔄 Item Status", "📋 All Claims Audit"])

    # Admin Tab 1: Pending Claims Review
    with admin_tabs[0]:
        st.subheader("Pending Claims Review")
        st.caption("Review student claims for found items before approving pickup codes.")

        try:
            claims = get_claims(current_user_role=current_user_role)
        except PermissionError:
            st.error("Permission denied: Unable to access claims.")
            claims = []

        pending_claims = [c for c in claims if c[6] == "Pending"]

        if not pending_claims:
            with st.container(border=True):
                st.info("✨ You're all caught up. No pending claims awaiting review.")
        else:
            for claim in pending_claims:
                with st.container(border=True):
                    c_id, itm_id, itm_title, c_name, c_contact, c_reason, c_status, c_pin, c_email, c_date = claim

                    st.subheader(f"Claim #{c_id} for '{itm_title}' (Item #{itm_id})")
                    c_info1, c_info2 = st.columns(2)
                    with c_info1:
                        st.write(f"**Claimant:** {c_name} ({c_email})")
                        st.write(f"**Contact:** {c_contact}")
                    with c_info2:
                        st.write(f"**Submitted:** {c_date}")
                        st.write(f"**Status:** :orange[**{c_status}**]")

                    st.markdown("**Identification Details:**")
                    st.info(c_reason)

                    btn_app, btn_rej = st.columns(2)
                    with btn_app:
                        if st.button("✅ Approve Claim & Issue PIN", key=f"app_{c_id}", type="primary", use_container_width=True):
                            try:
                                generated_pin = update_claim_status(c_id, "Approved", current_user_role=current_user_role)
                                st.success(f"Claim #{c_id} approved! Pickup PIN {generated_pin} generated for student.")
                                st.rerun()
                            except PermissionError:
                                st.error("Permission denied: Administrator role required.")
                    with btn_rej:
                        if st.button("❌ Reject Claim", key=f"rej_{c_id}", type="secondary", use_container_width=True):
                            try:
                                update_claim_status(c_id, "Rejected", current_user_role=current_user_role)
                                st.warning(f"Claim #{c_id} rejected.")
                                st.rerun()
                            except PermissionError:
                                st.error("Permission denied: Administrator role required.")

    # Admin Tab 2: Zero-Trust PIN Handover Verification
    with admin_tabs[1]:
        st.subheader("🔐 In-Person Pickup PIN Handover")
        st.caption("When a student arrives at the Custody Desk to claim their item, enter their PIN here to complete handover.")

        try:
            claims = get_claims(current_user_role=current_user_role)
            approved_claims = [c for c in claims if c[6] == "Approved"]
        except PermissionError:
            approved_claims = []

        if not approved_claims:
            with st.container(border=True):
                st.info("No approved claims currently awaiting physical pickup.")
        else:
            claim_dict = {
                f"Claim #{c[0]} — {c[2]} (Claimant: {c[3]})": c[0]
                for c in approved_claims
            }

            with st.container(border=True):
                chosen_claim_str = st.selectbox("Select Awaiting Claim", list(claim_dict.keys()))
                chosen_claim_id = claim_dict[chosen_claim_str]

                pin_input = st.text_input("Enter Student's 4-Digit Pickup PIN", max_chars=4, placeholder="e.g. 4821")

                if st.button("Verify PIN & Finalize Handover", type="primary", key="btn_verify_handover"):
                    if not pin_input.strip():
                        st.error("Please enter the 4-digit PIN.")
                    else:
                        success, message = verify_and_handover_item(
                            chosen_claim_id, pin_input.strip(), current_user_role=current_user_role
                        )
                        if success:
                            st.success(f"🎉 {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

    # Admin Tab 3: Item Status Management
    with admin_tabs[2]:
        st.subheader("Update Item Status")
        st.caption("Select any campus report to view or modify its operational status.")

        all_items = get_items()
        if not all_items:
            with st.container(border=True):
                st.info("No items reported yet.")
        else:
            item_map = {
                f"#{i[0]} — {i[2]} ({i[1]}) | Current: {i[7]}": (i[0], i[7])
                for i in all_items
            }

            with st.container(border=True):
                selected_report_label = st.selectbox(
                    "Select Report",
                    list(item_map.keys()),
                    key="admin_item_selector",
                )

                selected_id, current_status = item_map[selected_report_label]
                st.write(f"Current Status: **{current_status}**")

                new_status = st.selectbox(
                    "Set Status",
                    ["Open", "Recovered"],
                    index=0 if current_status == "Open" else 1,
                    key="admin_status_choice",
                )

                if st.button("Save Status", type="primary", key="admin_save_status_btn"):
                    if new_status == current_status:
                        st.info("The item already has this status.")
                    else:
                        try:
                            update_item_status(selected_id, new_status, current_user_role=current_user_role)
                            st.success(f"Report #{selected_id} updated to {new_status}.")
                            st.rerun()
                        except PermissionError:
                            st.error("Permission denied: You do not have administrator rights.")

    # Admin Tab 4: All Claims Audit
    with admin_tabs[3]:
        st.subheader("Claim History & Handover Audit")
        st.caption("Complete tamper-evident audit record of all submitted claims.")

        try:
            claims = get_claims(current_user_role=current_user_role)
        except PermissionError:
            claims = []

        if not claims:
            with st.container(border=True):
                st.info("No claims have been submitted.")
        else:
            for claim in claims:
                with st.container(border=True):
                    c_id, itm_id, itm_title, c_name, c_contact, c_reason, c_status, c_pin, c_email, c_date = claim
                    h_left, h_right = st.columns([3, 1])
                    with h_left:
                        st.markdown(f"**Claim #{c_id}** — Item: **{itm_title}** (#{itm_id})")
                        st.caption(f"Claimant: {c_name} ({c_email}) • Contact: {c_contact} • Date: {c_date}")
                        st.write(f"**Reason:** {c_reason}")
                        if c_pin:
                            st.caption(f"Issued PIN: `{c_pin}`")
                    with h_right:
                        if c_status == "Approved":
                            st.markdown(":green-background[**APPROVED**]")
                        elif c_status == "Handed Over":
                            st.markdown(":blue-background[**HANDED OVER**]")
                        elif c_status == "Rejected":
                            st.markdown(":red-background[**REJECTED**]")
                        else:
                            st.markdown(":orange-background[**PENDING**]")
