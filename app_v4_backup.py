import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from database_manager import DatabaseManager
from auth_manager import AuthManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term
import base64

# Page configuration
st.set_page_config(
    page_title="Quotation Management System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_database():
    """Initialize the database if it doesn't exist."""
    try:
        db_manager = DatabaseManager()
        return db_manager
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        return None

def init_auth():
    """Initialize the authentication manager."""
    try:
        auth_manager = AuthManager()
        return auth_manager
    except Exception as e:
        st.error(f"Authentication system initialization failed: {str(e)}")
        return None

def check_authentication():
    """Check if user is authenticated and return user info."""
    if 'session_token' not in st.session_state:
        return False, None
    
    auth_manager = init_auth()
    if not auth_manager:
        return False, None
    
    is_valid, user_info = auth_manager.validate_session(st.session_state.session_token)
    if not is_valid:
        # Clear invalid session
        if 'session_token' in st.session_state:
            del st.session_state.session_token
        return False, None
    
    return True, user_info

def login_page():
    """Display login page."""
    st.title("🔐 Quotation Management System - Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Please Login to Continue")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    auth_manager = init_auth()
                    if auth_manager:
                        success, user_info = auth_manager.authenticate(username, password)
                        if success:
                            # Create session
                            session_token = auth_manager.create_session(username)
                            st.session_state.session_token = session_token
                            st.success("Login successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.error("Authentication system unavailable")
                else:
                    st.warning("Please enter both username and password")
        
        st.markdown("---")
        st.info("**Default Admin Credentials:**\n- Username: admin\n- Password: admin123")

def logout():
    """Handle user logout."""
    if 'session_token' in st.session_state:
        auth_manager = init_auth()
        if auth_manager:
            auth_manager.logout(st.session_state.session_token)
        del st.session_state.session_token
    st.rerun()

def admin_panel():
    """Admin panel for user management."""
    st.header("👥 User Management")
    
    auth_manager = init_auth()
    if not auth_manager:
        st.error("Authentication system unavailable")
        return
    
    # Get all users
    users = auth_manager.get_all_users()
    
    if users:
        # Display users in a table
        df_users = pd.DataFrame(users)
        df_users['created_at'] = pd.to_datetime(df_users['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.subheader("Existing Users")
        st.dataframe(
            df_users[['username', 'role', 'is_active', 'created_at', 'created_by']],
            use_container_width=True
        )
        
        # User management actions
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("User Actions")
            selected_user = st.selectbox("Select User", [user['username'] for user in users if user['username'] != 'admin'])
            
            if selected_user:
                user_info = next(user for user in users if user['username'] == selected_user)
                
                # Toggle active status
                new_status = not user_info['is_active']
                status_text = "Activate" if new_status else "Deactivate"
                if st.button(f"{status_text} User"):
                    success, message = auth_manager.update_user_status(selected_user, new_status)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                
                # Change role
                current_role = user_info['role']
                new_role = st.selectbox("Change Role", ['admin', 'user'], 
                                      index=0 if current_role == 'admin' else 1)
                if st.button("Update Role") and new_role != current_role:
                    success, message = auth_manager.change_user_role(selected_user, new_role)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                
                # Delete user
                if st.button("Delete User", type="secondary"):
                    success, message = auth_manager.delete_user(selected_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        with col2:
            st.subheader("Reset Password")
            reset_user = st.selectbox("Select User for Password Reset", 
                                    [user['username'] for user in users], key="reset_user")
            new_password = st.text_input("New Password", type="password", key="new_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
            
            if st.button("Reset Password"):
                if new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 6:
                            success, message = auth_manager.admin_reset_password(
                                reset_user, new_password, st.session_state.get('username', 'admin')
                            )
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.error("Password must be at least 6 characters long")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.warning("Please enter and confirm the new password")
    
    # Create new user
    st.markdown("---")
    st.subheader("Create New User")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
        with col2:
            new_role = st.selectbox("Role", ['user', 'admin'])
            confirm_new_password = st.text_input("Confirm Password", type="password")
        
        create_button = st.form_submit_button("Create User")
        
        if create_button:
            if new_username and new_password and confirm_new_password:
                if new_password == confirm_new_password:
                    if len(new_password) >= 6:
                        success, message = auth_manager.create_user(
                            new_username, new_password, new_role, 
                            st.session_state.get('username', 'admin')
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Password must be at least 6 characters long")
                else:
                    st.error("Passwords do not match")
            else:
                st.warning("Please fill in all fields")

def main():
    # Check authentication
    is_authenticated, user_info = check_authentication()
    
    if not is_authenticated:
        login_page()
        return
    
    # Store user info in session state
    st.session_state.username = user_info['username']
    st.session_state.user_role = user_info['role']
    
    # Initialize database
    db_manager = init_database()
    if not db_manager:
        st.error("Database system unavailable. Please try again later.")
        return
    
    # Sidebar
    with st.sidebar:
        st.title("💼 Quotation System")
        st.markdown(f"**Welcome, {user_info['username']}!**")
        st.markdown(f"*Role: {user_info['role'].title()}*")
        
        # Navigation
        if user_info['role'] == 'admin':
            pages = ["📊 Dashboard", "📁 Data Management", "💰 Create Quotation", "📋 View Quotations", "👥 User Management"]
        else:
            pages = ["📊 Dashboard", "💰 Create Quotation", "📋 View Quotations"]
        
        selected_page = st.radio("Navigate", pages)
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    # Main content based on selected page
    if selected_page == "📊 Dashboard":
        st.title("📊 Dashboard")
        
        # Get statistics
        total_records = db_manager.get_total_records()
        quotations_df = db_manager.get_quotations()
        total_quotations = len(quotations_df)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", total_records)
        
        with col2:
            st.metric("Total Quotations", total_quotations)
        
        with col3:
            if not quotations_df.empty:
                total_value = quotations_df['final_amount'].sum()
                st.metric("Total Quotation Value", f"₹{total_value:,.2f}")
            else:
                st.metric("Total Quotation Value", "₹0.00")
        
        with col4:
            if not quotations_df.empty:
                avg_value = quotations_df['final_amount'].mean()
                st.metric("Average Quotation", f"₹{avg_value:,.2f}")
            else:
                st.metric("Average Quotation", "₹0.00")
        
        # Recent quotations
        if not quotations_df.empty:
            st.subheader("📋 Recent Quotations")
            recent_quotations = quotations_df.head(10)
            recent_quotations['created_at'] = pd.to_datetime(recent_quotations['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Format the display
            display_df = recent_quotations[['quotation_id', 'customer_name', 'final_amount', 'created_at']].copy()
            display_df['final_amount'] = display_df['final_amount'].apply(lambda x: f"₹{x:,.2f}")
            display_df.columns = ['Quotation ID', 'Customer Name', 'Final Amount', 'Created At']
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No quotations created yet.")
    
    elif selected_page == "📁 Data Management" and user_info['role'] == 'admin':
        st.title("📁 Data Management")
        
        # File upload section
        st.subheader("📤 Upload Product Data")
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload Excel file with product data including columns: model, body_color, picture, price, watt, size, beam_angle, cut_out"
        )
        
        if uploaded_file is not None:
            try:
                # Read the Excel file
                df = pd.read_excel(uploaded_file)
                
                # Validate structure
                is_valid, message = validate_excel_structure(df)
                
                if is_valid:
                    st.success("✅ File structure is valid!")
                    
                    # Show preview
                    st.subheader("📋 Data Preview")
                    st.dataframe(format_dataframe_display(df.head(10)), use_container_width=True)
                    
                    # Import options
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.info(f"📊 File contains {len(df)} records")
                    
                    with col2:
                        if st.button("💾 Import Data", type="primary"):
                            with st.spinner("Importing data..."):
                                success, import_message = db_manager.import_data(df)
                                
                                if success:
                                    st.success(f"✅ {import_message}")
                                    st.balloons()
                                else:
                                    st.error(f"❌ {import_message}")
                else:
                    st.error(f"❌ {message}")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        # Current data section
        st.markdown("---")
        st.subheader("📊 Current Database")
        
        total_records = db_manager.get_total_records()
        st.info(f"Total records in database: {total_records}")
        
        if total_records > 0:
            # Show sample data
            sample_data = db_manager.get_all_data().head(10)
            if not sample_data.empty:
                st.subheader("Sample Data")
                st.dataframe(format_dataframe_display(sample_data), use_container_width=True)
            
            # Clear database option
            st.markdown("---")
            st.subheader("⚠️ Danger Zone")
            if st.button("🗑️ Clear All Data", type="secondary"):
                if 'confirm_clear' not in st.session_state:
                    st.session_state.confirm_clear = True
                    st.warning("⚠️ Are you sure? This will delete ALL product data!")
                    st.rerun()
            
            if st.session_state.get('confirm_clear', False):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Clear All Data", type="secondary"):
                        db_manager.clear_database()
                        st.session_state.confirm_clear = False
                        st.success("✅ Database cleared successfully!")
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state.confirm_clear = False
                        st.rerun()
    
    elif selected_page == "💰 Create Quotation":
        st.title("💰 Create Quotation")
        
        # Check if there's data in the database
        total_records = db_manager.get_total_records()
        if total_records == 0:
            st.warning("⚠️ No product data available. Please upload product data first.")
            if user_info['role'] == 'admin':
                st.info("💡 Go to 'Data Management' to upload product data.")
            else:
                st.info("💡 Please contact an administrator to upload product data.")
            return
        
        # Customer information
        st.subheader("👤 Customer Information")
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name *", placeholder="Enter customer name")
        
        with col2:
            customer_address = st.text_area("Customer Address", placeholder="Enter customer address")
        
        # Product search and selection
        st.subheader("🔍 Product Search & Selection")
        
        # Search filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("🔍 Search Products", placeholder="Search by model, color, etc.")
        
        with col2:
            # Get unique values for filters
            all_data = db_manager.get_all_data()
            if not all_data.empty:
                body_colors = ['All'] + sorted(all_data['body_color'].dropna().unique().tolist())
                selected_color = st.selectbox("Body Color", body_colors)
            else:
                selected_color = 'All'
        
        with col3:
            if not all_data.empty:
                watts = ['All'] + sorted(all_data['watt'].dropna().unique().tolist())
                selected_watt = st.selectbox("Wattage", watts)
            else:
                selected_watt = 'All'
        
        # Build filters
        filters = {}
        if selected_color != 'All':
            filters['body_color'] = selected_color
        if selected_watt != 'All':
            filters['watt'] = selected_watt
        
        # Search and display products
        if search_term or filters:
            filtered_data = db_manager.search_data(clean_search_term(search_term), filters)
        else:
            filtered_data = db_manager.get_all_data()
        
        if not filtered_data.empty:
            st.subheader(f"📦 Available Products ({len(filtered_data)} found)")
            
            # Initialize quotation items in session state
            if 'quotation_items' not in st.session_state:
                st.session_state.quotation_items = []
            
            # Display products with add to quotation option
            for idx, row in filtered_data.iterrows():
                with st.expander(f"🔸 {row['model']} - {row['body_color']} - ₹{row['price']:,.2f}"):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    
                    with col1:
                        st.write(f"**Model:** {row['model']}")
                        st.write(f"**Color:** {row['body_color']}")
                        st.write(f"**Price:** ₹{row['price']:,.2f}")
                    
                    with col2:
                        st.write(f"**Wattage:** {row['watt']}")
                        st.write(f"**Size:** {row['size']}")
                        st.write(f"**Beam Angle:** {row['beam_angle']}")
                    
                    with col3:
                        st.write(f"**Cut Out:** {row['cut_out']}")
                        
                        # Display image if available
                        if pd.notna(row['picture']) and row['picture']:
                            image_path = f"uploaded_images/{row['picture']}"
                            if os.path.exists(image_path):
                                try:
                                    st.image(image_path, width=100, caption="Product Image")
                                except:
                                    st.write("🖼️ Image available")
                            else:
                                st.write("🖼️ Image not found")
                        else:
                            st.write("📷 No image")
                    
                    with col4:
                        # Add to quotation form
                        with st.form(f"add_product_{idx}"):
                            def clean_value(value):
                                """Clean numeric values for display."""
                                if pd.isna(value) or value == '' or value is None:
                                    return 0
                                try:
                                    return float(value)
                                except (ValueError, TypeError):
                                    return 0
                            
                            quantity = st.number_input("Quantity", min_value=1, value=1, key=f"qty_{idx}")
                            light_color = st.text_input("Light Color", value="Warm White", key=f"color_{idx}")
                            discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"disc_{idx}")
                            
                            if st.form_submit_button("➕ Add to Quotation"):
                                # Calculate item total
                                price = clean_value(row['price'])
                                discount_amount = (price * quantity * discount) / 100
                                item_total = (price * quantity) - discount_amount
                                
                                # Create item
                                item = {
                                    'id': row['id'],
                                    'model': row['model'],
                                    'body_color': row['body_color'],
                                    'picture': row['picture'],
                                    'price': price,
                                    'watt': row['watt'],
                                    'size': row['size'],
                                    'beam_angle': row['beam_angle'],
                                    'cut_out': row['cut_out'],
                                    'light_color': light_color,
                                    'quantity': quantity,
                                    'discount': discount,
                                    'item_total': item_total
                                }
                                
                                st.session_state.quotation_items.append(item)
                                st.success(f"✅ Added {row['model']} to quotation!")
                                st.rerun()
        else:
            st.info("🔍 No products found matching your search criteria.")
        
        # Quotation summary
        if st.session_state.quotation_items:
            st.markdown("---")
            st.subheader("📋 Quotation Summary")
            
            # Display selected items
            items_df = pd.DataFrame(st.session_state.quotation_items)
            
            # Format for display
            display_df = items_df.copy()
            display_df['price'] = display_df['price'].apply(lambda x: f"₹{x:,.2f}")
            display_df['item_total'] = display_df['item_total'].apply(lambda x: f"₹{x:,.2f}")
            
            # Reorder columns for better display
            column_order = ['model', 'body_color', 'light_color', 'quantity', 'price', 'discount', 'item_total']
            display_cols = [col for col in column_order if col in display_df.columns]
            
            st.dataframe(
                format_dataframe_display(display_df[display_cols]),
                use_container_width=True
            )
            
            # Remove items option
            if len(st.session_state.quotation_items) > 0:
                st.subheader("🗑️ Remove Items")
                item_to_remove = st.selectbox(
                    "Select item to remove",
                    range(len(st.session_state.quotation_items)),
                    format_func=lambda x: f"{st.session_state.quotation_items[x]['model']} - {st.session_state.quotation_items[x]['body_color']}"
                )
                
                if st.button("🗑️ Remove Item"):
                    st.session_state.quotation_items.pop(item_to_remove)
                    st.success("✅ Item removed!")
                    st.rerun()
            
            # Calculate totals
            print("Available columns:", list(items_df.columns))
            subtotal = items_df['item_total'].sum()
            print(f"Using column 'item_total' for subtotal calculation: {subtotal}")
            
            gst_rate = 18  # 18% GST
            gst_amount = subtotal * (gst_rate / 100)
            total_amount = subtotal + gst_amount
            
            # Display totals
            col1, col2 = st.columns([2, 1])
            
            with col2:
                st.markdown("### 💰 Totals")
                st.write(f"**Subtotal:** ₹{subtotal:,.2f}")
                st.write(f"**GST ({gst_rate}%):** ₹{gst_amount:,.2f}")
                st.markdown(f"**Total Amount:** ₹{total_amount:,.2f}")
            
            # Generate quotation
            if customer_name:
                quotation_date = datetime.now().strftime("%Y-%m-%d")
                quotation_id = f"QT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Save Quotation", type="primary"):
                        # Save to database
                        success, message = db_manager.save_quotation(
                            quotation_id=quotation_id,
                            customer_name=customer_name,
                            customer_address=customer_address,
                            items=st.session_state.quotation_items,
                            total_amount=subtotal,
                            discount_total=0.0,  # Calculate if needed
                            final_amount=total_amount
                        )
                        
                        if success:
                            st.success(f"✅ Quotation saved successfully! ID: {quotation_id}")
                            # Clear the quotation
                            st.session_state.quotation_items = []
                            st.balloons()
                        else:
                            st.error(f"❌ Error saving quotation: {message}")
                
                with col2:
                    # Excel export
                    items = pd.DataFrame(st.session_state.quotation_items)
                    excel_data = export_to_excel(items, customer_name=customer_name, customer_address=customer_address, quotation_date=quotation_date, quotation_id=quotation_id)
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name=f"quotation_{quotation_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="secondary"
                    )
            else:
                st.warning("⚠️ Please enter customer name to save quotation.")
        
        # Clear quotation button
        if st.session_state.quotation_items:
            if st.button("🗑️ Clear Quotation", type="secondary"):
                st.session_state.quotation_items = []
                st.success("✅ Quotation cleared!")
                st.rerun()
    
    elif selected_page == "📋 View Quotations":
        st.title("📋 View Quotations")
        
        quotations_df = db_manager.get_quotations()
        
        if not quotations_df.empty:
            # Sort by creation date (newest first)
            quotations_df = quotations_df.sort_values('created_at', ascending=False)
            
            st.subheader(f"📊 Total Quotations: {len(quotations_df)}")
            
            # Search and filter options
            col1, col2 = st.columns(2)
            
            with col1:
                search_customer = st.text_input("🔍 Search by Customer Name")
            
            with col2:
                # Date filter
                date_filter = st.selectbox("📅 Filter by Date", ["All", "Today", "This Week", "This Month"])
            
            # Apply filters
            filtered_quotations = quotations_df.copy()
            
            if search_customer:
                filtered_quotations = filtered_quotations[
                    filtered_quotations['customer_name'].str.contains(search_customer, case=False, na=False)
                ]
            
            if date_filter != "All":
                now = datetime.now()
                if date_filter == "Today":
                    filtered_quotations = filtered_quotations[
                        pd.to_datetime(filtered_quotations['created_at']).dt.date == now.date()
                    ]
                elif date_filter == "This Week":
                    week_start = now - pd.Timedelta(days=now.weekday())
                    filtered_quotations = filtered_quotations[
                        pd.to_datetime(filtered_quotations['created_at']).dt.date >= week_start.date()
                    ]
                elif date_filter == "This Month":
                    month_start = now.replace(day=1)
                    filtered_quotations = filtered_quotations[
                        pd.to_datetime(filtered_quotations['created_at']).dt.date >= month_start.date()
                    ]
            
            # Display quotations
            if not filtered_quotations.empty:
                for idx, quotation in filtered_quotations.iterrows():
                    with st.expander(f"📄 {quotation['quotation_id']} - {quotation['customer_name']} - ₹{quotation['final_amount']:,.2f}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Customer:** {quotation['customer_name']}")
                            if pd.notna(quotation.get('customer_address')):
                                st.write(f"**Address:** {quotation['customer_address']}")
                            st.write(f"**Date:** {pd.to_datetime(quotation['created_at']).strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"**Total Amount:** ₹{quotation['final_amount']:,.2f}")
                            
                            # Get quotation items
                            items_df = db_manager.get_quotation_items(quotation['quotation_id'])
                            if not items_df.empty:
                                st.write(f"**Items:** {len(items_df)} products")
                                
                                # Show items summary
                                with st.expander("View Items"):
                                    display_items = items_df.copy()
                                    if 'price' in display_items.columns:
                                        display_items['price'] = display_items['price'].apply(lambda x: f"₹{x:,.2f}")
                                    if 'item_total' in display_items.columns:
                                        display_items['item_total'] = display_items['item_total'].apply(lambda x: f"₹{x:,.2f}")
                                    
                                    st.dataframe(
                                        format_dataframe_display(display_items),
                                        use_container_width=True
                                    )
                        
                        with col2:
                            # Download options
                            items_for_export = db_manager.get_quotation_items(quotation['quotation_id'])
                            if not items_for_export.empty:
                                excel_data = export_to_excel(
                                    items_for_export,
                                    customer_name=quotation['customer_name'],
                                    customer_address=quotation.get('customer_address', ''),
                                    quotation_date=pd.to_datetime(quotation['created_at']).strftime('%Y-%m-%d'),
                                    quotation_id=quotation['quotation_id']
                                )
                                
                                st.download_button(
                                    label="📥 Download Excel",
                                    data=excel_data,
                                    file_name=f"quotation_{quotation['quotation_id']}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
            else:
                st.info("🔍 No quotations found matching your search criteria.")
        else:
            st.info("📋 No quotations created yet.")
    
    elif selected_page == "👥 User Management" and user_info['role'] == 'admin':
        admin_panel()

if __name__ == "__main__":
    main()