import streamlit as st
import pandas as pd
import io
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
            if st.button("Clear Database", type="secondary"):
                if st.session_state.get('confirm_clear', False):
                    db.clear_database()
                    st.success("Database cleared successfully!")
                    st.session_state['confirm_clear'] = False
                    st.rerun()
                else:
                    st.session_state['confirm_clear'] = True
                    st.warning("Click again to confirm clearing the database")
    
    # Main content area
    if db.get_total_records() == 0:
        st.info("👆 Please upload an Excel file using the sidebar to get started.")
        
        # Show manual data entry form when no data exists
        st.subheader("Or add data manually:")
        with st.form("manual_data_entry"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sl_no = st.number_input("SL.NO", min_value=1, value=1)
                module = st.text_input("Module")
                body_colour = st.text_input("Body Colour")
            
            with col2:
                picture = st.text_input("Picture (filename)")
                single_colour = st.text_input("Single Colour Option")
                watt = st.number_input("Watt", min_value=0.0, step=0.1)
            
            with col3:
                size = st.number_input("Size", min_value=0.0, step=0.1)
                beam_angle = st.text_input("Beam Angle")
                cut_out = st.text_input("Cut Out")
            
            if st.form_submit_button("Add Product"):
                new_data = pd.DataFrame([{
                    'SL.NO': sl_no,
                    'MODULE': module,
                    'BODY COLOUR': body_colour,
                    'PICTURE': picture,
                    'SINGLE COLOUR OPTION': single_colour,
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
            if 'SINGLE COLOUR OPTION' in all_data.columns:
                single_colors = ['All'] + sorted([str(x) for x in all_data['SINGLE COLOUR OPTION'].dropna().unique().tolist()])
            else:
                single_colors = ['All']
            selected_single_color = st.selectbox("Single Colour Option", single_colors)
    
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
    if selected_single_color != 'All':
        filters['SINGLE COLOUR OPTION'] = selected_single_color
    
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
                new_sl_no = st.number_input("SL.NO", min_value=1, value=db.get_total_records() + 1)
                new_module = st.text_input("Module")
                new_body_colour = st.text_input("Body Colour")
            
            with col2:
                new_picture = st.text_input("Picture (filename)")
                new_single_colour = st.text_input("Single Colour Option")
                new_watt = st.number_input("Watt", min_value=0.0, step=0.1)
            
            with col3:
                new_size = st.number_input("Size", min_value=0.0, step=0.1)
                new_beam_angle = st.text_input("Beam Angle")
                new_cut_out = st.text_input("Cut Out")
            
            if st.form_submit_button("Add Product", type="primary"):
                new_data = pd.DataFrame([{
                    'SL.NO': new_sl_no,
                    'MODULE': new_module,
                    'BODY COLOUR': new_body_colour,
                    'PICTURE': new_picture,
                    'SINGLE COLOUR OPTION': new_single_colour,
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
                
                with st.form("edit_record"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        edit_sl_no = st.number_input("SL.NO", value=float(record_to_edit.get('SL.NO', 1)))
                        edit_module = st.text_input("Module", value=str(record_to_edit.get('MODULE', '')))
                        edit_body_colour = st.text_input("Body Colour", value=str(record_to_edit.get('BODY COLOUR', '')))
                    
                    with col2:
                        edit_picture = st.text_input("Picture", value=str(record_to_edit.get('PICTURE', '')))
                        edit_single_colour = st.text_input("Single Colour Option", value=str(record_to_edit.get('SINGLE COLOUR OPTION', '')))
                        edit_watt = st.number_input("Watt", value=float(record_to_edit.get('WATT', 0)))
                    
                    with col3:
                        edit_size = st.number_input("Size", value=float(record_to_edit.get('SIZE', 0)))
                        edit_beam_angle = st.text_input("Beam Angle", value=str(record_to_edit.get('BEAM ANGLE', '')))
                        edit_cut_out = st.text_input("Cut Out", value=str(record_to_edit.get('CUT OUT', '')))
                    
                    if st.form_submit_button("Update Record", type="primary"):
                        # Update the record in the database
                        updated_data = all_data.copy()
                        updated_data.iloc[selected_idx] = {
                            'SL.NO': edit_sl_no,
                            'MODULE': edit_module,
                            'BODY COLOUR': edit_body_colour,
                            'PICTURE': edit_picture,
                            'SINGLE COLOUR OPTION': edit_single_colour,
                            'WATT': edit_watt,
                            'SIZE': edit_size,
                            'BEAM ANGLE': edit_beam_angle,
                            'CUT OUT': edit_cut_out
                        }
                        
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

if __name__ == "__main__":
    main()
