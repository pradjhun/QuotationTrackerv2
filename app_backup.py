import streamlit as st
import pandas as pd
import io
import zipfile
import os
from database_manager import DatabaseManager
from utils import validate_excel_structure, format_dataframe_display

# Initialize database manager
@st.cache_resource
def init_database():
    return DatabaseManager()

def main():
    st.set_page_config(
        page_title="Quotation Management System",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize database
    db = init_database()
    
    st.title("📊 Quotation Management System")
    st.markdown("Upload Excel files and manage your product quotation database with powerful search capabilities.")
    
    # Sidebar for file upload and database info
    with st.sidebar:
        st.header("📁 File Upload")
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload your quotation Excel file to import data into the database"
        )
        
        if uploaded_file is not None:
            try:
                # Read the Excel file
                df = pd.read_excel(uploaded_file)
                
                # Validate structure
                is_valid, message = validate_excel_structure(df)
                
                if is_valid:
                    st.success("✅ File structure validated successfully!")
                    
                    if st.button("Import Data", type="primary"):
                        # Import data to database
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
        
        # Database statistics
        st.header("📈 Database Info")
        total_records = db.get_total_records()
        st.metric("Total Records", total_records)
        
        if total_records > 0:
            # Database backup section
            st.subheader("💾 Database Backup & Restore")
            
            backup_col1, backup_col2, backup_col3 = st.columns(3)
            with backup_col1:
                if st.button("📤 Backup", help="Download current database with images as ZIP"):
                    all_data = db.get_all_data()
                    if not all_data.empty:
                        try:
                            import zipfile
                            # Create backup ZIP file with data and images
                            zip_buffer = io.BytesIO()
                            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                            
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                # Add Excel data file
                                excel_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                    all_data.to_excel(writer, sheet_name='Database_Backup', index=False)
                                excel_buffer.seek(0)
                                zip_file.writestr(f"database_backup_{timestamp}.xlsx", excel_buffer.getvalue())
                                
                                # Add images if they exist
                                if 'uploaded_images' in st.session_state and st.session_state.uploaded_images:
                                    for img_name, img_data in st.session_state.uploaded_images.items():
                                        zip_file.writestr(f"images/{img_name}", img_data)
                                    
                                    # Create a readme file
                                    readme_content = f"""Database Backup - {timestamp}
                                    
This backup contains:
1. database_backup_{timestamp}.xlsx - Your quotation data
2. images/ folder - All uploaded product images

To restore:
1. Upload the Excel file to import your data
2. Upload the images from the images folder to restore pictures
"""
                                    zip_file.writestr("README.txt", readme_content)
                            
                            zip_buffer.seek(0)
                            
                            st.download_button(
                                label="Download Backup (ZIP)",
                                data=zip_buffer.getvalue(),
                                file_name=f"database_backup_{timestamp}.zip",
                                mime="application/zip"
                            )
                            
                            image_count = len(st.session_state.get('uploaded_images', {}))
                            image_names = list(st.session_state.get('uploaded_images', {}).keys())
                            st.success(f"Backup ready! Includes {len(all_data)} records and {image_count} images")
                            if image_names:
                                st.info(f"Images included: {', '.join(image_names)}")
                            else:
                                st.warning("No images found in session. Upload images using the sidebar to include them in backups.")
                        except Exception as e:
                            st.error(f"Error creating backup: {str(e)}")
                    else:
                        st.warning("No data to backup")
            
            with backup_col2:
                if st.button("📥 Restore", help="Restore database from backup file"):
                    st.session_state.show_restore = True
                    
            with backup_col3:
                if st.button("🗑️ Clear All", type="secondary"):
                    if st.session_state.get('confirm_clear', False):
                        db.clear_database()
                        if 'uploaded_images' in st.session_state:
                            st.session_state.uploaded_images = {}
                        st.success("Database cleared successfully!")
                        st.session_state['confirm_clear'] = False
                        st.rerun()
                    else:
                        st.session_state['confirm_clear'] = True
                        st.warning("Click again to confirm clearing all data")
                        
        # Restore section
        if st.session_state.get('show_restore', False):
            st.subheader("📥 Restore Database")
            
            restore_tab1, restore_tab2 = st.tabs(["📄 From Excel File", "📦 From ZIP Backup"])
            
            with restore_tab1:
                st.info("Upload an Excel file to restore data only (without images)")
                restore_file = st.file_uploader(
                    "Choose Excel backup file", 
                    type=['xlsx', 'xls'],
                    key="restore_excel"
                )
                
                if restore_file is not None:
                    try:
                        df = pd.read_excel(restore_file)
                        
                        # Validate structure
                        is_valid, message = validate_excel_structure(df)
                        if is_valid:
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔄 Replace All Data", key="replace_data"):
                                    db.clear_database()
                                    success, msg = db.import_data(df)
                                    if success:
                                        st.success(f"✅ Database restored! {msg}")
                                        st.session_state.show_restore = False
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {msg}")
                                        
                            with col2:
                                if st.button("➕ Add to Existing Data", key="add_data"):
                                    success, msg = db.import_data(df)
                                    if success:
                                        st.success(f"✅ Data added! {msg}")
                                        st.session_state.show_restore = False
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {msg}")
                                        
                            st.dataframe(df.head(), use_container_width=True)
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"❌ Error reading file: {str(e)}")
            
            with restore_tab2:
                st.info("Upload a ZIP backup file to restore both data and images")
                zip_file = st.file_uploader(
                    "Choose ZIP backup file", 
                    type=['zip'],
                    key="restore_zip"
                )
                
                if zip_file is not None:
                    try:
                        import zipfile
                        from io import BytesIO
                        
                        with zipfile.ZipFile(BytesIO(zip_file.read())) as zip_ref:
                            # List contents
                            file_list = zip_ref.namelist()
                            st.write("📁 Backup contents:")
                            for file in file_list:
                                st.write(f"  - {file}")
                            
                            # Find Excel file
                            excel_files = [f for f in file_list if f.endswith(('.xlsx', '.xls'))]
                            if excel_files:
                                excel_file = excel_files[0]
                                
                                # Read Excel data
                                with zip_ref.open(excel_file) as excel_data:
                                    df = pd.read_excel(excel_data)
                                
                                # Validate structure
                                is_valid, message = validate_excel_structure(df)
                                if is_valid:
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("🔄 Replace All Data", key="replace_zip_data"):
                                            db.clear_database()
                                            success, msg = db.import_data(df)
                                            if success:
                                                # Extract images
                                                image_files = [f for f in file_list if f.startswith('images/') and f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))]
                                                if image_files:
                                                    if 'uploaded_images' not in st.session_state:
                                                        st.session_state.uploaded_images = {}
                                                    
                                                    for img_file in image_files:
                                                        with zip_ref.open(img_file) as img_data:
                                                            img_name = os.path.basename(img_file)
                                                            img_content = img_data.read()
                                                            st.session_state.uploaded_images[img_name] = img_content
                                                    
                                                    st.success(f"✅ Database and {len(image_files)} images restored! {msg}")
                                                else:
                                                    st.success(f"✅ Database restored! {msg}")
                                                st.session_state.show_restore = False
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {msg}")
                                    
                                    with col2:
                                        if st.button("➕ Add to Existing Data", key="add_zip_data"):
                                            success, msg = db.import_data(df)
                                            if success:
                                                # Extract images
                                                image_files = [f for f in file_list if f.startswith('images/') and f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))]
                                                if image_files:
                                                    if 'uploaded_images' not in st.session_state:
                                                        st.session_state.uploaded_images = {}
                                                    
                                                    added_images = 0
                                                    for img_file in image_files:
                                                        with zip_ref.open(img_file) as img_data:
                                                            img_name = os.path.basename(img_file)
                                                            if img_name not in st.session_state.uploaded_images:
                                                                img_content = img_data.read()
                                                                st.session_state.uploaded_images[img_name] = img_content
                                                                added_images += 1
                                                    
                                                    st.success(f"✅ Data and {added_images} new images added! {msg}")
                                                else:
                                                    st.success(f"✅ Data added! {msg}")
                                                st.session_state.show_restore = False
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {msg}")
                                    
                                    st.dataframe(df.head(), use_container_width=True)
                                else:
                                    st.error(f"❌ {message}")
                            else:
                                st.error("❌ No Excel file found in backup")
                    except Exception as e:
                        st.error(f"❌ Error processing ZIP file: {str(e)}")
            
            if st.button("❌ Cancel Restore"):
                st.session_state.show_restore = False
                st.rerun()
    
    # Main content area
    if db.get_total_records() == 0:
        st.info("👆 Please upload an Excel file using the sidebar to get started.")
        
        # Show manual data entry form when no data exists
        st.subheader("Or add data manually:")
        with st.form("manual_data_entry"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sl_no = st.number_input("SL.NO", min_value=1, value=1, key="add_sl_no")
                module = st.text_input("Model")
                body_colour = st.text_input("Body Colour")
            
            with col2:
                # Picture upload
                uploaded_picture = st.file_uploader("Upload Picture", type=['png', 'jpg', 'jpeg', 'gif'], key="manual_picture")
                picture_filename = ""
                if uploaded_picture:
                    picture_filename = uploaded_picture.name
                    # Store in session state
                    if 'uploaded_images' not in st.session_state:
                        st.session_state.uploaded_images = {}
                    st.session_state.uploaded_images[uploaded_picture.name] = uploaded_picture.getvalue()
                    st.success(f"Picture uploaded: {uploaded_picture.name}")
                
                price = st.text_input("Price")
                watt = st.text_input("Watt")
            
            with col3:
                size = st.text_input("Size")
                beam_angle = st.text_input("Beam Angle")
                cut_out = st.text_input("Cut Out")
            
            if st.form_submit_button("Add Product"):
                new_data = pd.DataFrame([{
                    'SL.NO': sl_no,
                    'MODULE': module,
                    'BODY COLOUR': body_colour,
                    'PICTURE': picture_filename,
                    'PRICE': price,
                    'WATT': watt,
                    'SIZE': size,
                    'BEAM ANGLE': beam_angle,
                    'CUT OUT': cut_out
                }])
                
                success, message = db.import_data(new_data)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        return
    
    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["🔍 Browse Products", "📋 Create Quotation", "📄 View Quotations"])
    
    with tab1:
        # Search and filter section
        st.header("🔍 Search & Filter")
        
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
            
            # Get unique values for filter dropdowns
            all_data = db.get_all_data()
            
            with filter_cols[0]:
            if 'MODULE' in all_data.columns:
                modules = ['All'] + sorted([str(x) for x in all_data['MODULE'].dropna().unique().tolist()])
            else:
                modules = ['All']
            selected_module = st.selectbox("Module", modules)
        
        with filter_cols[1]:
            if 'BODY COLOUR' in all_data.columns:
                colors = ['All'] + sorted([str(x) for x in all_data['BODY COLOUR'].dropna().unique().tolist()])
            else:
                colors = ['All']
            selected_color = st.selectbox("Body Colour", colors)
        
        with filter_cols[2]:
            if 'WATT' in all_data.columns:
                watts = ['All'] + sorted([str(x) for x in all_data['WATT'].dropna().unique().tolist()])
            else:
                watts = ['All']
            selected_watt = st.selectbox("Watt", watts)
        
        # Additional filters
        filter_cols2 = st.columns(3)
        
        with filter_cols2[0]:
            if 'SIZE' in all_data.columns:
                sizes = ['All'] + sorted([str(x) for x in all_data['SIZE'].dropna().unique().tolist()])
            else:
                sizes = ['All']
            selected_size = st.selectbox("Size", sizes)
        
        with filter_cols2[1]:
            if 'BEAM ANGLE' in all_data.columns:
                beam_angles = ['All'] + sorted([str(x) for x in all_data['BEAM ANGLE'].dropna().unique().tolist()])
            else:
                beam_angles = ['All']
            selected_beam_angle = st.selectbox("Beam Angle", beam_angles)
        
        with filter_cols2[2]:
            if 'PRICE' in all_data.columns:
                prices = ['All'] + sorted([str(x) for x in all_data['PRICE'].dropna().unique().tolist()])
            else:
                prices = ['All']
            selected_price = st.selectbox("Price", prices)
    
    # Build filters dictionary
    filters = {}
    if selected_module != 'All':
        filters['MODULE'] = selected_module
    if selected_color != 'All':
        filters['BODY COLOUR'] = selected_color
    if selected_watt != 'All':
        filters['WATT'] = selected_watt
    if selected_size != 'All':
        filters['SIZE'] = selected_size
    if selected_beam_angle != 'All':
        filters['BEAM ANGLE'] = selected_beam_angle
    if selected_price != 'All':
        filters['PRICE'] = selected_price
    
    # Get filtered data
    if search_term or filters:
        filtered_data = db.search_data(search_term, filters)
    else:
        filtered_data = db.get_all_data()
    
    # Display results
    st.header("📋 Results")
    
    if filtered_data.empty:
        st.warning("No results found matching your search criteria.")
    else:
        # Results summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Results Found", len(filtered_data))
        with col2:
            st.metric("Total Records", db.get_total_records())
        with col3:
            export_button = st.button("📥 Export Results", type="secondary")
        
        # Export functionality
        if export_button:
            try:
                # Create Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered_data.to_excel(writer, sheet_name='Quotation_Results', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="Download Excel File",
                    data=output.getvalue(),
                    file_name=f"quotation_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error creating Excel file: {str(e)}")
        
        # Display data in pages
        items_per_page = 25
        total_pages = (len(filtered_data) - 1) // items_per_page + 1
        
        if total_pages > 1:
            page = st.selectbox("Page", range(1, total_pages + 1))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_data = filtered_data.iloc[start_idx:end_idx]
        else:
            page = 1
            page_data = filtered_data
        
        # Format and display the dataframe
        formatted_df = format_dataframe_display(page_data)
        
        # Add image upload section
        with st.expander("📸 Upload Product Images (Optional)"):
            st.markdown("""
            **How to add images:**
            1. Look at the PICTURE column in your data
            2. Upload image files with matching names
            3. For example: if PICTURE column shows "product1.jpg", upload a file named "product1.jpg"
            """)
            
            # Show what image names we're looking for
            if 'PICTURE' in formatted_df.columns:
                picture_names = formatted_df['PICTURE'].dropna().unique()
                if len(picture_names) > 0:
                    st.write("**Image names found in your data:**")
                    for name in picture_names[:10]:  # Show first 10
                        if str(name) not in ['', 'nan', 'None']:
                            st.write(f"• {name}")
                    if len(picture_names) > 10:
                        st.write(f"... and {len(picture_names) - 10} more")
            
            uploaded_images = st.file_uploader(
                "Choose image files",
                type=['png', 'jpg', 'jpeg', 'gif'],
                accept_multiple_files=True,
                help="Upload images that match the names shown above"
            )
            
            # Store uploaded images in session state
            if uploaded_images:
                if 'uploaded_images' not in st.session_state:
                    st.session_state.uploaded_images = {}
                
                for uploaded_file in uploaded_images:
                    st.session_state.uploaded_images[uploaded_file.name] = uploaded_file.getvalue()
                
                st.success(f"Uploaded {len(uploaded_images)} images successfully!")
                
                # Show which images were uploaded
                st.write("**Uploaded images:**")
                for img_name in st.session_state.uploaded_images.keys():
                    st.write(f"✓ {img_name}")
        
        # Check if we should show image gallery view
        show_gallery = ('uploaded_images' in st.session_state and 
                       len(st.session_state.uploaded_images) > 0 and 
                       'PICTURE' in formatted_df.columns)
        
        if show_gallery:
            # Toggle between gallery and table view
            view_mode = st.radio("View Mode:", ["Gallery View", "Table View"], horizontal=True)
            
            if view_mode == "Gallery View":
                st.subheader("📸 Product Gallery")
                
                # Display data with images
                for idx, row in formatted_df.iterrows():
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            picture_name = str(row.get('PICTURE', ''))
                            if picture_name and picture_name not in ['', 'nan', 'None']:
                                # Try to find matching image
                                image_found = False
                                # Try exact match first
                                if picture_name in st.session_state.uploaded_images:
                                    st.image(st.session_state.uploaded_images[picture_name], width=150)
                                    image_found = True
                                else:
                                    # Try partial match
                                    base_name = picture_name.split('.')[0] if '.' in picture_name else picture_name
                                    for img_name in st.session_state.uploaded_images.keys():
                                        if base_name.lower() in img_name.lower() or img_name.split('.')[0].lower() == base_name.lower():
                                            st.image(st.session_state.uploaded_images[img_name], width=150)
                                            image_found = True
                                            break
                                
                                if not image_found:
                                    st.write("🖼️ Image not found")
                                    st.caption(f"Looking for: {picture_name}")
                            else:
                                st.write("📷 No image")
                        
                        with col2:
                            # Display other product details
                            st.write("**Product Details:**")
                            for col_name, value in row.items():
                                if col_name != 'PICTURE' and pd.notna(value) and str(value) not in ['', 'nan', 'None']:
                                    st.write(f"**{col_name}:** {value}")
                        
                        st.divider()
            else:
                # Regular table display
                st.dataframe(
                    formatted_df,
                    use_container_width=True,
                    hide_index=True,
                    height=600
                )
        else:
            # Show regular table when no images are uploaded
            st.dataframe(
                formatted_df,
                use_container_width=True,
                hide_index=True,
                height=600
            )
        
        # Show pagination info
        if total_pages > 1:
            st.caption(f"Showing page {page} of {total_pages} ({len(page_data)} of {len(filtered_data)} results)")
    
    # Data management section
    st.header("📝 Data Management")
    
    # Tabs for different data operations
    tab1, tab2, tab3 = st.tabs(["Add New Record", "Edit Existing Record", "Delete Records"])
    
    with tab1:
        st.subheader("Add New Product")
        with st.form("add_new_record"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_sl_no = st.number_input("SL.NO", min_value=1, value=db.get_total_records() + 1, key="new_sl_no")
                new_module = st.text_input("Model")
                new_body_colour = st.text_input("Body Colour")
            
            with col2:
                # Picture upload for new record with preview
                new_uploaded_picture = st.file_uploader("Upload Picture", type=['png', 'jpg', 'jpeg', 'gif'], key="add_new_picture")
                new_picture_filename = ""
                if new_uploaded_picture:
                    new_picture_filename = new_uploaded_picture.name
                    # Store in session state
                    if 'uploaded_images' not in st.session_state:
                        st.session_state.uploaded_images = {}
                    st.session_state.uploaded_images[new_uploaded_picture.name] = new_uploaded_picture.getvalue()
                    st.success(f"Picture uploaded: {new_uploaded_picture.name}")
                    # Show preview of uploaded image
                    st.image(new_uploaded_picture, caption=f"Preview: {new_uploaded_picture.name}", width=150)
                
                new_price = st.text_input("Price")
                new_watt = st.text_input("Watt")
            
            with col3:
                new_size = st.text_input("Size")
                new_beam_angle = st.text_input("Beam Angle")
                new_cut_out = st.text_input("Cut Out")
            
            if st.form_submit_button("Add Product", type="primary"):
                new_data = pd.DataFrame([{
                    'SL.NO': new_sl_no,
                    'MODULE': new_module,
                    'BODY COLOUR': new_body_colour,
                    'PICTURE': new_picture_filename,
                    'PRICE': new_price,
                    'WATT': new_watt,
                    'SIZE': new_size,
                    'BEAM ANGLE': new_beam_angle,
                    'CUT OUT': new_cut_out
                }])
                
                success, message = db.import_data(new_data)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    with tab2:
        st.subheader("Edit Existing Record")
        
        if db.get_total_records() > 0:
            all_data = db.get_all_data()
            
            # Select record to edit
            record_options = []
            for idx, row in all_data.iterrows():
                sl_no = row.get('SL.NO', idx)
                module = row.get('MODULE', 'Unknown')
                record_options.append(f"SL.NO {sl_no}: {module}")
            
            selected_record = st.selectbox("Select record to edit:", record_options)
            
            if selected_record:
                # Get the selected record index
                selected_idx = record_options.index(selected_record)
                record_to_edit = all_data.iloc[selected_idx]
                
                st.write("**Current values:**")
                st.write(record_to_edit.to_dict())
                
                # Initialize session state for form values if not exists
                if f'edit_form_{selected_idx}' not in st.session_state:
                    # Better data cleaning function
                    def clean_value(value):
                        if pd.isna(value) or value is None:
                            return ''
                        str_val = str(value)
                        if str_val.lower() in ['nan', 'none', 'null', '']:
                            return ''
                        return str_val.strip()
                    
                    st.session_state[f'edit_form_{selected_idx}'] = {
                        'sl_no': float(record_to_edit.get('SL.NO', 1)),
                        'module': clean_value(record_to_edit.get('MODEL')),  # Fixed: MODEL not MODULE
                        'body_colour': clean_value(record_to_edit.get('BODY CLOLOR')),  # Fixed: BODY CLOLOR not BODY COLOUR
                        'price': clean_value(record_to_edit.get('PRICE')),
                        'watt': clean_value(record_to_edit.get('WATT')),
                        'size': clean_value(record_to_edit.get('SIZE')),
                        'beam_angle': clean_value(record_to_edit.get('BEAM ANGLE')),
                        'cut_out': clean_value(record_to_edit.get('CUT OUT'))
                    }
                
                with st.form("edit_record"):
                    col1, col2, col3 = st.columns(3)
                    
                    form_data = st.session_state[f'edit_form_{selected_idx}']
                    
                    # Debug output to see what values we're working with
                    st.write("**Debug - Raw values from DataFrame:**")
                    st.write(f"Raw MODEL: {repr(record_to_edit.get('MODEL'))}")
                    st.write(f"Raw BODY CLOLOR: {repr(record_to_edit.get('BODY CLOLOR'))}")
                    st.write(f"Raw PRICE: {repr(record_to_edit.get('PRICE'))}")
                    
                    st.write("**Debug - Cleaned values being loaded into form:**")
                    st.write(f"Model: '{form_data['module']}'")
                    st.write(f"Body Colour: '{form_data['body_colour']}'")
                    st.write(f"Price: '{form_data['price']}'")
                    
                    # Also show all available columns
                    st.write("**Available columns in data:**")
                    st.write(list(record_to_edit.index))
                    
                    with col1:
                        edit_sl_no = st.number_input("SL.NO", value=form_data['sl_no'])
                        edit_module = st.text_input("Model", value=form_data['module'])
                        edit_body_colour = st.text_input("Body Colour", value=form_data['body_colour'])
                    
                    with col2:
                        # Picture upload for edit with preview
                        current_picture = str(record_to_edit.get('PICTURE', ''))
                        st.write(f"**Current Picture:** {current_picture}")
                        
                        # Show current image preview if available
                        if current_picture and current_picture not in ['', 'nan', 'None']:
                            if 'uploaded_images' in st.session_state and current_picture in st.session_state.uploaded_images:
                                st.image(st.session_state.uploaded_images[current_picture], 
                                        caption=f"Current: {current_picture}", 
                                        width=150)
                            else:
                                # Try partial match for current image
                                image_found = False
                                if 'uploaded_images' in st.session_state:
                                    base_name = current_picture.split('.')[0] if '.' in current_picture else current_picture
                                    for img_name in st.session_state.uploaded_images.keys():
                                        if base_name.lower() in img_name.lower() or img_name.split('.')[0].lower() == base_name.lower():
                                            st.image(st.session_state.uploaded_images[img_name], 
                                                    caption=f"Current: {img_name}", 
                                                    width=150)
                                            image_found = True
                                            break
                                
                                if not image_found:
                                    st.info("Current image not available in preview")
                        else:
                            st.info("No current image")
                        
                        edit_uploaded_picture = st.file_uploader("Upload New Picture (optional)", type=['png', 'jpg', 'jpeg', 'gif'], key="edit_picture")
                        edit_picture_filename = current_picture
                        if edit_uploaded_picture:
                            edit_picture_filename = edit_uploaded_picture.name
                            # Store in session state
                            if 'uploaded_images' not in st.session_state:
                                st.session_state.uploaded_images = {}
                            st.session_state.uploaded_images[edit_uploaded_picture.name] = edit_uploaded_picture.getvalue()
                            st.success(f"New picture uploaded: {edit_uploaded_picture.name}")
                            # Show preview of new image
                            st.image(edit_uploaded_picture, caption=f"New: {edit_uploaded_picture.name}", width=150)
                        
                        edit_price = st.text_input("Price", value=form_data['price'])
                        edit_watt = st.text_input("Watt", value=form_data['watt'])
                    
                    with col3:
                        edit_size = st.text_input("Size", value=form_data['size'])
                        edit_beam_angle = st.text_input("Beam Angle", value=form_data['beam_angle'])
                        edit_cut_out = st.text_input("Cut Out", value=form_data['cut_out'])
                    
                    if st.form_submit_button("Update Record", type="primary"):
                        # Validate that edit_module has a value
                        if not edit_module or edit_module.strip() == "":
                            st.error("Model field cannot be empty. Please enter a model name.")
                        else:
                            # Debug: Show what values are being captured
                            st.write("**Values being saved:**")
                            st.write(f"Model: '{edit_module}'")
                            st.write(f"SL.NO: '{edit_sl_no}'")
                            
                            # Update the record in the database
                            updated_data = all_data.copy()
                            # Convert values to appropriate types to avoid dtype warnings
                            update_values = {
                                'SL.NO': edit_sl_no,  # Keep as number
                                'MODEL': str(edit_module),  # Fixed column name
                                'BODY CLOLOR': str(edit_body_colour),  # Fixed column name
                                'PICTURE': str(edit_picture_filename),
                                'PRICE': edit_price,  # Keep original type
                                'WATT': str(edit_watt),
                                'SIZE': str(edit_size),
                                'BEAM ANGLE': str(edit_beam_angle),
                                'CUT OUT': str(edit_cut_out)
                            }
                            
                            # Update each column individually with proper type conversion
                            for col, value in update_values.items():
                                if col in updated_data.columns:
                                    # Convert to the same dtype as the existing column
                                    original_dtype = updated_data[col].dtype
                                    if original_dtype in ['int64', 'int32']:
                                        try:
                                            converted_value = int(float(str(value))) if str(value) else 0
                                        except:
                                            converted_value = str(value)
                                    elif original_dtype in ['float64', 'float32']:
                                        try:
                                            converted_value = float(str(value)) if str(value) else 0.0
                                        except:
                                            converted_value = str(value)
                                    else:
                                        converted_value = str(value)
                                    
                                    updated_data.at[updated_data.index[selected_idx], col] = converted_value
                            
                            # Clear and reimport updated data
                            db.clear_database()
                            success, message = db.import_data(updated_data)
                            if success:
                                st.success("Record updated successfully!")
                                st.rerun()
                            else:
                                st.error(f"Error updating record: {message}")
        else:
            st.info("No records available to edit.")
    
    with tab3:
        st.subheader("Delete Records")
        
        if db.get_total_records() > 0:
            all_data = db.get_all_data()
            
            # Multi-select for records to delete
            record_options = []
            for idx, row in all_data.iterrows():
                sl_no = row.get('SL.NO', idx)
                module = row.get('MODULE', 'Unknown')
                record_options.append(f"SL.NO {sl_no}: {module}")
            
            records_to_delete = st.multiselect("Select records to delete:", record_options)
            
            if records_to_delete:
                st.warning(f"You are about to delete {len(records_to_delete)} record(s):")
                for record in records_to_delete:
                    st.write(f"- {record}")
                
                if st.button("Delete Selected Records", type="secondary"):
                    # Get indices of records to delete
                    indices_to_delete = [record_options.index(record) for record in records_to_delete]
                    
                    # Create new dataframe without deleted records
                    remaining_data = all_data.drop(all_data.index[indices_to_delete]).reset_index(drop=True)
                    
                    # Update SL.NO to be sequential
                    if 'SL.NO' in remaining_data.columns:
                        remaining_data['SL.NO'] = range(1, len(remaining_data) + 1)
                    
                    # Clear and reimport remaining data
                    db.clear_database()
                    if not remaining_data.empty:
                        success, message = db.import_data(remaining_data)
                        if success:
                            st.success(f"Deleted {len(records_to_delete)} record(s) successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error updating database: {message}")
                    else:
                        st.success("All records deleted. Database is now empty.")
                        st.rerun()
        else:
            st.info("No records available to delete.")
    
    with tab2:
        # Quotation Creation Tab
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
            if st.button("🔍 Search"):
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
                            if picture and 'uploaded_images' in st.session_state and picture in st.session_state.uploaded_images:
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
        
        # Display current quotation
        if st.session_state.quotation_items:
            st.subheader("Current Quotation Items")
            
            quotation_df = pd.DataFrame(st.session_state.quotation_items)
            
            # Display quotation items with remove option
            for i, item in enumerate(st.session_state.quotation_items):
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{item['model']}** - {item['body_color']}")
                        st.write(f"Light Color: {item['light_color']}")
                    
                    with col2:
                        st.write(f"Qty: {item['quantity']}")
                        st.write(f"Price: ₹{item['price']:,.2f}")
                    
                    with col3:
                        st.write(f"Discount: {item['discount']}%")
                        st.write(f"Total: ₹{item['item_total']:,.2f}")
                    
                    with col4:
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
        # View Quotations Tab
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
                        st.dataframe(quotation_items[['model', 'body_color', 'light_color', 'quantity', 'price', 'discount', 'item_total']], 
                                   use_container_width=True)
        else:
            st.info("No quotations found. Create your first quotation in the 'Create Quotation' tab.")

if __name__ == "__main__":
    main()
