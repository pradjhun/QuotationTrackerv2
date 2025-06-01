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
    
    # Admin-only tabs
    if user_info and user_info['role'] == 'admin':
        with tab2:
            st.header("➕ Add Product")
            st.error("Add Product functionality will be available in the next update.")
        
        with tab3:
            st.header("✏️ Edit Product")
            st.error("Edit Product functionality will be available in the next update.")
    
    with tab4:
        st.header("💼 Create Quotation")
        
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
                    
                    with col3:
                        if st.button("➕ Add", key=f"add_{idx}"):
                            # Add item to quotation
                            item = {
                                'model': row.get('MODEL', 'N/A'),
                                'body_color': row.get('BODY CLOLOR', 'N/A'),
                                'unit_price': float(row.get('PRICE', 0)),
                                'quantity': quantity,
                                'discount_percent': discount,
                                'line_total': quantity * float(row.get('PRICE', 0)) * (1 - discount/100)
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
                    items=st.session_state.quotation_items,
                    total_amount=total_amount,
                    discount_total=0,
                    final_amount=total_amount
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
                        st.write(f"Date: {quotation['created_date']}")
                    
                    with col3:
                        # Get quotation items for export
                        items = db.get_quotation_items(quotation['quotation_id'])
                        
                        if not items.empty:
                            # Export to Excel
                            excel_data = export_to_excel(items)
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