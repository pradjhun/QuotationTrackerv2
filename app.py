import streamlit as st
import pandas as pd
import os
from io import BytesIO
from database_manager import DatabaseManager
from auth_manager import AuthManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term

def init_database():
    """Initialize the database if it doesn't exist."""
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseManager()

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
    # Display company logo in top left corner
    col_logo, col_title = st.columns([1, 3])
    
    with col_logo:
        try:
            st.image("company_logo.webp", width=200)
        except:
            pass  # If logo not found, continue without it
    
    with col_title:
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
        st.subheader("Password Management")
        
        # Admin's own password change
        st.write("### Change Your Password")
        with st.form("change_own_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_submitted = st.form_submit_button("🔑 Change My Password", type="primary")
            
            if change_submitted:
                if current_password and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("New passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
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
        
        st.divider()
        
        # Reset other users' passwords
        st.write("### Reset User Passwords")
        st.info("As an admin, you can reset passwords for other users. They will be notified to change their password on next login.")
        
        users = auth.get_all_users()
        other_users = [user for user in users if user['username'] != st.session_state.user_info['username']]
        
        if other_users:
            with st.form("reset_user_password_form"):
                user_options = [f"{user['username']} ({user['role']})" for user in other_users]
                selected_user_option = st.selectbox("Select User", user_options)
                new_user_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)")
                confirm_user_password = st.text_input("Confirm New Password", type="password")
                
                reset_submitted = st.form_submit_button("🔑 Reset User Password", type="secondary")
                
                if reset_submitted:
                    if selected_user_option and new_user_password and confirm_user_password:
                        if new_user_password != confirm_user_password:
                            st.error("New passwords do not match.")
                        elif len(new_user_password) < 6:
                            st.error("Password must be at least 6 characters long.")
                        else:
                            # Extract username from selection
                            selected_username = selected_user_option.split(' (')[0]
                            
                            # For password reset by admin, we'll use a special method
                            # Since admin doesn't know the old password, we need to add this functionality
                            success, message = auth.admin_reset_password(
                                selected_username,
                                new_user_password,
                                st.session_state.user_info['username']
                            )
                            
                            if success:
                                st.success(f"Password reset successfully for user: {selected_username}")
                            else:
                                st.error(message)
                    else:
                        st.error("Please fill in all fields.")
        else:
            st.info("No other users to manage.")

def main():
    st.set_page_config(
        page_title="Quotation Management System",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize authentication
    init_auth()
    
    # Check authentication
    is_authenticated, user_info = check_authentication()
    
    if not is_authenticated:
        login_page()
        return
    
    # Initialize database
    init_database()
    db = st.session_state.db
    
    # Initialize session state for quotation items
    if 'quotation_items' not in st.session_state:
        st.session_state.quotation_items = []
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("📊 Quotation Management System")
    
    with col2:
        if user_info:
            st.write(f"**User:** {user_info['username']}")
            st.write(f"**Role:** {user_info['role'].title()}")
    
    with col3:
        if st.button("🚪 Logout", type="secondary"):
            logout()
    
    st.markdown("---")
    
    # Create tabs based on user role
    if user_info and user_info['role'] == 'admin':
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📋 Browse Products", 
            "➕ Add Product", 
            "✏️ Edit Product",
            "💼 Create Quotation", 
            "📄 View Quotations", 
            "⬇️ Download Quotations",
            "👥 Admin Panel"
        ])
        
        # Admin Panel tab
        with tab7:
            admin_panel()
        
        # Admin-only tabs
        with tab2:
            st.header("➕ Add New Product")
            
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_sno = st.text_input("S.NO", placeholder="Enter serial number")
                    new_model = st.text_input("MODEL", placeholder="Enter model name")
                    new_body_color = st.text_input("BODY COLOR", placeholder="Enter body color")
                    
                    # Picture upload
                    uploaded_picture = st.file_uploader(
                        "Upload Product Picture", 
                        type=['jpg', 'jpeg', 'png', 'gif'],
                        help="Upload product image (JPG, PNG, GIF)"
                    )
                    
                    # Option to enter filename manually if no upload
                    if not uploaded_picture:
                        new_picture = st.text_input("Or enter picture filename", placeholder="picture.jpg")
                    else:
                        new_picture = uploaded_picture.name
                
                with col2:
                    new_price = st.number_input("PRICE", min_value=0.0, format="%.2f")
                    new_watt = st.text_input("WATT", placeholder="Enter wattage")
                    new_size = st.text_input("SIZE", placeholder="Enter size")
                    new_beam_angle = st.text_input("BEAM ANGLE", placeholder="Enter beam angle")
                    new_cut_out = st.text_input("CUT OUT", placeholder="Enter cut out")
                
                submitted = st.form_submit_button("➕ Add Product", type="primary")
                
                if submitted:
                    if new_model and new_body_color:  # Basic validation
                        # Handle image upload
                        picture_filename = new_picture
                        if uploaded_picture:
                            # Create uploaded_images directory if it doesn't exist
                            import os
                            upload_dir = "uploaded_images"
                            if not os.path.exists(upload_dir):
                                os.makedirs(upload_dir)
                            
                            # Save the uploaded file
                            file_path = os.path.join(upload_dir, uploaded_picture.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_picture.getbuffer())
                            
                            picture_filename = uploaded_picture.name
                            st.success(f"Image uploaded successfully: {picture_filename}")
                        
                        new_product = {
                            'S.NO': new_sno if new_sno else '',
                            'MODEL': new_model,
                            'BODY CLOLOR': new_body_color,
                            'PICTURE': picture_filename,
                            'PRICE': new_price,
                            'WATT': new_watt,
                            'SIZE': new_size,
                            'BEAM ANGLE': new_beam_angle,
                            'CUT OUT': new_cut_out
                        }
                        
                        # Add to database
                        new_df = pd.DataFrame([new_product])
                        success, message = db.import_data(new_df)
                        
                        if success:
                            st.success("Product added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add product: {message}")
                    else:
                        st.error("Please fill in at least Model and Body Color")
        
        with tab3:
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
                                edit_model = st.text_input("MODEL", value=str(selected_product.get('MODEL', '')), key="edit_model")
                                edit_body_color = st.text_input("BODY COLOR", value=str(selected_product.get('BODY CLOLOR', '')), key="edit_body_color")
                                
                                # Picture upload for editing
                                current_picture = str(selected_product.get('PICTURE', ''))
                                st.write(f"Current picture: {current_picture}")
                                
                                uploaded_picture_edit = st.file_uploader(
                                    "Upload New Picture", 
                                    type=['jpg', 'jpeg', 'png', 'gif'],
                                    help="Upload new product image (JPG, PNG, GIF)",
                                    key="edit_picture_upload"
                                )
                                
                                # Option to keep current picture or change filename
                                if uploaded_picture_edit:
                                    edit_picture = uploaded_picture_edit.name
                                else:
                                    edit_picture = st.text_input("Or edit picture filename", value=current_picture, key="edit_picture")
                            
                            with col2:
                                try:
                                    current_price = float(selected_product.get('PRICE', 0))
                                except (ValueError, TypeError):
                                    current_price = 0.0
                                edit_price = st.number_input("PRICE", value=current_price, min_value=0.0, format="%.2f", key="edit_price")
                                edit_watt = st.text_input("WATT", value=str(selected_product.get('WATT', '')), key="edit_watt")
                                edit_size = st.text_input("SIZE", value=str(selected_product.get('SIZE', '')), key="edit_size")
                                edit_beam_angle = st.text_input("BEAM ANGLE", value=str(selected_product.get('BEAM ANGLE', '')), key="edit_beam_angle")
                                edit_cut_out = st.text_input("CUT OUT", value=str(selected_product.get('CUT OUT', '')), key="edit_cut_out")
                            
                            col_submit, col_delete = st.columns([1, 1])
                            
                            with col_submit:
                                update_submitted = st.form_submit_button("💾 Update Product", type="primary")
                            
                            with col_delete:
                                delete_clicked = st.form_submit_button("🗑️ Delete Product", type="secondary")
                            
                            if update_submitted:
                                if edit_model and edit_body_color:
                                    # Handle image upload for editing
                                    picture_filename = edit_picture
                                    if uploaded_picture_edit:
                                        # Create uploaded_images directory if it doesn't exist
                                        import os
                                        upload_dir = "uploaded_images"
                                        if not os.path.exists(upload_dir):
                                            os.makedirs(upload_dir)
                                        
                                        # Save the uploaded file
                                        file_path = os.path.join(upload_dir, uploaded_picture_edit.name)
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_picture_edit.getbuffer())
                                        
                                        picture_filename = uploaded_picture_edit.name
                                        st.success(f"New image uploaded: {picture_filename}")
                                    
                                    # Update product in database
                                    updated_product = {
                                        'S.NO': edit_sno,
                                        'MODEL': edit_model,
                                        'BODY CLOLOR': edit_body_color,
                                        'PICTURE': picture_filename,
                                        'PRICE': edit_price,
                                        'WATT': edit_watt,
                                        'SIZE': edit_size,
                                        'BEAM ANGLE': edit_beam_angle,
                                        'CUT OUT': edit_cut_out
                                    }
                                    
                                    # Update the dataframe
                                    all_products_updated = all_products.copy()
                                    for col, value in updated_product.items():
                                        if col in all_products_updated.columns:
                                            all_products_updated.loc[selected_index, col] = value
                                    
                                    # Clear and reimport
                                    db.clear_database()
                                    success, message = db.import_data(all_products_updated)
                                    
                                    if success:
                                        st.success("Product updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to update product: {message}")
                                else:
                                    st.error("Model and Body Color are required")
                            
                            if delete_clicked:
                                # Delete the selected product
                                updated_products = all_products.drop(selected_index).reset_index(drop=True)
                                
                                db.clear_database()
                                if not updated_products.empty:
                                    success, message = db.import_data(updated_products)
                                    if success:
                                        st.success("Product deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to delete product: {message}")
                                else:
                                    st.success("Product deleted successfully!")
                                    st.rerun()
            else:
                st.info("No products available to edit. Please import some data first.")
    else:
        tab1, tab4, tab5, tab6 = st.tabs([
            "📋 Browse Products", 
            "💼 Create Quotation", 
            "📄 View Quotations", 
            "⬇️ Download Quotations"
        ])
    
    with tab1:
        st.header("📋 Browse Products Database")
        
        # Upload section (admin only)
        if user_info and user_info['role'] == 'admin':
            st.subheader("📤 Import Products from Excel")
            uploaded_file = st.file_uploader(
                "Choose an Excel file", 
                type=['xlsx', 'xls'],
                help="Upload Excel file with columns: S.NO, MODEL, BODY CLOLOR, PICTURE, PRICE, WATT, SIZE, BEAM ANGLE, CUT OUT"
            )
            
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    # Validate structure
                    is_valid, message = validate_excel_structure(df)
                    
                    if is_valid:
                        st.success(message)
                        
                        # Preview data
                        st.subheader("📋 Data Preview")
                        st.dataframe(df.head(), use_container_width=True)
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("📥 Import Data", type="primary"):
                                success, import_message = db.import_data(df)
                                if success:
                                    st.success(import_message)
                                    st.rerun()
                                else:
                                    st.error(import_message)
                        
                        with col2:
                            if st.button("🗑️ Clear Database", type="secondary"):
                                db.clear_database()
                                st.success("Database cleared successfully!")
                                st.rerun()
                    else:
                        st.error(message)
                        
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
        
        # Search and filter section
        st.subheader("🔍 Search & Filter Products")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_term = st.text_input(
                "Search across all columns",
                placeholder="Enter search term...",
                help="Search will look across all columns in the database"
            )
        
        with col2:
            search_button = st.button("Search", type="primary")
        
        # Get filtered data
        if search_term:
            filtered_data = db.search_data(search_term)
        else:
            filtered_data = db.get_all_data()
        
        # Display results
        if not filtered_data.empty:
            st.subheader(f"📊 Results ({len(filtered_data)} records)")
            
            # Format and display data
            formatted_data = format_dataframe_display(filtered_data)
            st.dataframe(formatted_data, use_container_width=True)
        else:
            st.info("No records found. Please upload data or adjust your search criteria.")
    
    with tab4:
        st.header("💼 Create Quotation")
        
        # Initialize quotation session state
        if 'quotation_items' not in st.session_state:
            st.session_state.quotation_items = []
        
        # Customer Information
        st.subheader("Customer Information")
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Organization Name", placeholder="Enter organization name")
            sales_person = st.text_input("Sales Person Name", placeholder="Enter sales person name")
        
        with col2:
            customer_address = st.text_area("Customer Address", placeholder="Enter customer address", height=100)
            sales_contact = st.text_input("Sales Person Contact", placeholder="Enter contact number")
        
        # Product Search and Selection
        st.subheader("Add Products to Quotation")
        
        # Search for products
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            product_search = st.text_input("Search Products", placeholder="Search by model, color, etc.")
        with search_col2:
            if st.button("🔍 Search Products"):
                st.rerun()
        
        # Get search results
        if product_search:
            search_results = db.search_data(product_search)
        else:
            search_results = db.get_all_data()
        
        if not search_results.empty:
            st.subheader("Available Products")
            
            # Display products with "Add to Quotation" buttons
            for idx, row in search_results.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"**{row.get('MODEL', 'N/A')}** - {row.get('BODY CLOLOR', 'N/A')}")
                        st.write(f"Price: ₹{row.get('PRICE', 'N/A')} | Watt: {row.get('WATT', 'N/A')}")
                    
                    with col2:
                        quantity = st.number_input(
                            "Quantity", 
                            min_value=1, 
                            value=1, 
                            key=f"qty_{idx}"
                        )
                        discount = st.number_input(
                            "Discount %", 
                            min_value=0.0, 
                            max_value=100.0, 
                            value=0.0, 
                            key=f"disc_{idx}"
                        )
                        light_color = st.text_input(
                            "Light Color", 
                            placeholder="e.g., Warm White, Cool White",
                            key=f"light_{idx}"
                        )
                    
                    with col3:
                        if st.button("➕ Add", key=f"add_{idx}"):
                            # Add item to quotation with all required fields
                            price = float(row.get('PRICE', 0))
                            item_total = quantity * price * (1 - discount/100)
                            item = {
                                'product_id': idx,  # Use the dataframe index as product_id
                                'model': row.get('MODEL', 'N/A'),
                                'body_color': row.get('BODY CLOLOR', 'N/A'),
                                'picture': row.get('PICTURE', ''),
                                'price': price,
                                'watt': row.get('WATT', ''),
                                'size': row.get('SIZE', ''),
                                'beam_angle': row.get('BEAM ANGLE', ''),
                                'cut_out': row.get('CUT OUT', ''),
                                'light_color': light_color,
                                'quantity': quantity,
                                'discount': discount,
                                'item_total': item_total,
                                'unit_price': price,
                                'discount_percent': discount,
                                'line_total': item_total
                            }
                            st.session_state.quotation_items.append(item)
                            st.success(f"Added {item['model']} to quotation!")
                            st.rerun()
                    
                    st.divider()
        
        # Display current quotation items
        if st.session_state.quotation_items:
            st.subheader("Current Quotation Items")
            
            total_amount = 0
            for i, item in enumerate(st.session_state.quotation_items):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"{item['model']} - {item['body_color']}")
                
                with col2:
                    st.write(f"Qty: {item['quantity']}")
                
                with col3:
                    st.write(f"₹{item['line_total']:.2f}")
                
                with col4:
                    if st.button("🗑️", key=f"remove_{i}"):
                        st.session_state.quotation_items.pop(i)
                        st.rerun()
                
                total_amount += item['line_total']
            
            st.write(f"**Total Amount: ₹{total_amount:.2f}**")
            
            # Generate quotation
            if customer_name and st.button("📄 Generate Quotation", type="primary"):
                # Save quotation to database
                quotation_id = f"Q{len(db.get_quotations()) + 1:04d}"
                
                success, message = db.save_quotation(
                    quotation_id=quotation_id,
                    customer_name=customer_name,
                    customer_address=customer_address,
                    items=st.session_state.quotation_items,
                    total_amount=total_amount,
                    discount_total=0,
                    final_amount=total_amount,
                    sales_person=sales_person,
                    sales_contact=sales_contact
                )
                
                if success:
                    st.success(f"Quotation {quotation_id} created successfully!")
                    # Clear quotation items
                    st.session_state.quotation_items = []
                    st.rerun()
                else:
                    st.error(f"Failed to save quotation: {message}")
        else:
            st.info("No items in quotation. Add products from the search results above.")
    
    with tab5:
        st.header("📄 View Saved Quotations")
        
        quotations = db.get_quotations()
        
        if not quotations.empty:
            # Display quotations in a table
            formatted_quotations = format_dataframe_display(quotations)
            st.dataframe(formatted_quotations, use_container_width=True)
            
            # Quotation details
            st.subheader("Quotation Details")
            quotation_ids = quotations['quotation_id'].tolist()
            selected_quotation = st.selectbox("Select quotation to view details:", quotation_ids)
            
            if selected_quotation:
                items = db.get_quotation_items(selected_quotation)
                if not items.empty:
                    st.write(f"**Items in {selected_quotation}:**")
                    formatted_items = format_dataframe_display(items)
                    st.dataframe(formatted_items, use_container_width=True)
                else:
                    st.info("No items found for this quotation.")
        else:
            st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")
    
    with tab6:
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
                            # Get quotation date, customer name, address, and sales person info
                            customer_name = quotation['customer_name']
                            customer_address = quotation.get('customer_address', '')
                            quotation_date = quotation.get('quotation_date', quotation.get('created_date', ''))
                            sales_person = quotation.get('sales_person', '')
                            sales_contact = quotation.get('sales_contact', '')
                            
                            # Export to Excel with customer and sales person info
                            excel_data = export_to_excel(items, customer_name=customer_name, customer_address=customer_address, quotation_date=quotation_date, quotation_id=quotation['quotation_id'], sales_person=sales_person, sales_contact=sales_contact)
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