import streamlit as st
import pandas as pd
from database_manager import DatabaseManager
from auth_manager import AuthManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term
import os
from datetime import datetime
import uuid
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Product & Quotation Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'auth_manager' not in st.session_state:
    st.session_state.auth_manager = None

def init_database():
    """Initialize the database if it doesn't exist."""
    return DatabaseManager()

def init_auth():
    """Initialize the authentication manager."""
    return AuthManager()

def check_authentication():
    """Check if user is authenticated and return user info."""
    if not st.session_state.authenticated or not st.session_state.user_info:
        return None
    return st.session_state.user_info

def login_page():
    """Display login page."""
    st.title("🔐 Login")
    
    if st.session_state.auth_manager is None:
        st.session_state.auth_manager = init_auth()
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("Please login to continue")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            login_button = st.form_submit_button("Login", type="primary", use_container_width=True)
            
            if login_button:
                if username and password:
                    success, user_info = st.session_state.auth_manager.authenticate(username, password)
                    if success:
                        # Create session
                        session_token = st.session_state.auth_manager.create_session(username)
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_info
                        st.session_state.session_token = session_token
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")

def logout():
    """Handle user logout."""
    if 'session_token' in st.session_state:
        st.session_state.auth_manager.logout(st.session_state.session_token)
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user_info = None
    if 'session_token' in st.session_state:
        del st.session_state.session_token
    st.rerun()

