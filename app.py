import streamlit as st
import pandas as pd
import zipfile
import io
import os
from database_manager import DatabaseManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term
from typing import Dict, Any

def init_database():
    """Initialize the database if it doesn't exist."""
    db = DatabaseManager()
    return db

def main():
    st.set_page_config(
        page_title="Quotation Management System",
        page_icon="💡",
        layout="wide"
    )
    
    st.title("💡 Quotation Management System")
    st.write("Manage your product database and create professional quotations")
    
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
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Browse Products", "📋 Create Quotation", "📄 View Quotations", "📥 Download Quotations"])
    
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
    
    with tab2:
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
            product_search = st.text_input("Search Products", placeholder="Search by model, color, etc.")
        with search_col2:
            if st.button("🔍 Search Products"):
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
    
    with tab4:
        st.header("📥 Download Quotations")
        
        # Import pandas at the beginning of this scope
        import pandas as pd
        from io import BytesIO
        
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
                    
                    # Create DataFrame
                    quotation_df = pd.DataFrame(quotation_data)
                    
                    # Create Excel file in memory
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # Create header information
                        header_data = {
                            'Field': ['QUOTATION', '', 'Customer Name:', 'Quotation ID:', 'Date:', ''],
                            'Value': ['', '', quotation_details['customer_name'], 
                                    quotation_details['quotation_id'], 
                                    quotation_details['quotation_date'], '']
                        }
                        header_df = pd.DataFrame(header_data)
                        
                        # Write header
                        header_df.to_excel(writer, sheet_name='Quotation', index=False, header=False, startrow=0)
                        
                        # Write quotation items
                        quotation_df.to_excel(writer, sheet_name='Quotation', index=False, startrow=7)
                        
                        # Write totals
                        total_row = len(quotation_df) + 9
                        totals_data = {
                            'Field': ['', '', '', '', '', '', '', '', 'TOTAL:', f"₹{quotation_details['final_amount']:,.2f}"],
                        }
                        totals_df = pd.DataFrame([totals_data['Field']])
                        totals_df.to_excel(writer, sheet_name='Quotation', index=False, header=False, startrow=total_row)
                        
                        # Format the worksheet
                        worksheet = writer.sheets['Quotation']
                        
                        # Format header
                        worksheet['A1'] = 'QUOTATION'
                        worksheet['A3'] = 'Customer Name:'
                        worksheet['B3'] = quotation_details['customer_name']
                        worksheet['A4'] = 'Quotation ID:'
                        worksheet['B4'] = quotation_details['quotation_id']
                        worksheet['A5'] = 'Date:'
                        worksheet['B5'] = quotation_details['quotation_date']
                        
                        # Format totals
                        total_cell = f'I{total_row + 1}'
                        amount_cell = f'J{total_row + 1}'
                        worksheet[total_cell] = 'TOTAL:'
                        worksheet[amount_cell] = f"₹{quotation_details['final_amount']:,.2f}"
                        
                        # Adjust column widths
                        for column in worksheet.columns:
                            max_length = 0
                            column = [cell for cell in column]
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                    
                    excel_bytes = output.getvalue()
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Download Quotation Excel",
                        data=excel_bytes,
                        file_name=f"Quotation_{selected_quotation}_{quotation_details['customer_name'].replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("Quotation document generated successfully!")
                
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