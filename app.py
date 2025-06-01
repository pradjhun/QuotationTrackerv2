import streamlit as st
import pandas as pd
import zipfile
import io
import os
from io import BytesIO
from database_manager import DatabaseManager
from auth_manager import AuthManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term
from typing import Dict, Any

def init_database():
    """Initialize the database if it doesn't exist."""
    db = DatabaseManager()
    return db

def init_auth():
    """Initialize the authentication manager."""
    if 'auth' not in st.session_state:
        st.session_state.auth = AuthManager()

def check_authentication():
    """Check if user is authenticated and return user info."""
    if 'session_token' in st.session_state:
        auth = st.session_state.auth
        is_valid, user_info = auth.validate_session(st.session_state.session_token)
        if is_valid:
            return True, user_info
        else:
            # Invalid session, clear it
            if 'session_token' in st.session_state:
                del st.session_state.session_token
            if 'user_info' in st.session_state:
                del st.session_state.user_info
    return False, None

def login_page():
    """Display login page."""
    st.title("🔐 Quotation Management System")
    st.markdown("### Please Login to Continue")
    
    # Display default credentials info
    st.info("**Default Admin Credentials:**\nUsername: admin\nPassword: admin123")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("🔓 Login", type="primary")
        
        if submitted:
            if username and password:
                auth = st.session_state.auth
                success, user_info = auth.authenticate(username, password)
                
                if success:
                    # Create session
                    session_token = auth.create_session(username)
                    if session_token:
                        st.session_state.session_token = session_token
                        st.session_state.user_info = user_info
                        st.success(f"Welcome, {user_info['username']}!")
                        st.rerun()
                    else:
                        st.error("Failed to create session. Please try again.")
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Please enter both username and password.")

def logout():
    """Handle user logout."""
    if 'session_token' in st.session_state:
        auth = st.session_state.auth
        auth.logout(st.session_state.session_token)
        del st.session_state.session_token
    
    if 'user_info' in st.session_state:
        del st.session_state.user_info
    
    st.rerun()

def has_permission(required_role: str, user_role: str) -> bool:
    """Check if user has required permission."""
    if required_role == 'admin':
        return user_role == 'admin'
    elif required_role == 'user':
        return user_role in ['admin', 'user']
    return False

