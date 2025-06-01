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
        
        st.dataframe(
            formatted_df,
            use_container_width=True,
            hide_index=True,
            height=600
        )
        
        # Show pagination info
        if total_pages > 1:
            st.caption(f"Showing page {page} of {total_pages} ({len(page_data)} of {len(filtered_data)} results)")

if __name__ == "__main__":
    main()