def admin_panel():
    """Admin panel for user management."""
    st.header("👨‍💼 Admin Panel")
    
    if st.session_state.user_info['role'] != 'admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    tab1, tab2 = st.tabs(["👥 User Management", "📊 System Stats"])
    
    with tab1:
        # Create new user
        st.subheader("Create New User")
        with st.form("create_user_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_username = st.text_input("Username")
            with col2:
                new_password = st.text_input("Password", type="password")
            with col3:
                new_role = st.selectbox("Role", ["user", "admin"])
            
            create_button = st.form_submit_button("Create User", type="primary")
            
            if create_button:
                if new_username and new_password:
                    success, message = st.session_state.auth_manager.create_user(
                        new_username, new_password, new_role, st.session_state.user_info['username']
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please fill in all fields")
        
        st.divider()
        
        # List existing users
        st.subheader("Existing Users")
        users = st.session_state.auth_manager.get_all_users()
        
        if users:
            for user in users:
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{user['username']}**")
                with col2:
                    st.write(user['role'])
                with col3:
                    status = "Active" if user['is_active'] else "Inactive"
                    st.write(status)
                with col4:
                    if user['username'] != st.session_state.user_info['username']:
                        if st.button("Toggle Status", key=f"toggle_{user['username']}"):
                            success, message = st.session_state.auth_manager.update_user_status(
                                user['username'], not user['is_active']
                            )
                            if success:
                                st.rerun()
                            else:
                                st.error(message)
                with col5:
                    if user['username'] != st.session_state.user_info['username']:
                        if st.button("Delete", key=f"delete_{user['username']}", type="secondary"):
                            success, message = st.session_state.auth_manager.delete_user(user['username'])
                            if success:
                                st.rerun()
                            else:
                                st.error(message)
                
                st.divider()
    
    with tab2:
        # System statistics
        st.subheader("System Statistics")
        
        db = init_database()
        total_products = db.get_total_records()
        quotations = db.get_quotations()
        total_quotations = len(quotations) if not quotations.empty else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Products", total_products)
        with col2:
            st.metric("Total Quotations", total_quotations)
        with col3:
            st.metric("Total Users", len(users) if users else 0)

def main():
    # Check authentication
    user_info = check_authentication()
    
    if not user_info:
        login_page()
        return
    
    # Sidebar with user info and logout
    with st.sidebar:
        st.header(f"Welcome, {user_info['username']}!")
        st.write(f"Role: {user_info['role'].title()}")
        
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            logout()
        
        st.divider()
        
        # Navigation
        if user_info['role'] == 'admin':
            if st.button("👨‍💼 Admin Panel", use_container_width=True):
                st.session_state.show_admin = True
        
        st.divider()
        
        # Quick stats
        db = init_database()
        total_records = db.get_total_records()
        st.metric("Total Products", total_records)
    
    # Check if admin panel should be shown
    if user_info['role'] == 'admin' and st.session_state.get('show_admin', False):
        admin_panel()
        if st.button("← Back to Main App"):
            st.session_state.show_admin = False
            st.rerun()
        return
    
    # Main application
    st.title("📊 Product & Quotation Management System")
    st.markdown("*Manage your product database and generate professional quotations*")
    
    # Initialize database
    db = init_database()
    
    # Create tabs
    if user_info['role'] == 'admin':
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📂 Data Management", "🔍 Search & Filter", "➕ Add Products", 
            "✏️ Edit Products", "📋 Create Quotation", "⬇️ Download Quotations"
        ])
    else:
        tab1, tab2, tab4, tab5, tab6 = st.tabs([
            "📂 Data Management", "🔍 Search & Filter", 
            "📋 Create Quotation", "📋 View Quotations", "⬇️ Download Quotations"
        ])
    
    with tab1:
        st.header("📂 Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 Import Data")
            uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx', 'xls'])
            
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    # Validate structure
                    is_valid, message = validate_excel_structure(df)
                    
                    if is_valid:
                        st.success("✅ File structure is valid!")
                        st.write("**Preview:**")
                        st.dataframe(df.head(), use_container_width=True)
                        
                        if st.button("Import Data", type="primary"):
                            success, import_message = db.import_data(df)
                            if success:
                                st.success(f"✅ {import_message}")
                                st.rerun()
                            else:
                                st.error(f"❌ {import_message}")
                    else:
                        st.error(f"❌ {message}")
                        
                except Exception as e:
                    st.error(f"❌ Error reading file: {str(e)}")
        
        with col2:
            st.subheader("📊 Database Overview")
            
            total_records = db.get_total_records()
            st.metric("Total Records", total_records)
            
            if total_records > 0:
                st.subheader("📥 Export Options")
                
                # Get all data for export
                all_data = db.get_all_data()
                if not all_data.empty:
                    formatted_data = format_dataframe_display(all_data)
                    
                    # Export to Excel
                    excel_data = export_to_excel(formatted_data)
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name=f"product_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                if user_info['role'] == 'admin':
                    st.divider()
                    st.subheader("⚠️ Danger Zone")
                    if st.button("🗑️ Clear All Data", type="secondary"):
                        if 'confirm_clear' not in st.session_state:
                            st.session_state.confirm_clear = True
                        else:
                            db.clear_database()
                            st.session_state.confirm_clear = False
                            st.success("✅ Database cleared successfully!")
                            st.rerun()
                    
                    if st.session_state.get('confirm_clear', False):
                        st.warning("⚠️ Are you sure? This action cannot be undone!")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes, Clear All", type="primary"):
                                db.clear_database()
                                st.session_state.confirm_clear = False
                                st.success("✅ Database cleared successfully!")
                                st.rerun()
                        with col_no:
                            if st.button("Cancel"):
                                st.session_state.confirm_clear = False
                                st.rerun()
    
    with tab2:
        st.header("🔍 Search & Filter Products")
        
        # Search controls
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_term = st.text_input("🔍 Search products", placeholder="Enter model, color, or any keyword...")
        
        with col2:
            st.write("") # Spacing
            search_button = st.button("Search", type="primary")
        
        # Advanced filters
        with st.expander("🔧 Advanced Filters"):
            col1, col2, col3 = st.columns(3)
            
            # Get unique values for filters
            all_data = db.get_all_data()
            
            if not all_data.empty:
                with col1:
                    colors = ["All"] + sorted(all_data['BODY CLOLOR'].dropna().unique().tolist())
                    selected_color = st.selectbox("Body Color", colors)
                
                with col2:
                    sizes = ["All"] + sorted(all_data['SIZE'].dropna().unique().tolist())
                    selected_size = st.selectbox("Size", sizes)
                
                with col3:
                    watts = ["All"] + sorted(all_data['WATT'].dropna().unique().tolist())
                    selected_watt = st.selectbox("Wattage", watts)
        
        # Perform search
        if search_term or search_button:
            filters = {}
            
            # Apply advanced filters
            if 'selected_color' in locals() and selected_color != "All":
                filters['BODY CLOLOR'] = selected_color
            if 'selected_size' in locals() and selected_size != "All":
                filters['SIZE'] = selected_size
            if 'selected_watt' in locals() and selected_watt != "All":
                filters['WATT'] = selected_watt
            
            # Search with filters
            results = db.search_data(search_term, filters)
            
            if not results.empty:
                st.success(f"✅ Found {len(results)} products")
                
                # Display results
                formatted_results = format_dataframe_display(results)
                st.dataframe(formatted_results, use_container_width=True)
                
                # Export search results
                if len(results) > 0:
                    excel_data = export_to_excel(formatted_results)
                    st.download_button(
                        label="📥 Download Search Results",
                        data=excel_data,
                        file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("🔍 No products found matching your criteria")
        else:
            # Show all data when no search
            all_data = db.get_all_data()
            if not all_data.empty:
                st.info(f"📊 Showing all {len(all_data)} products")
                formatted_data = format_dataframe_display(all_data)
                st.dataframe(formatted_data, use_container_width=True)
    
    if user_info['role'] == 'admin':
        with tab3:
            st.header("➕ Add New Products")
            
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    add_sno = st.text_input("S.NO", key="add_sno")
                    add_model = st.text_input("Model *", key="add_model")
                    add_body_color = st.text_input("Body Color *", key="add_body_color")
                    
                    # Picture upload
                    uploaded_picture = st.file_uploader("Upload Product Picture", type=['jpg', 'png', 'gif'], key="add_picture_upload")
                    add_picture = st.text_input("Or enter picture filename", key="add_picture")
                    
                    add_price = st.number_input("Price *", min_value=0.0, step=0.01, key="add_price")
                
                with col2:
                    add_watt = st.text_input("Watt", key="add_watt")
                    add_size = st.text_input("Size", key="add_size")
                    add_beam_angle = st.text_input("Beam Angle", key="add_beam_angle")
                    add_cut_out = st.text_input("Cut Out", key="add_cut_out")
                    add_light_color = st.text_input("Light Color", key="add_light_color")
                
                submit_button = st.form_submit_button("Add Product", type="primary")
                
                if submit_button:
                    # Handle picture upload
                    picture_filename = add_picture
                    if uploaded_picture is not None:
                        # Create uploaded_images directory if it doesn't exist
                        os.makedirs("uploaded_images", exist_ok=True)
                        
                        # Save uploaded file
                        picture_filename = uploaded_picture.name
                        file_path = os.path.join("uploaded_images", picture_filename)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_picture.getbuffer())
                        st.success(f"Picture uploaded: {picture_filename}")
                    
                    if add_model and add_body_color:
                        # Create new product data
                        new_product = {
                            'S.NO': add_sno,
                            'MODEL': add_model,
                            'BODY CLOLOR': add_body_color,
                            'PICTURE': picture_filename,
                            'PRICE': add_price,
                            'WATT': add_watt,
                            'SIZE': add_size,
                            'BEAM ANGLE': add_beam_angle,
                            'CUT OUT': add_cut_out,
                            'LIGHT COLOR': add_light_color
                        }
                        
                        # Convert to DataFrame and import
                        new_df = pd.DataFrame([new_product])
                        success, message = db.import_data(new_df)
                        
                        if success:
                            st.success(f"✅ Product added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add product: {message}")
                    else:
                        st.error("Please fill in at least Model and Body Color")
        
        with tab4:
            st.header("✏️ Edit Products")
            
            all_products = db.get_all_data()
            
            if not all_products.empty:
                st.subheader("Search and Select Product to Edit")
                
                # Search bar for filtering products
                search_filter = st.text_input(
                    "Search products by model, color, or price", 
                    placeholder="Type to filter products...",
                    key="edit_search"
                )
                
                # Filter products based on search
                filtered_products = all_products
                if search_filter:
                    search_lower = search_filter.lower()
                    filtered_products = all_products[
                        all_products['MODEL'].astype(str).str.lower().str.contains(search_lower, na=False) |
                        all_products['BODY CLOLOR'].astype(str).str.lower().str.contains(search_lower, na=False) |
                        all_products['PRICE'].astype(str).str.contains(search_lower, na=False)
                    ]
                
                if not filtered_products.empty:
                    # Create a product selector from filtered results
                    product_options = []
                    for idx, row in filtered_products.iterrows():
                        model = row.get('MODEL', 'Unknown')
                        color = row.get('BODY CLOLOR', 'Unknown')
                        price = row.get('PRICE', 'Unknown')
                        product_options.append(f"{model} - {color} (₹{price})")
                    
                    selected_product_str = st.selectbox("Select product to edit:", product_options)
                else:
                    st.info("No products found matching your search criteria.")
                    selected_product_str = None
                
                if selected_product_str:
                    # Find the selected product
                    selected_model = selected_product_str.split(' - ')[0]
                    selected_product = None
                    selected_index = None
                    
                    for idx, row in filtered_products.iterrows():
                        if row.get('MODEL', '') == selected_model:
                            selected_product = row
                            selected_index = idx
                            break
                    
                    if selected_product is not None:
                        # Display current product image if exists
                        current_picture = str(selected_product.get('PICTURE', ''))
                        if current_picture and current_picture != 'nan' and current_picture != '':
                            import os
                            image_path = os.path.join("uploaded_images", current_picture)
                            if os.path.exists(image_path):
                                st.subheader("Current Product Image")
                                col1, col2, col3 = st.columns([1, 2, 1])
                                with col2:
                                    st.image(image_path, caption=f"Current image: {current_picture}", width=300)
                            else:
                                st.info(f"Image file not found: {current_picture}")
                        else:
                            st.info("No image associated with this product")
                        
                        with st.form("edit_product_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edit_sno = st.text_input("S.NO", value=str(selected_product.get('S.NO', '')), key="edit_sno")
                                edit_model = st.text_input("Model *", value=str(selected_product.get('MODEL', '')), key="edit_model")
                                edit_body_color = st.text_input("Body Color *", value=str(selected_product.get('BODY CLOLOR', '')), key="edit_body_color")
                                
                                # Picture upload for editing
                                uploaded_picture = st.file_uploader("Upload New Picture", type=['jpg', 'png', 'gif'], key="edit_picture_upload")
                                edit_picture = st.text_input("Or edit picture filename", value=str(selected_product.get('PICTURE', '')), key="edit_picture")
                                
                                edit_price = st.number_input("Price *", min_value=0.0, step=0.01, value=float(selected_product.get('PRICE', 0)), key="edit_price")
                            
                            with col2:
                                edit_watt = st.text_input("Watt", value=str(selected_product.get('WATT', '')), key="edit_watt")
                                edit_size = st.text_input("Size", value=str(selected_product.get('SIZE', '')), key="edit_size")
                                edit_beam_angle = st.text_input("Beam Angle", value=str(selected_product.get('BEAM ANGLE', '')), key="edit_beam_angle")
                                edit_cut_out = st.text_input("Cut Out", value=str(selected_product.get('CUT OUT', '')), key="edit_cut_out")
                                edit_light_color = st.text_input("Light Color", value=str(selected_product.get('LIGHT COLOR', '')), key="edit_light_color")
                            
                            col_update, col_delete = st.columns(2)
                            
                            with col_update:
                                update_button = st.form_submit_button("Update Product", type="primary")
                            
                            with col_delete:
                                delete_button = st.form_submit_button("Delete Product", type="secondary")
                            
                            if update_button:
                                # Handle picture upload for editing
                                picture_filename = edit_picture
                                if uploaded_picture is not None:
                                    # Create uploaded_images directory if it doesn't exist
                                    os.makedirs("uploaded_images", exist_ok=True)
                                    
                                    # Save uploaded file
                                    picture_filename = uploaded_picture.name
                                    file_path = os.path.join("uploaded_images", picture_filename)
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_picture.getbuffer())
                                    st.success(f"New picture uploaded: {picture_filename}")
                                
                                # Update the product data
                                all_products.loc[selected_index, 'S.NO'] = edit_sno
                                all_products.loc[selected_index, 'MODEL'] = edit_model
                                all_products.loc[selected_index, 'BODY CLOLOR'] = edit_body_color
                                all_products.loc[selected_index, 'PICTURE'] = picture_filename
                                all_products.loc[selected_index, 'PRICE'] = edit_price
                                all_products.loc[selected_index, 'WATT'] = edit_watt
                                all_products.loc[selected_index, 'SIZE'] = edit_size
                                all_products.loc[selected_index, 'BEAM ANGLE'] = edit_beam_angle
                                all_products.loc[selected_index, 'CUT OUT'] = edit_cut_out
                                all_products.loc[selected_index, 'LIGHT COLOR'] = edit_light_color
                                
                                # Clear and re-import data
                                db.clear_database()
                                success, message = db.import_data(all_products)
                                
                                if success:
                                    st.success("✅ Product updated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to update product: {message}")
                            
                            if delete_button:
                                # Remove the product
                                all_products = all_products.drop(selected_index).reset_index(drop=True)
                                
                                # Clear and re-import data
                                db.clear_database()
                                success, message = db.import_data(all_products)
                                
                                if success:
                                    st.success("✅ Product deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to delete product: {message}")
            else:
                st.info("No products available to edit. Please import some data first.")
    
    if user_info['role'] == 'admin':
        quotation_tab = tab5
    else:
        quotation_tab = tab4
    
    with quotation_tab:
        st.header("📋 Create Quotation")
        
        # Quotation form
        with st.form("quotation_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                customer_name = st.text_input("Customer Name *", key="customer_name")
                quotation_date = st.date_input("Quotation Date", value=datetime.now().date(), key="quotation_date")
            
            with col2:
                quotation_id = st.text_input("Quotation ID", value=f"QT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}", key="quotation_id")
                
            st.subheader("Add Products to Quotation")
            
            # Get available products
            all_products = db.get_all_data()
            
            if not all_products.empty:
                # Initialize quotation items in session state
                if 'quotation_items' not in st.session_state:
                    st.session_state.quotation_items = []
                
                # Product selection
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    product_options = []
                    for idx, row in all_products.iterrows():
                        model = row.get('MODEL', 'Unknown')
                        color = row.get('BODY CLOLOR', 'Unknown')
                        price = row.get('PRICE', 0)
                        product_options.append(f"{model} - {color} (₹{price})")
                    
                    selected_product = st.selectbox("Select Product", product_options, key="product_select")
                
                with col2:
                    quantity = st.number_input("Quantity", min_value=1, value=1, key="quantity")
                
                with col3:
                    discount = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="discount")
                
                with col4:
                    light_color = st.text_input("Light Color", key="light_color")
                
                with col5:
                    add_item_button = st.form_submit_button("Add Item", type="secondary")
                
                if add_item_button and selected_product:
                    # Find selected product details
                    selected_model = selected_product.split(' - ')[0]
                    
                    for idx, row in all_products.iterrows():
                        if row.get('MODEL', '') == selected_model:
                            # Calculate pricing
                            original_price = float(row.get('PRICE', 0))
                            discount_amount = original_price * (discount / 100)
                            unit_price_after_discount = original_price - discount_amount
                            item_total = unit_price_after_discount * quantity
                            
                            item = {
                                'model': row.get('MODEL', ''),
                                'body_color': row.get('BODY CLOLOR', ''),
                                'picture': row.get('PICTURE', ''),
                                'price': original_price,
                                'watt': row.get('WATT', ''),
                                'size': row.get('SIZE', ''),
                                'beam_angle': row.get('BEAM ANGLE', ''),
                                'cut_out': row.get('CUT OUT', ''),
                                'light_color': light_color,
                                'quantity': quantity,
                                'discount': discount,
                                'unit_price': unit_price_after_discount,
                                'item_total': item_total
                            }
                            
                            st.session_state.quotation_items.append(item)
                            break
                
                # Display current quotation items
                if st.session_state.quotation_items:
                    st.subheader("Quotation Items")
                    
                    total_amount = 0
                    discount_total = 0
                    
                    for i, item in enumerate(st.session_state.quotation_items):
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                            
                            with col1:
                                st.write(f"**{item['model']}** - {item['body_color']}")
                                if item['light_color']:
                                    st.write(f"Light Color: {item['light_color']}")
                            
                            with col2:
                                st.write(f"Qty: {item['quantity']}")
                                st.write(f"₹{item['price']:.2f}")
                            
                            with col3:
                                st.write(f"Discount: {item['discount']:.1f}%")
                                st.write(f"Unit: ₹{item['unit_price']:.2f}")
                            
                            with col4:
                                st.write(f"**Total: ₹{item['item_total']:.2f}**")
                            
                            with col5:
                                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                                    st.session_state.quotation_items.pop(i)
                                    st.rerun()
                            
                            st.divider()
                        
                        total_amount += item['item_total']
                        discount_total += (item['price'] * item['quantity']) - item['item_total']
                    
                    # Final totals
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Amount", f"₹{total_amount:.2f}")
                    with col2:
                        st.metric("Total Discount", f"₹{discount_total:.2f}")
                    with col3:
                        final_amount = total_amount
                        st.metric("Final Amount", f"₹{final_amount:.2f}")
                
                # Save quotation
                save_button = st.form_submit_button("Save Quotation", type="primary")
                
                if save_button:
                    if customer_name and st.session_state.quotation_items:
                        # Calculate totals
                        total_amount = sum(item['item_total'] for item in st.session_state.quotation_items)
                        discount_total = sum((item['price'] * item['quantity']) - item['item_total'] for item in st.session_state.quotation_items)
                        final_amount = total_amount
                        
                        # Save quotation
                        success, message = db.save_quotation(
                            quotation_id, customer_name, st.session_state.quotation_items,
                            total_amount, discount_total, final_amount
                        )
                        
                        if success:
                            st.success(f"✅ Quotation saved successfully! ID: {quotation_id}")
                            st.session_state.quotation_items = []  # Clear items
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to save quotation: {message}")
                    else:
                        st.error("Please enter customer name and add at least one item")
            else:
                st.info("No products available. Please import product data first.")
        
        # Clear items button
        if st.session_state.get('quotation_items', []):
            if st.button("Clear All Items", type="secondary"):
                st.session_state.quotation_items = []
                st.rerun()
    
    if user_info['role'] == 'admin':
        view_tab = tab5
    else:
        view_tab = tab5
    
    # View Quotations tab (for users, this replaces the hidden tabs)
    if user_info['role'] != 'admin':
        with view_tab:
            st.header("📋 View Quotations")
            
            quotations = db.get_quotations()
            
            if not quotations.empty:
                st.subheader("Your Quotations")
                
                for _, quotation in quotations.iterrows():
                    with st.expander(f"📄 {quotation['quotation_id']} - {quotation['customer_name']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Customer:** {quotation['customer_name']}")
                            st.write(f"**Date:** {quotation.get('quotation_date', quotation.get('created_date', 'N/A'))}")
                        
                        with col2:
                            st.write(f"**Total Amount:** ₹{quotation['total_amount']:,.2f}")
                            st.write(f"**Final Amount:** ₹{quotation['final_amount']:,.2f}")
                        
                        # Get and display items
                        items = db.get_quotation_items(quotation['quotation_id'])
                        if not items.empty:
                            st.write("**Items:**")
                            formatted_items = format_dataframe_display(items)
                            st.dataframe(formatted_items, use_container_width=True)
            else:
                st.info("No quotations found.")
    
    # Download tab
    if user_info['role'] == 'admin':
        download_tab = tab6
    else:
        download_tab = tab6
    
    with download_tab:
        st.header("⬇️ Download Quotations")
        
        quotations = db.get_quotations()
        
        if not quotations.empty:
            st.subheader("Available Quotations")
            
            for _, quotation in quotations.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**{quotation['quotation_id']}**")
                        st.write(f"Customer: {quotation['customer_name']}")
                    
                    with col2:
                        st.write(f"Amount: ₹{quotation['final_amount']:.2f}")
                        st.write(f"Date: {quotation.get('quotation_date', quotation.get('created_date', 'N/A'))}")
                    
                    with col3:
                        # Get quotation items for export
                        items = db.get_quotation_items(quotation['quotation_id'])
                        
                        if not items.empty:
                            # Get quotation date and customer name
                            customer_name = quotation['customer_name']
                            quotation_date = quotation.get('quotation_date', quotation.get('created_date', ''))
                            
                            # Export to Excel with customer info
                            excel_data = export_to_excel(items, customer_name=customer_name, quotation_date=quotation_date)
                            st.download_button(
                                label="📥 Excel",
                                data=excel_data,
                                file_name=f"quotation_{quotation['quotation_id']}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"excel_{quotation['quotation_id']}"
                            )
                    
                    st.divider()
        else:
            st.info("No quotations available for download.")

if __name__ == "__main__":
    main()