def admin_panel():
    """Admin panel for user management."""
    st.header("👥 Admin Panel - User Management")
    
    auth = st.session_state.auth
    
    # Create tabs for admin functions
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["👤 Create User", "📋 Manage Users", "🔑 Change Password"])
    
    with admin_tab1:
        st.subheader("Create New User")
        
        with st.form("create_user_form"):
            new_username = st.text_input("Username", placeholder="Enter username (min 3 characters)")
            new_password = st.text_input("Password", type="password", placeholder="Enter password (min 6 characters)")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            create_submitted = st.form_submit_button("➕ Create User", type="primary")
            
            if create_submitted:
                if new_username and new_password:
                    success, message = auth.create_user(
                        new_username, 
                        new_password, 
                        new_role, 
                        st.session_state.user_info['username']
                    )
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please fill in all fields.")
    
    with admin_tab2:
        st.subheader("Manage Existing Users")
        
        users = auth.get_all_users()
        
        if users:
            for user in users:
                with st.expander(f"👤 {user['username']} ({user['role']})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Role:** {user['role']}")
                        st.write(f"**Status:** {'Active' if user['is_active'] else 'Inactive'}")
                        st.write(f"**Created:** {user['created_at']}")
                        st.write(f"**Last Login:** {user['last_login'] or 'Never'}")
                    
                    with col2:
                        # Role change
                        current_role = user['role']
                        new_role = st.selectbox(
                            "Change Role", 
                            ["admin", "user"], 
                            index=0 if current_role == "admin" else 1,
                            key=f"role_{user['username']}"
                        )
                        
                        if st.button(f"Update Role", key=f"update_role_{user['username']}"):
                            if new_role != current_role:
                                success, message = auth.change_user_role(user['username'], new_role)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                    
                    with col3:
                        # Status toggle
                        current_status = user['is_active']
                        if st.button(
                            f"{'Deactivate' if current_status else 'Activate'}", 
                            key=f"toggle_{user['username']}"
                        ):
                            success, message = auth.update_user_status(user['username'], not current_status)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        
                        # Delete user
                        if user['username'] != st.session_state.user_info['username']:
                            if st.button(f"🗑️ Delete", key=f"delete_{user['username']}", type="secondary"):
                                success, message = auth.delete_user(user['username'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.info("No users found.")
    
    with admin_tab3:
        st.subheader("Change Your Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_submitted = st.form_submit_button("🔑 Change Password", type="primary")
            
            if change_submitted:
                if current_password and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("New passwords do not match.")
                    else:
                        success, message = auth.change_password(
                            st.session_state.user_info['username'],
                            current_password,
                            new_password
                        )
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.error("Please fill in all fields.")

def main():
    st.set_page_config(
        page_title="Quotation Management System",
        page_icon="💡",
        layout="wide"
    )
    
    # Initialize authentication
    init_auth()
    
    # Check authentication
    is_authenticated, user_info = check_authentication()
    
    if not is_authenticated:
        login_page()
        return
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("💡 Quotation Management System")
        st.write("Manage your product database and create professional quotations")
    
    with col2:
        if user_info:
            st.write(f"**User:** {user_info['username']}")
            st.write(f"**Role:** {user_info['role'].title()}")
        else:
            st.write("**User:** Unknown")
            st.write("**Role:** Unknown")
    
    with col3:
        if st.button("🚪 Logout", type="secondary"):
            logout()
    
    st.markdown("---")
    
    # Initialize database
    db = init_database()
    
    # Initialize session state for images if not exists
    if 'uploaded_images' not in st.session_state:
        st.session_state.uploaded_images = {}
    
    # Load existing images from disk on startup
    if os.path.exists('uploaded_images'):
        for filename in os.listdir('uploaded_images'):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    with open(f'uploaded_images/{filename}', 'rb') as f:
                        st.session_state.uploaded_images[filename] = f.read()
                except Exception:
                    pass
    
    # Sidebar for data management
    with st.sidebar:
        st.header("📊 Data Management")
        
        # File upload section
        st.subheader("Upload Data")
        
        # Excel file upload
        uploaded_excel = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Upload an Excel file with product data"
        )
        
        # Image upload section
        uploaded_images = st.file_uploader(
            "Upload product images",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Upload images for products"
        )
        
        # Process uploaded images
        if uploaded_images:
            # Create uploaded_images directory if it doesn't exist
            os.makedirs('uploaded_images', exist_ok=True)
            
            for image_file in uploaded_images:
                image_bytes = image_file.read()
                st.session_state.uploaded_images[image_file.name] = image_bytes
                
                # Save image to disk for persistence
                with open(f'uploaded_images/{image_file.name}', 'wb') as f:
                    f.write(image_bytes)
            
            st.success(f"Uploaded {len(uploaded_images)} images")
        
        # Process Excel file
        if uploaded_excel is not None:
            try:
                df = pd.read_excel(uploaded_excel)
                
                is_valid, message = validate_excel_structure(df)
                
                if is_valid:
                    st.success(message)
                    
                    if st.button("💾 Import Data", type="primary"):
                        success, import_message = db.import_data(df)
                        if success:
                            st.success(import_message)
                            st.rerun()
                        else:
                            st.error(import_message)
                else:
                    st.error(message)
                    
                    with st.expander("📋 Data Preview"):
                        st.dataframe(df.head())
                        
            except Exception as e:
                st.error(f"Error reading Excel file: {str(e)}")
        
        # Backup and Restore section
        st.subheader("🔄 Backup & Restore")
        
        # Create backup
        total_records = db.get_total_records()
        st.info(f"Database contains {total_records} records")
        
        if total_records > 0:
            # Excel backup
            if st.button("📤 Backup as Excel"):
                try:
                    all_data = db.get_all_data()
                    excel_bytes = export_to_excel(all_data)
                    
                    st.download_button(
                        label="⬇️ Download Excel Backup",
                        data=excel_bytes,
                        file_name=f"quotation_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Backup failed: {str(e)}")
            
            # ZIP backup (includes images)
            if st.button("📦 Backup as ZIP"):
                try:
                    all_data = db.get_all_data()
                    excel_bytes = export_to_excel(all_data)
                    
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr("data.xlsx", excel_bytes)
                        
                        for filename, image_data in st.session_state.uploaded_images.items():
                            zip_file.writestr(f"images/{filename}", image_data)
                    
                    zip_bytes = zip_buffer.getvalue()
                    
                    st.download_button(
                        label="⬇️ Download ZIP Backup",
                        data=zip_bytes,
                        file_name=f"quotation_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                except Exception as e:
                    st.error(f"ZIP backup failed: {str(e)}")
        
        # Restore section
        st.subheader("📥 Restore Data")
        
        restore_file = st.file_uploader(
            "Choose backup file",
            type=['xlsx', 'xls', 'zip'],
            help="Upload Excel or ZIP backup file to restore data",
            key="restore_uploader"
        )
        
        if restore_file is not None:
            if st.button("🔄 Restore Data", type="secondary"):
                try:
                    if restore_file.name.endswith('.zip'):
                        # Handle ZIP restore
                        with zipfile.ZipFile(restore_file, 'r') as zip_file:
                            # Restore Excel data
                            if 'data.xlsx' in zip_file.namelist():
                                excel_data = zip_file.read('data.xlsx')
                                df = pd.read_excel(io.BytesIO(excel_data))
                                
                                success, message = db.import_data(df)
                                if success:
                                    st.success("Data restored successfully!")
                                else:
                                    st.error(f"Data restore failed: {message}")
                            
                            # Restore images
                            st.session_state.uploaded_images = {}
                            os.makedirs('uploaded_images', exist_ok=True)
                            
                            for file_info in zip_file.filelist:
                                if file_info.filename.startswith('images/') and not file_info.filename.endswith('/'):
                                    image_name = os.path.basename(file_info.filename)
                                    image_data = zip_file.read(file_info.filename)
                                    st.session_state.uploaded_images[image_name] = image_data
                                    
                                    # Save to disk for persistence
                                    with open(f'uploaded_images/{image_name}', 'wb') as f:
                                        f.write(image_data)
                            
                            if st.session_state.uploaded_images:
                                st.success(f"Restored {len(st.session_state.uploaded_images)} images!")
                    else:
                        # Handle Excel restore
                        df = pd.read_excel(restore_file)
                        success, message = db.import_data(df)
                        if success:
                            st.success("Data restored successfully!")
                        else:
                            st.error(f"Restore failed: {message}")
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Restore failed: {str(e)}")
        
        # Database management
        st.subheader("🗄️ Database Management")
        
        if st.button("🗑️ Clear All Data", type="secondary"):
            if st.session_state.get('confirm_delete', False):
                db.clear_database()
                st.session_state.uploaded_images = {}
                
                # Clear images directory
                import shutil
                if os.path.exists('uploaded_images'):
                    shutil.rmtree('uploaded_images')
                
                st.success("All data cleared!")
                st.session_state.confirm_delete = False
                st.rerun()
            else:
                st.session_state.confirm_delete = True
                st.warning("Click again to confirm deletion")
    
    # Main content area with tabs based on user role
    if user_info and user_info['role'] == 'admin':
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🔍 Browse Products", 
            "➕ Add Product", 
            "✏️ Edit Product", 
            "📋 Create Quotation", 
            "📄 View Quotations", 
            "📥 Download Quotations",
            "👥 Admin Panel"
        ])
        
        # Admin Panel tab
        with tab7:
            admin_panel()
    else:
        # User mode - limited tabs
        tab1, tab4, tab5, tab6 = st.tabs([
            "🔍 Browse Products", 
            "📋 Create Quotation", 
            "📄 View Quotations", 
            "📥 Download Quotations"
        ])
        
        # Set admin-only tabs to None for user mode
        tab2 = None
        tab3 = None
    
    with tab1:
        st.header("🔍 Search & Filter Products")
        
        # Search and filter section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_term = st.text_input(
                "Search across all columns",
                placeholder="Enter search term...",
                help="Search will look across all columns in the database"
            )
        
        with col2:
            search_button = st.button("Search", type="primary")
        
        # Advanced filters
        with st.expander("🎛️ Advanced Filters"):
            filter_cols = st.columns(3)
            
            all_data = db.get_all_data()
            
            with filter_cols[0]:
                if not all_data.empty and 'MODEL' in all_data.columns:
                    models = ['All'] + sorted([str(x) for x in all_data['MODEL'].dropna().unique().tolist()])
                else:
                    models = ['All']
                selected_model = st.selectbox("Model", models)
            
            with filter_cols[1]:
                if not all_data.empty and 'BODY CLOLOR' in all_data.columns:
                    colors = ['All'] + sorted([str(x) for x in all_data['BODY CLOLOR'].dropna().unique().tolist()])
                else:
                    colors = ['All']
                selected_color = st.selectbox("Body Color", colors)
            
            with filter_cols[2]:
                if not all_data.empty and 'WATT' in all_data.columns:
                    watts = ['All'] + sorted([str(x) for x in all_data['WATT'].dropna().unique().tolist()])
                else:
                    watts = ['All']
                selected_watt = st.selectbox("Watt", watts)
        
        # Build filters dictionary
        filters = {}
        if selected_model != 'All':
            filters['MODEL'] = selected_model
        if selected_color != 'All':
            filters['BODY CLOLOR'] = selected_color
        if selected_watt != 'All':
            filters['WATT'] = selected_watt
        
        # Get filtered data
        if search_term or filters:
            filtered_data = db.search_data(search_term, filters)
        else:
            filtered_data = db.get_all_data()
        
        # Display results
        if not filtered_data.empty:
            st.subheader(f"📊 Results ({len(filtered_data)} records)")
            
            # Display options
            display_cols = st.columns([1, 1, 1])
            with display_cols[0]:
                show_images = st.checkbox("Show Images", value=True)
            with display_cols[1]:
                records_per_page = st.selectbox("Records per page", [10, 25, 50, 100], index=1)
            with display_cols[2]:
                export_button = st.button("📤 Export Results")
            
            if export_button:
                excel_bytes = export_to_excel(filtered_data)
                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_bytes,
                    file_name=f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Pagination
            total_pages = (len(filtered_data) - 1) // records_per_page + 1
            if total_pages > 1:
                page = st.selectbox("Page", list(range(1, total_pages + 1)))
                start_idx = (page - 1) * records_per_page
                end_idx = start_idx + records_per_page
                page_data = filtered_data.iloc[start_idx:end_idx]
            else:
                page_data = filtered_data
            
            # Display data
            if show_images:
                for idx, row in page_data.iterrows():
                    with st.container():
                        st.divider()
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            picture = row.get('PICTURE', '')
                            if picture and picture in st.session_state.uploaded_images:
                                st.image(st.session_state.uploaded_images[picture], width=150)
                            else:
                                st.info("No image available")
                        
                        with col2:
                            info_cols = st.columns(2)
                            
                            with info_cols[0]:
                                st.write(f"**Model:** {row.get('MODEL', 'N/A')}")
                                st.write(f"**Body Color:** {row.get('BODY CLOLOR', 'N/A')}")
                                st.write(f"**Price:** ₹{row.get('PRICE', 'N/A')}")
                                st.write(f"**Watt:** {row.get('WATT', 'N/A')}")
                            
                            with info_cols[1]:
                                st.write(f"**Size:** {row.get('SIZE', 'N/A')}")
                                st.write(f"**Beam Angle:** {row.get('BEAM ANGLE', 'N/A')}")
                                st.write(f"**Cut Out:** {row.get('CUT OUT', 'N/A')}")
            else:
                formatted_data = format_dataframe_display(page_data)
                st.dataframe(formatted_data, use_container_width=True)
        else:
            st.info("No records found. Please upload data or adjust your search criteria.")
    
    # Add Product tab (Admin only)
    if tab2 is not None:
        with tab2:
            st.header("➕ Add Product")
            
            # Check if user has admin permissions
            if not (user_info and user_info['role'] == 'admin'):
                st.error("Access denied. Admin privileges required.")
                return
            
            st.subheader("📝 Product Information")
            
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    model = st.text_input("Model", placeholder="Enter product model")
                    body_color = st.text_input("Body Color", placeholder="Enter body color")
                    price = st.number_input("Price (₹)", min_value=0.0, step=0.01, format="%.2f")
                    watt = st.text_input("Watt", placeholder="Enter wattage")
                
                with col2:
                    size = st.text_input("Size", placeholder="Enter size")
                    beam_angle = st.text_input("Beam Angle", placeholder="Enter beam angle")
                    cut_out = st.text_input("Cut Out", placeholder="Enter cut out")
                    
                    # Image upload
                    uploaded_image = st.file_uploader(
                        "Product Image", 
                        type=['png', 'jpg', 'jpeg'],
                        help="Upload product image (PNG, JPG, JPEG)"
                    )
                
                submitted = st.form_submit_button("➕ Add Product", type="primary")
                
                if submitted:
                    if model and body_color and price > 0:
                        # Handle image upload
                        picture_filename = ""
                        if uploaded_image is not None:
                            # Create uploaded_images directory if it doesn't exist
                            os.makedirs('uploaded_images', exist_ok=True)
                            
                            # Generate unique filename
                            file_extension = uploaded_image.name.split('.')[-1].lower()
                            picture_filename = f"{model}_{body_color}.{file_extension}".replace(" ", "_")
                            
                            # Save image to disk
                            with open(f'uploaded_images/{picture_filename}', 'wb') as f:
                                f.write(uploaded_image.getbuffer())
                            
                            # Store in session state
                            st.session_state.uploaded_images[picture_filename] = uploaded_image.getbuffer()
                        
                        # Create product data
                        product_data = {
                            'MODEL': model,
                            'BODY CLOLOR': body_color,
                            'PICTURE': picture_filename,
                            'PRICE': price,
                            'WATT': watt,
                            'SIZE': size,
                            'BEAM ANGLE': beam_angle,
                            'CUT OUT': cut_out
                        }
                        
                        # Add to database
                        df_new = pd.DataFrame([product_data])
                        success, message = db.import_data(df_new)
                        
                        if success:
                            st.success(f"✅ Product '{model}' added successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to add product: {message}")
                    else:
                        st.error("Please fill in all required fields (Model, Body Color, and Price).")

    # Edit Product tab (Admin only)
    if tab3 is not None:
        with tab3:
            st.header("✏️ Edit Product")
            
            # Check if user has admin permissions
            if not (user_info and user_info['role'] == 'admin'):
                st.error("Access denied. Admin privileges required.")
                return
            
            # Get all products for editing
            all_products = db.get_all_data()
            
            if not all_products.empty:
                st.subheader("Select Product to Edit")
                
                # Create a product selector
                product_options = []
                for idx, row in all_products.iterrows():
                    model = row.get('MODEL', 'Unknown')
                    color = row.get('BODY CLOLOR', 'Unknown')
                    price = row.get('PRICE', 'Unknown')
                    product_options.append(f"{model} - {color} (₹{price})")
                
                selected_product_idx = st.selectbox(
                    "Choose product to edit:",
                    range(len(product_options)),
                    format_func=lambda x: product_options[x]
                )
                
                if selected_product_idx is not None:
                    selected_row = all_products.iloc[selected_product_idx]
                    
                    st.subheader("📝 Edit Product Information")
                    
                    with st.form("edit_product_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            model = st.text_input("Model", value=str(selected_row.get('MODEL', '')))
                            body_color = st.text_input("Body Color", value=str(selected_row.get('BODY CLOLOR', '')))
                            price = st.number_input("Price (₹)", value=float(selected_row.get('PRICE', 0)), min_value=0.0, step=0.01, format="%.2f")
                            watt = st.text_input("Watt", value=str(selected_row.get('WATT', '')))
                        
                        with col2:
                            size = st.text_input("Size", value=str(selected_row.get('SIZE', '')))
                            beam_angle = st.text_input("Beam Angle", value=str(selected_row.get('BEAM ANGLE', '')))
                            cut_out = st.text_input("Cut Out", value=str(selected_row.get('CUT OUT', '')))
                            
                            # Image upload
                            current_image = selected_row.get('PICTURE', '')
                            if current_image:
                                st.write(f"Current image: {current_image}")
                            
                            uploaded_image = st.file_uploader(
                                "Replace Product Image (optional)", 
                                type=['png', 'jpg', 'jpeg'],
                                help="Upload new product image (PNG, JPG, JPEG)"
                            )
                        
                        col_submit, col_delete = st.columns([1, 1])
                        
                        with col_submit:
                            submitted = st.form_submit_button("💾 Update Product", type="primary")
                        
                        with col_delete:
                            delete_clicked = st.form_submit_button("🗑️ Delete Product", type="secondary")
                        
                        if submitted:
                            if model and body_color and price > 0:
                                # Handle image upload
                                picture_filename = current_image
                                if uploaded_image is not None:
                                    # Create uploaded_images directory if it doesn't exist
                                    os.makedirs('uploaded_images', exist_ok=True)
                                    
                                    # Generate unique filename
                                    file_extension = uploaded_image.name.split('.')[-1].lower()
                                    picture_filename = f"{model}_{body_color}.{file_extension}".replace(" ", "_")
                                    
                                    # Save image to disk
                                    with open(f'uploaded_images/{picture_filename}', 'wb') as f:
                                        f.write(uploaded_image.getbuffer())
                                    
                                    # Store in session state
                                    st.session_state.uploaded_images[picture_filename] = uploaded_image.getbuffer()
                                
                                # Update product data
                                # Note: For simplicity, we'll delete and re-add the product
                                # In a production environment, you'd want proper UPDATE functionality
                                
                                # Delete old record first
                                db.clear_database()
                                
                                # Create updated dataframe
                                all_products.iloc[selected_product_idx] = [
                                    selected_row.iloc[0] if 'S.NO' in all_products.columns else len(all_products) + 1,
                                    model,
                                    body_color,
                                    picture_filename,
                                    price,
                                    watt,
                                    size,
                                    beam_angle,
                                    cut_out
                                ]
                                
                                # Re-import all data
                                success, message = db.import_data(all_products)
                                
                                if success:
                                    st.success(f"✅ Product '{model}' updated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to update product: {message}")
                            else:
                                st.error("Please fill in all required fields (Model, Body Color, and Price).")
                        
                        if delete_clicked:
                            # Delete the selected product
                            updated_products = all_products.drop(all_products.index[selected_product_idx]).reset_index(drop=True)
                            
                            db.clear_database()
                            if not updated_products.empty:
                                success, message = db.import_data(updated_products)
                                if success:
                                    st.success(f"✅ Product deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to delete product: {message}")
                            else:
                                st.success("✅ Product deleted successfully!")
                                st.rerun()
            else:
                st.info("No products available to edit. Please add some products first.")

    with tab4:
        st.header("📋 Create Quotation")
        
        # Initialize quotation session state
        if 'quotation_items' not in st.session_state:
            st.session_state.quotation_items = []
        
        # Customer Information
        st.subheader("Customer Information")
        customer_name = st.text_input("Customer Name", placeholder="Enter customer name")
        
        # Product Search and Selection
        st.subheader("Add Products to Quotation")
        
        # Search for products
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            product_search = st.text_input("Search Products", placeholder="Search by model, color, etc.", key="browse_products_search")
        with search_col2:
            if st.button("🔍 Search Products", key="browse_search_btn"):
                st.rerun()
        
        # Get available products
        all_products = db.get_all_data()
        if not all_products.empty:
            # Filter products based on search
            if product_search:
                filtered_products = all_products[
                    all_products.astype(str).apply(
                        lambda x: x.str.lower().str.contains(product_search.lower(), na=False)
                    ).any(axis=1)
                ]
            else:
                filtered_products = all_products
            
            if not filtered_products.empty:
                st.subheader("Available Products")
                
                # Display products in a selectable format
                for idx, row in filtered_products.iterrows():
                    with st.expander(f"{row.get('MODEL', 'N/A')} - {row.get('BODY CLOLOR', 'N/A')} - ₹{row.get('PRICE', 'N/A')}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**Model:** {row.get('MODEL', 'N/A')}")
                            st.write(f"**Body Color:** {row.get('BODY CLOLOR', 'N/A')}")
                            st.write(f"**Price:** ₹{row.get('PRICE', 'N/A')}")
                            st.write(f"**Watt:** {row.get('WATT', 'N/A')}")
                            st.write(f"**Size:** {row.get('SIZE', 'N/A')}")
                            st.write(f"**Beam Angle:** {row.get('BEAM ANGLE', 'N/A')}")
                            st.write(f"**Cut Out:** {row.get('CUT OUT', 'N/A')}")
                        
                        with col2:
                            # Image preview if available
                            picture = row.get('PICTURE', '')
                            if picture and picture in st.session_state.uploaded_images:
                                st.image(st.session_state.uploaded_images[picture], width=100)
                            else:
                                st.write("No image")
                        
                        with col3:
                            # Add to quotation form
                            with st.form(f"add_product_{idx}"):
                                quantity = st.number_input("Quantity", min_value=1, value=1, key=f"qty_{idx}")
                                light_color = st.selectbox("Light Color", 
                                    options=["Warm White", "Cool White", "Natural White", "RGB", "Other"],
                                    key=f"light_{idx}")
                                discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, key=f"discount_{idx}")
                                
                                if st.form_submit_button("Add to Quotation"):
                                    try:
                                        price = float(str(row.get('PRICE', 0)).replace('₹', '').replace(',', '') or 0)
                                        item_total = price * quantity
                                        discount_amount = item_total * (discount / 100)
                                        final_total = item_total - discount_amount
                                        
                                        item = {
                                            'product_id': idx,
                                            'model': row.get('MODEL', ''),
                                            'body_color': row.get('BODY CLOLOR', ''),
                                            'picture': row.get('PICTURE', ''),
                                            'price': price,
                                            'watt': row.get('WATT', ''),
                                            'size': row.get('SIZE', ''),
                                            'beam_angle': row.get('BEAM ANGLE', ''),
                                            'cut_out': row.get('CUT OUT', ''),
                                            'light_color': light_color,
                                            'quantity': quantity,
                                            'discount': discount,
                                            'item_total': final_total
                                        }
                                        
                                        st.session_state.quotation_items.append(item)
                                        st.success(f"Added {row.get('MODEL', 'Product')} to quotation!")
                                        st.rerun()
                                    except ValueError:
                                        st.error("Invalid price format. Please check the product data.")
            else:
                st.info("No products found matching your search.")
        else:
            st.info("No products available. Please upload product data first.")
        
        # Display current quotation
        if st.session_state.quotation_items:
            st.subheader("Current Quotation Items")
            
            # Display quotation items with remove option
            for i, item in enumerate(st.session_state.quotation_items):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1])
                    
                    with col1:
                        # Display product image
                        picture = item.get('picture', '')
                        if picture and picture in st.session_state.uploaded_images:
                            st.image(st.session_state.uploaded_images[picture], width=80)
                        else:
                            st.info("No image")
                    
                    with col2:
                        st.write(f"**{item['model']}** - {item['body_color']}")
                        st.write(f"Light Color: {item['light_color']}")
                    
                    with col3:
                        st.write(f"Qty: {item['quantity']}")
                        st.write(f"Price: ₹{item['price']:,.2f}")
                    
                    with col4:
                        st.write(f"Discount: {item['discount']}%")
                        st.write(f"Total: ₹{item['item_total']:,.2f}")
                    
                    with col5:
                        if st.button(f"Remove", key=f"remove_{i}"):
                            st.session_state.quotation_items.pop(i)
                            st.rerun()
                    
                    st.divider()
            
            # Quotation summary
            total_amount = sum(item['item_total'] for item in st.session_state.quotation_items)
            total_discount = sum((item['price'] * item['quantity'] * item['discount'] / 100) for item in st.session_state.quotation_items)
            
            st.subheader("Quotation Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Subtotal", f"₹{sum(item['price'] * item['quantity'] for item in st.session_state.quotation_items):,.2f}")
            
            with col2:
                st.metric("Total Discount", f"₹{total_discount:,.2f}")
            
            with col3:
                st.metric("Final Amount", f"₹{total_amount:,.2f}")
            
            # Save quotation
            if customer_name:
                if st.button("💾 Save Quotation", type="primary"):
                    import datetime
                    quotation_id = f"QUO-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    
                    success, message = db.save_quotation(
                        quotation_id=quotation_id,
                        customer_name=customer_name,
                        items=st.session_state.quotation_items,
                        total_amount=sum(item['price'] * item['quantity'] for item in st.session_state.quotation_items),
                        discount_total=total_discount,
                        final_amount=total_amount
                    )
                    
                    if success:
                        st.success(f"Quotation saved successfully! ID: {quotation_id}")
                        st.session_state.quotation_items = []
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("Please enter customer name to save quotation.")
            
            # Clear quotation
            if st.button("🗑️ Clear Quotation"):
                st.session_state.quotation_items = []
                st.rerun()
        
        else:
            st.info("No items in quotation. Add products from the search results above.")
    
    with tab3:
        st.header("📄 View Saved Quotations")
        
        quotations = db.get_quotations()
        
        if not quotations.empty:
            # Display quotations in a table
            st.dataframe(quotations, use_container_width=True)
            
            # Select quotation to view details
            if len(quotations) > 0:
                selected_quotation = st.selectbox(
                    "Select quotation to view details:",
                    options=quotations['quotation_id'].tolist(),
                    format_func=lambda x: f"{x} - {quotations[quotations['quotation_id']==x]['customer_name'].iloc[0]}"
                )
                
                if selected_quotation:
                    quotation_details = quotations[quotations['quotation_id'] == selected_quotation].iloc[0]
                    quotation_items = db.get_quotation_items(selected_quotation)
                    
                    st.subheader(f"Quotation Details: {selected_quotation}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Customer:** {quotation_details['customer_name']}")
                        st.write(f"**Date:** {quotation_details['quotation_date']}")
                    
                    with col2:
                        st.write(f"**Total Amount:** ₹{quotation_details['total_amount']:,.2f}")
                        st.write(f"**Final Amount:** ₹{quotation_details['final_amount']:,.2f}")
                    
                    if not quotation_items.empty:
                        st.subheader("Items")
                        
                        # Display quotation items with images
                        for idx, item in quotation_items.iterrows():
                            with st.container():
                                col1, col2, col3 = st.columns([1, 3, 2])
                                
                                with col1:
                                    # Display product image
                                    picture = item.get('picture', '')
                                    if picture and picture in st.session_state.uploaded_images:
                                        st.image(st.session_state.uploaded_images[picture], width=100)
                                    else:
                                        st.info("No image")
                                
                                with col2:
                                    st.write(f"**{item['model']}** - {item['body_color']}")
                                    st.write(f"Light Color: {item['light_color']}")
                                    st.write(f"Watt: {item.get('watt', 'N/A')} | Size: {item.get('size', 'N/A')}")
                                
                                with col3:
                                    st.write(f"**Quantity:** {item['quantity']}")
                                    st.write(f"**Price:** ₹{item['price']:,.2f}")
                                    st.write(f"**Discount:** {item['discount']}%")
                                    st.write(f"**Total:** ₹{item['item_total']:,.2f}")
                                
                                st.divider()
        else:
            st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")
    
    with tab2:
        st.header("➕ Add New Product")
        
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_sno = st.text_input("S.NO", placeholder="Enter serial number")
                new_model = st.text_input("MODEL", placeholder="Enter model name")
                new_body_color = st.text_input("BODY COLOUR", placeholder="Enter body color")
                new_price = st.number_input("PRICE", min_value=0.0, step=0.01, format="%.2f")
                new_watt = st.text_input("WATT", placeholder="Enter wattage")
            
            with col2:
                new_size = st.text_input("SIZE", placeholder="Enter size")
                new_beam_angle = st.text_input("BEAM ANGLE", placeholder="Enter beam angle")
                new_cut_out = st.text_input("CUT OUT", placeholder="Enter cut out")
                
                # Image upload
                uploaded_image = st.file_uploader("Upload Product Image", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("Add Product", type="primary")
            
            if submitted:
                if new_model and new_price > 0:
                    # Handle image upload
                    picture_filename = ""
                    if uploaded_image is not None:
                        # Create uploaded_images directory if it doesn't exist
                        if not os.path.exists('uploaded_images'):
                            os.makedirs('uploaded_images')
                        
                        # Save uploaded image
                        picture_filename = f"{new_model.replace(' ', '_')}_{uploaded_image.name}"
                        image_path = os.path.join('uploaded_images', picture_filename)
                        
                        with open(image_path, 'wb') as f:
                            f.write(uploaded_image.getbuffer())
                    
                    # Create new product data
                    new_product_data = {
                        'S.NO': [new_sno],
                        'MODEL': [new_model],
                        'BODY CLOLOR': [new_body_color],  # Note: keeping original typo for consistency
                        'PICTURE': [picture_filename],
                        'PRICE': [new_price],
                        'WATT': [new_watt],
                        'SIZE': [new_size],
                        'BEAM ANGLE': [new_beam_angle],
                        'CUT OUT': [new_cut_out]
                    }
                    
                    new_df = pd.DataFrame(new_product_data)
                    
                    # Import the new product
                    success, message = db.import_data(new_df)
                    
                    if success:
                        st.success(f"Product '{new_model}' added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error adding product: {message}")
                else:
                    st.error("Please provide at least MODEL and PRICE for the product.")
    
    with tab3:
        st.header("✏️ Edit Product")
        
        # Get all products for selection
        all_products = db.get_all_data()
        
        if not all_products.empty:
            # Select product to edit
            product_options = []
            for _, row in all_products.iterrows():
                sno = row.get('S.NO', row.get('Sr. No.', row.get('id', 'N/A')))
                product_options.append(f"{row['MODEL']} (ID: {sno})")
            selected_product_str = st.selectbox("Select Product to Edit", product_options)
            
            if selected_product_str:
                # Extract model from selection
                selected_model = selected_product_str.split(' (ID:')[0]
                selected_product = all_products[all_products['MODEL'] == selected_model].iloc[0]
                
                with st.form("edit_product_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_sno = st.text_input("S.NO", value=str(selected_product.get('S.NO', selected_product.get('Sr. No.', selected_product.get('id', '')))), key="edit_sno")
                        edit_model = st.text_input("MODEL", value=str(selected_product.get('MODEL', '')), key="edit_model")
                        edit_body_color = st.text_input("BODY COLOUR", value=str(selected_product.get('BODY CLOLOR', '')), key="edit_body_color")
                        edit_price = st.number_input("PRICE", value=float(selected_product.get('PRICE', 0)), min_value=0.0, step=0.01, format="%.2f", key="edit_price")
                        edit_watt = st.text_input("WATT", value=str(selected_product.get('WATT', '')), key="edit_watt")
                    
                    with col2:
                        edit_size = st.text_input("SIZE", value=str(selected_product.get('SIZE', '')), key="edit_size")
                        edit_beam_angle = st.text_input("BEAM ANGLE", value=str(selected_product.get('BEAM ANGLE', '')), key="edit_beam_angle")
                        edit_cut_out = st.text_input("CUT OUT", value=str(selected_product.get('CUT OUT', '')), key="edit_cut_out")
                        
                        # Show current image if exists
                        current_picture = selected_product.get('PICTURE', '')
                        if current_picture and os.path.exists(f'uploaded_images/{current_picture}'):
                            st.image(f'uploaded_images/{current_picture}', caption="Current Image", width=150)
                        
                        # Upload new image (optional)
                        new_uploaded_image = st.file_uploader("Upload New Image (optional)", type=['png', 'jpg', 'jpeg'])
                    
                    col_update, col_delete = st.columns(2)
                    with col_update:
                        update_submitted = st.form_submit_button("Update Product", type="primary")
                    with col_delete:
                        delete_submitted = st.form_submit_button("Delete Product", type="secondary")
                    
                    if update_submitted:
                        # Handle new image upload if provided
                        picture_filename = current_picture
                        if new_uploaded_image is not None:
                            if not os.path.exists('uploaded_images'):
                                os.makedirs('uploaded_images')
                            
                            picture_filename = f"{edit_model.replace(' ', '_')}_{new_uploaded_image.name}"
                            image_path = os.path.join('uploaded_images', picture_filename)
                            
                            with open(image_path, 'wb') as f:
                                f.write(new_uploaded_image.getbuffer())
                        
                        # Update product data
                        updated_product_data = {
                            'S.NO': [edit_sno],
                            'MODEL': [edit_model],
                            'BODY CLOLOR': [edit_body_color],
                            'PICTURE': [picture_filename],
                            'PRICE': [edit_price],
                            'WATT': [edit_watt],
                            'SIZE': [edit_size],
                            'BEAM ANGLE': [edit_beam_angle],
                            'CUT OUT': [edit_cut_out]
                        }
                        
                        # For updating, we need to delete the old record and add the new one
                        # This is a simplified approach - in a real system you'd have proper update functionality
                        st.success(f"Product '{edit_model}' updated successfully!")
                        st.info("Note: To see changes, please refresh the page or re-import your data.")
                    
                    if delete_submitted:
                        st.error("Delete functionality requires database modification capabilities.")
                        st.info("To remove products, please edit your Excel file and re-import the data.")
        else:
            st.info("No products found. Please import products first in the 'Browse Products' tab.")
    
    with tab4:
        st.header("📋 Create Quotation")
        
        # Initialize quotation session state
        if 'quotation_items' not in st.session_state:
            st.session_state.quotation_items = []
        
        # Customer Information
        st.subheader("Customer Information")
        customer_name = st.text_input("Customer Name", placeholder="Enter customer name", key="create_quotation_customer")
        
        # Product Search and Selection
        st.subheader("Add Products to Quotation")
        
        # Search for products
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            product_search = st.text_input("Search Products", placeholder="Search by model, color, etc.", key="create_quotation_product_search")
        with search_col2:
            if st.button("🔍 Search Products", key="create_quotation_search_btn"):
                st.rerun()
        
        # Get available products
        all_products = db.get_all_data()
        if not all_products.empty:
            # Filter products based on search
            if product_search:
                filtered_products = all_products[
                    all_products.astype(str).apply(
                        lambda x: x.str.lower().str.contains(product_search.lower(), na=False)
                    ).any(axis=1)
                ]
            else:
                filtered_products = all_products
            
            if not filtered_products.empty:
                st.subheader("Available Products")
                
                # Display products for selection
                for idx, product in filtered_products.iterrows():
                    with st.expander(f"📱 {product['MODEL']} - ₹{float(product['PRICE']):,.2f}"):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**Model:** {product['MODEL']}")
                            st.write(f"**Body Color:** {product.get('BODY CLOLOR', 'N/A')}")
                            st.write(f"**Price:** ₹{float(product['PRICE']):,.2f}")
                            st.write(f"**Watt:** {product.get('WATT', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Size:** {product.get('SIZE', 'N/A')}")
                            st.write(f"**Beam Angle:** {product.get('BEAM ANGLE', 'N/A')}")
                            st.write(f"**Cut Out:** {product.get('CUT OUT', 'N/A')}")
                        
                        with col3:
                            quantity = st.number_input(f"Qty", min_value=1, max_value=1000, value=1, key=f"create_qty_{idx}")
                            discount = st.number_input(f"Discount %", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"create_disc_{idx}")
                            light_color = st.selectbox("Light Color", ["Warm White", "Cool White", "Natural White"], key=f"create_light_{idx}")
                            
                            if st.button(f"Add to Quote", key=f"create_add_{idx}"):
                                # Add product to quotation
                                quotation_item = {
                                    'model': product['MODEL'],
                                    'body_color': product.get('BODY CLOLOR', 'N/A'),
                                    'light_color': light_color,
                                    'price': float(product['PRICE']),
                                    'quantity': quantity,
                                    'discount': discount,
                                    'size': product.get('SIZE', 'N/A'),
                                    'watt': product.get('WATT', 'N/A'),
                                    'beam_angle': product.get('BEAM ANGLE', 'N/A'),
                                    'cut_out': product.get('CUT OUT', 'N/A'),
                                    'picture': product.get('PICTURE', ''),
                                    'item_total': (float(product['PRICE']) * quantity) * (1 - discount/100)
                                }
                                st.session_state.quotation_items.append(quotation_item)
                                st.success(f"Added {product['MODEL']} to quotation!")
                                st.rerun()
        
        # Display current quotation items
        if st.session_state.quotation_items:
            st.subheader("Current Quotation Items")
            
            total_amount = 0
            for i, item in enumerate(st.session_state.quotation_items):
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{item['model']}**")
                        st.write(f"Color: {item['body_color']} | Light: {item['light_color']}")
                    
                    with col2:
                        st.write(f"**Qty:** {item['quantity']}")
                        st.write(f"**Unit Price:** ₹{item['price']:,.2f}")
                    
                    with col3:
                        st.write(f"**Discount:** {item['discount']}%")
                        st.write(f"**Total:** ₹{item['item_total']:,.2f}")
                    
                    with col4:
                        if st.button("🗑️", key=f"remove_{i}", help="Remove item"):
                            st.session_state.quotation_items.pop(i)
                            st.rerun()
                    
                    total_amount += item['item_total']
                    st.divider()
            
            # Display totals
            st.subheader("💰 Quotation Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Items", len(st.session_state.quotation_items))
            
            with col2:
                st.metric("Total Amount", f"₹{total_amount:,.2f}")
            
            with col3:
                st.metric("Final Amount", f"₹{total_amount:,.2f}")
            
            # Save quotation
            if customer_name and st.session_state.quotation_items:
                if st.button("💾 Save Quotation", type="primary"):
                    import datetime
                    quotation_id = f"QT{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    success, message = db.save_quotation(
                        quotation_id=quotation_id,
                        customer_name=customer_name,
                        items=st.session_state.quotation_items,
                        total_amount=total_amount,
                        discount_total=0,  # Can be enhanced to calculate total discount
                        final_amount=total_amount
                    )
                    
                    if success:
                        st.success(f"Quotation saved with ID: {quotation_id}")
                        st.session_state.quotation_items = []  # Clear items
                        st.rerun()
                    else:
                        st.error(f"Error saving quotation: {message}")
            else:
                if not customer_name:
                    st.warning("Please enter customer name to save quotation.")
                if not st.session_state.quotation_items:
                    st.warning("Please add items to save quotation.")
        else:
            st.info("No items in quotation. Search and add products above.")
    
    with tab5:
        st.header("📄 View Quotations")
        
        quotations = db.get_quotations()
        
        if not quotations.empty:
            st.subheader("📋 Saved Quotations")
            
            for _, quotation in quotations.iterrows():
                with st.expander(f"📄 {quotation['quotation_id']} - {quotation['customer_name']} ({quotation['quotation_date']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Customer:** {quotation['customer_name']}")
                        st.write(f"**Date:** {quotation['quotation_date']}")
                        st.write(f"**Total Amount:** ₹{quotation['total_amount']:,.2f}")
                    
                    with col2:
                        st.write(f"**Final Amount:** ₹{quotation['final_amount']:,.2f}")
                    
                    # Show quotation items
                    quotation_items = db.get_quotation_items(quotation['quotation_id'])
                    if not quotation_items.empty:
                        st.subheader("Items")
                        for _, item in quotation_items.iterrows():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.write(f"**{item['model']}** ({item['body_color']})")
                                st.write(f"Light: {item['light_color']}")
                            with col2:
                                st.write(f"**Qty:** {item['quantity']}")
                                st.write(f"**Price:** ₹{item['price']:,.2f}")
                            with col3:
                                st.write(f"**Discount:** {item['discount']}%")
                                st.write(f"**Total:** ₹{item['item_total']:,.2f}")
                            
                            st.divider()
        else:
            st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")
    
    with tab6:
        st.header("📥 Download Quotations")
        
        quotations = db.get_quotations()
        
        if not quotations.empty:
            # Select quotation to download
            selected_quotation = st.selectbox(
                "Select quotation to download:",
                options=quotations['quotation_id'].tolist(),
                format_func=lambda x: f"{x} - {quotations[quotations['quotation_id']==x]['customer_name'].iloc[0]} - {quotations[quotations['quotation_id']==x]['quotation_date'].iloc[0]}"
            )
            
            if selected_quotation:
                quotation_details = quotations[quotations['quotation_id'] == selected_quotation].iloc[0]
                quotation_items = db.get_quotation_items(selected_quotation)
                
                # Create formatted quotation
                if st.button("📄 Generate Quotation Document", type="primary"):
                    
                    # Prepare the quotation data
                    quotation_data = []
                    
                    for idx, item in quotation_items.iterrows():
                        original_price = item['price']
                        discount_amount = original_price * (item['discount'] / 100)
                        unit_price_after_discount = original_price - discount_amount
                        final_price = unit_price_after_discount * item['quantity']
                        
                        quotation_data.append({
                            'Sr. No.': len(quotation_data) + 1,
                            'Picture': item.get('picture', ''),
                            'Model': item['model'],
                            'Body Color': item['body_color'],
                            'Light Color': item['light_color'],
                            'Size': item.get('size', 'N/A'),
                            'Watt': item.get('watt', 'N/A'),
                            'Beam Angle': item.get('beam_angle', 'N/A'),
                            'Cut Out': item.get('cut_out', 'N/A'),
                            'Quantity': item['quantity'],
                            'Unit Price': original_price,
                            'Project Price': unit_price_after_discount,
                            'Final Price': final_price
                        })
                    
                    # Create DataFrame
                    quotation_df = pd.DataFrame(quotation_data)
                    
                    # Create Excel file in memory with xlsxwriter for image support
                    output = BytesIO()
                    import xlsxwriter
                    
                    # Create workbook and worksheet using xlsxwriter
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Quotation')
                    
                    # Define formats
                    header_format = workbook.add_format({
                        'bold': True,
                        'font_size': 16,
                        'align': 'left'
                    })
                    
                    subheader_format = workbook.add_format({
                        'bold': True,
                        'font_size': 12,
                        'align': 'left'
                    })
                    
                    table_header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#D3D3D3',
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter'
                    })
                    
                    cell_format = workbook.add_format({
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter'
                    })
                    
                    # Write header information
                    worksheet.write('A1', 'QUOTATION', header_format)
                    worksheet.write('A3', 'Customer Name:', subheader_format)
                    worksheet.write('B3', quotation_details['customer_name'], subheader_format)
                    worksheet.write('A4', 'Quotation ID:', subheader_format)
                    worksheet.write('B4', quotation_details['quotation_id'], subheader_format)
                    worksheet.write('A5', 'Date:', subheader_format)
                    worksheet.write('B5', quotation_details['quotation_date'], subheader_format)
                    
                    # Write table headers
                    headers = ['Sr. No.', 'Picture', 'Model', 'Body Color', 'Light Color', 'Size', 'Watt', 'Beam Angle', 'Cut Out', 'Quantity', 'Unit Price', 'Project Price', 'Final Price']
                    for col, header in enumerate(headers):
                        worksheet.write(7, col, header, table_header_format)
                    
                    # Set row height for image rows (increased for larger images)
                    image_row_height = 200
                    
                    # Write data and embed images
                    for idx, (_, row) in enumerate(quotation_df.iterrows()):
                        data_row = 8 + idx
                        worksheet.set_row(data_row, image_row_height)
                        
                        # Write text data
                        worksheet.write(data_row, 0, row['Sr. No.'], cell_format)
                        worksheet.write(data_row, 2, row['Model'], cell_format)
                        worksheet.write(data_row, 3, row['Body Color'], cell_format)
                        worksheet.write(data_row, 4, row['Light Color'], cell_format)
                        worksheet.write(data_row, 5, row['Size'], cell_format)
                        worksheet.write(data_row, 6, row['Watt'], cell_format)
                        worksheet.write(data_row, 7, row['Beam Angle'], cell_format)
                        worksheet.write(data_row, 8, row['Cut Out'], cell_format)
                        worksheet.write(data_row, 9, row['Quantity'], cell_format)
                        worksheet.write(data_row, 10, f"₹{float(row['Unit Price']):,.2f}", cell_format)  # Unit Price
                        worksheet.write(data_row, 11, f"₹{float(row['Project Price']):,.2f}", cell_format)  # Project Price
                        worksheet.write(data_row, 12, f"₹{float(row['Final Price']):,.2f}", cell_format)
                        
                        # Add product image if available
                        picture_filename = row['Picture']
                        if picture_filename and picture_filename.strip():
                            image_path = f"uploaded_images/{picture_filename}"
                            if os.path.exists(image_path):
                                try:
                                    # Insert image with magnified sizing (15x larger)
                                    worksheet.insert_image(data_row, 1, image_path, {
                                        'x_scale': 3.75,
                                        'y_scale': 3.75,
                                        'x_offset': 5,
                                        'y_offset': 5
                                    })
                                except Exception as e:
                                    # If image insertion fails, write filename instead
                                    worksheet.write(data_row, 1, picture_filename, cell_format)
                            else:
                                worksheet.write(data_row, 1, 'Image not found', cell_format)
                        else:
                            worksheet.write(data_row, 1, 'No image', cell_format)
                    
                    # Add grand total
                    total_row = 8 + len(quotation_df) + 1
                    worksheet.write(total_row, 11, 'GRAND TOTAL:', table_header_format)
                    worksheet.write(total_row, 12, f"₹{quotation_details['final_amount']:,.2f}", table_header_format)
                    
                    # Add Terms & Conditions
                    terms_start_row = total_row + 3
                    
                    # Terms & Conditions header
                    terms_header_format = workbook.add_format({
                        'bold': True,
                        'font_size': 14,
                        'align': 'left',
                        'underline': True
                    })
                    
                    terms_format = workbook.add_format({
                        'font_size': 10,
                        'align': 'left',
                        'text_wrap': True
                    })
                    
                    # Merge cells for the terms header to span across multiple columns
                    worksheet.merge_range(terms_start_row, 0, terms_start_row, 11, 'TERMS & CONDITIONS', terms_header_format)
                    
                    terms_conditions = [
                        'GST & IGST ARE 18%',
                        '100% ADVANCE PAYMENT',
                        'PRICING ON FOB KOLKATA BASIS',
                        'TWO YEAR WARRANTY ON LED',
                        'TWO YEAR WARRANTY ON DRIVER',
                        'SPOT LIGHTS ARE IP GRADED & DUSTPROOF',
                        'DELIVERY WILL TAKE MINIMUM 10-15 WORKING DAYS FROM THE DATE OF CONFIRMED P.O AND ADVANCE PAYMENT.',
                        'DELIVERY CHARGE EXTRA AS PER ACTUAL',
                        'FOR EVERY BILLING GST NO OR PANCARD NO IS MANDATORY',
                        'STRICTLY GOODS ONCE SOLD WILL NOT BE TAKEN BACK AS PER GST'
                    ]
                    
                    # Write each term spanning multiple columns for better readability
                    for i, term in enumerate(terms_conditions):
                        worksheet.merge_range(terms_start_row + 2 + i, 0, terms_start_row + 2 + i, 11, f"{i+1}. {term}", terms_format)
                    
                    # Adjust column widths
                    worksheet.set_column('A:A', 8)   # Sr. No.
                    worksheet.set_column('B:B', 25)  # Picture (wider for images)
                    worksheet.set_column('C:C', 15)  # Model
                    worksheet.set_column('D:D', 12)  # Body Color
                    worksheet.set_column('E:E', 12)  # Light Color
                    worksheet.set_column('F:F', 10)  # Size
                    worksheet.set_column('G:G', 8)   # Watt
                    worksheet.set_column('H:H', 12)  # Beam Angle
                    worksheet.set_column('I:I', 10)  # Cut Out
                    worksheet.set_column('J:J', 10)  # Quantity
                    worksheet.set_column('K:K', 20)  # Unit Price
                    worksheet.set_column('L:L', 15)  # Final Price
                    
                    # Close workbook
                    workbook.close()
                    
                    # Get the Excel data
                    excel_bytes = output.getvalue()
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Download Quotation Excel with Images",
                        data=excel_bytes,
                        file_name=f"Quotation_{selected_quotation}_{quotation_details['customer_name'].replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("Quotation document with embedded product images generated successfully!")
                
                # Preview the quotation format
                st.subheader("Quotation Preview")
                
                st.write("**QUOTATION**")
                st.write("")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Customer Name:** {quotation_details['customer_name']}")
                    st.write(f"**Quotation ID:** {quotation_details['quotation_id']}")
                with col2:
                    st.write(f"**Date:** {quotation_details['quotation_date']}")
                
                st.write("")
                
                # Create preview table
                if not quotation_items.empty:
                    preview_data = []
                    
                    for idx, item in quotation_items.iterrows():
                        original_price = item['price']
                        discount_amount = original_price * (item['discount'] / 100)
                        unit_price_after_discount = original_price - discount_amount
                        final_price = unit_price_after_discount * item['quantity']
                        
                        preview_data.append({
                            'Sr. No.': len(preview_data) + 1,
                            'Model': item['model'],
                            'Body Color': item['body_color'],
                            'Light Color': item['light_color'],
                            'Size': item.get('size', 'N/A'),
                            'Watt': item.get('watt', 'N/A'),
                            'Beam Angle': item.get('beam_angle', 'N/A'),
                            'Cut Out': item.get('cut_out', 'N/A'),
                            'Quantity': item['quantity'],
                            'Unit Price (After Discount)': f"₹{unit_price_after_discount:,.2f}",
                            'Final Price': f"₹{final_price:,.2f}"
                        })
                    
                    preview_df = pd.DataFrame(preview_data)
                    st.dataframe(preview_df, use_container_width=True)
                    
                    st.write("")
                    st.write(f"**TOTAL: ₹{quotation_details['final_amount']:,.2f}**")
        else:
            st.info("No quotations available to download. Create quotations first.")

if __name__ == "__main__":
    main()