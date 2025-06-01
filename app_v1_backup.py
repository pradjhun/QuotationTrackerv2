import streamlit as st
import pandas as pd
import os
from io import BytesIO
from database_manager import DatabaseManager
from utils import validate_excel_structure, format_dataframe_display, export_to_excel, clean_search_term


def init_database():
    """Initialize the database if it doesn't exist."""
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseManager()

def main():
    st.set_page_config(
        page_title="Quotation Management System",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database
    init_database()
    db = st.session_state.db
    
    # Initialize session state for quotation items
    if 'quotation_items' not in st.session_state:
        st.session_state.quotation_items = []
    
    st.title("📊 Quotation Management System")
    st.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Browse Products", 
        "➕ Add Product", 
        "✏️ Edit Product",
        "💼 Create Quotation", 
        "📄 View Quotations", 
        "⬇️ Download Quotations"
    ])
    
    with tab1:
        st.header("📋 Browse Products Database")
        
        # Upload section
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
                    st.subheader("📊 Preview Data")
                    st.dataframe(format_dataframe_display(df), use_container_width=True)
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        if st.button("💾 Import Data", type="primary"):
                            success, import_message = db.import_data(df)
                            if success:
                                st.success(import_message)
                                st.rerun()
                            else:
                                st.error(import_message)
                    
                    with col2:
                        if st.button("🗑️ Clear Database", type="secondary"):
                            if st.session_state.get('confirm_clear', False):
                                db.clear_database()
                                st.success("Database cleared successfully!")
                                st.session_state.confirm_clear = False
                                st.rerun()
                            else:
                                st.session_state.confirm_clear = True
                                st.warning("Click again to confirm clearing all data!")
                    
                    with col3:
                        if not st.session_state.get('confirm_clear', False):
                            st.session_state.confirm_clear = False
                
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        # Display current data
        st.subheader("🔍 Search and Filter Products")
        
        # Search and filter controls
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_term = st.text_input("🔎 Search products", placeholder="Enter model, color, watt, or size...")
        
        with col2:
            if st.button("🔍 Search Products", key="browse_search_btn"):
                st.rerun()
        
        # Filter options
        all_data = db.get_all_data()
        if not all_data.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                unique_colors = ['All'] + list(all_data['BODY CLOLOR'].dropna().unique())
                color_filter = st.selectbox("Filter by Body Color", unique_colors)
            
            with col2:
                unique_watts = ['All'] + list(all_data['WATT'].dropna().unique())
                watt_filter = st.selectbox("Filter by Watt", unique_watts)
            
            with col3:
                unique_sizes = ['All'] + list(all_data['SIZE'].dropna().unique())
                size_filter = st.selectbox("Filter by Size", unique_sizes)
            
            # Apply filters
            filters = {}
            if color_filter != 'All':
                filters['BODY CLOLOR'] = color_filter
            if watt_filter != 'All':
                filters['WATT'] = watt_filter
            if size_filter != 'All':
                filters['SIZE'] = size_filter
            
            # Get filtered data
            if search_term or filters:
                filtered_data = db.search_data(clean_search_term(search_term), filters)
            else:
                filtered_data = all_data
            
            # Display results
            if not filtered_data.empty:
                st.subheader(f"📊 Products Found: {len(filtered_data)}")
                
                # Format for display
                display_df = format_dataframe_display(filtered_data)
                st.dataframe(display_df, use_container_width=True)
                
                # Export option
                if st.button("📥 Export to Excel"):
                    excel_data = export_to_excel(display_df)
                    st.download_button(
                        label="💾 Download Excel File",
                        data=excel_data,
                        file_name="products_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("No products found matching your criteria.")
        else:
            st.info("No products in database. Please import data first.")
        
        # Database statistics
        if not all_data.empty:
            st.subheader("📈 Database Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Products", len(all_data))
            
            with col2:
                st.metric("Unique Models", all_data['MODEL'].nunique())
            
            with col3:
                st.metric("Body Colors", all_data['BODY CLOLOR'].nunique())
            
            with col4:
                avg_price = all_data['PRICE'].astype(str).str.replace(',', '').astype(float).mean()
                st.metric("Avg Price", f"₹{avg_price:,.2f}")
    
    with tab2:
        st.header("➕ Add New Product")
        
        with st.form("add_product_form"):
            st.subheader("Product Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                model = st.text_input("Model*", placeholder="Enter product model")
                body_color = st.text_input("Body Color", placeholder="Enter body color")
                price = st.number_input("Price*", min_value=0.0, step=0.01, format="%.2f")
                watt = st.text_input("Watt", placeholder="Enter wattage")
            
            with col2:
                size = st.text_input("Size", placeholder="Enter size")
                beam_angle = st.text_input("Beam Angle", placeholder="Enter beam angle")
                cut_out = st.text_input("Cut Out", placeholder="Enter cut out")
                picture = st.text_input("Picture", placeholder="Enter picture filename")
            
            submitted = st.form_submit_button("➕ Add Product", type="primary")
            
            if submitted:
                if model and price > 0:
                    # Add product to database using the existing structure
                    new_product = pd.DataFrame([{
                        'MODEL': model,
                        'BODY CLOLOR': body_color,
                        'PICTURE': picture,
                        'PRICE': price,
                        'WATT': watt,
                        'SIZE': size,
                        'BEAM ANGLE': beam_angle,
                        'CUT OUT': cut_out
                    }])
                    
                    success, message = db.import_data(new_product)
                    if success:
                        st.success(f"Product '{model}' added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error adding product: {message}")
                else:
                    st.error("Please fill in all required fields (Model and Price).")
    
    with tab3:
        st.header("✏️ Edit Product")
        
        # Get all products for editing
        all_products = db.get_all_data()
        
        if not all_products.empty:
            # Product selection
            st.subheader("Select Product to Edit")
            
            # Create a more readable display for selection
            product_options = []
            for idx, row in all_products.iterrows():
                price_str = f"₹{float(row['PRICE']):,.2f}" if row['PRICE'] else "N/A"
                option = f"{row['MODEL']} - {row.get('BODY CLOLOR', 'N/A')} - {price_str}"
                product_options.append(option)
            
            selected_option = st.selectbox("Choose a product to edit:", product_options)
            
            if selected_option:
                # Get the selected product index
                selected_idx = product_options.index(selected_option)
                selected_product = all_products.iloc[selected_idx]
                
                st.subheader("Edit Product Details")
                
                with st.form("edit_product_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        model = st.text_input("Model*", value=str(selected_product['MODEL']))
                        body_color = st.text_input("Body Color", value=str(selected_product.get('BODY CLOLOR', '')))
                        price = st.number_input("Price*", min_value=0.0, step=0.01, format="%.2f", 
                                              value=float(selected_product['PRICE']) if selected_product['PRICE'] else 0.0)
                        watt = st.text_input("Watt", value=str(selected_product.get('WATT', '')))
                    
                    with col2:
                        size = st.text_input("Size", value=str(selected_product.get('SIZE', '')))
                        beam_angle = st.text_input("Beam Angle", value=str(selected_product.get('BEAM ANGLE', '')))
                        cut_out = st.text_input("Cut Out", value=str(selected_product.get('CUT OUT', '')))
                        picture = st.text_input("Picture", value=str(selected_product.get('PICTURE', '')))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_submitted = st.form_submit_button("💾 Update Product", type="primary")
                    
                    with col2:
                        delete_submitted = st.form_submit_button("🗑️ Delete Product", type="secondary")
                    
                    if update_submitted:
                        if model and price > 0:
                            # Update product in database
                            # Since we're using the existing database structure, we need to work with the current data
                            st.warning("Product update functionality requires database schema updates. Please delete and re-add the product for now.")
                        else:
                            st.error("Please fill in all required fields (Model and Price).")
                    
                    if delete_submitted:
                        st.warning("Product deletion functionality requires database schema updates. Please use the Clear Database option in Browse Products tab for now.")
        else:
            st.info("No products available for editing. Please add products first.")
    
    with tab4:
        st.header("💼 Create Quotation")
        
        # Customer information
        st.subheader("👤 Customer Information")
        customer_name = st.text_input("Customer Name*", placeholder="Enter customer name")
        
        if customer_name:
            # Product selection for quotation
            st.subheader("🛍️ Add Products to Quotation")
            
            # Search for products
            col1, col2 = st.columns([3, 1])
            
            with col1:
                product_search = st.text_input("🔎 Search products for quotation", placeholder="Enter model, color, watt, or size...")
            
            with col2:
                if st.button("🔍 Search Products", key="create_quotation_search_btn"):
                    st.rerun()
            
            # Get products based on search
            all_products = db.get_all_data()
            
            if not all_products.empty:
                if product_search:
                    filtered_products = db.search_data(clean_search_term(product_search))
                else:
                    filtered_products = all_products.head(10)  # Show first 10 products
                
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
                with st.expander(f"📦 {item['model']} - Qty: {item['quantity']}"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Model:** {item['model']}")
                        st.write(f"**Body Color:** {item['body_color']}")
                        st.write(f"**Light Color:** {item['light_color']}")
                        st.write(f"**Unit Price:** ₹{item['price']:,.2f}")
                    
                    with col2:
                        st.write(f"**Quantity:** {item['quantity']}")
                        st.write(f"**Discount:** {item['discount']}%")
                        st.write(f"**Item Total:** ₹{item['item_total']:,.2f}")
                    
                    with col3:
                        if st.button(f"🗑️ Remove", key=f"remove_{i}"):
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
                    st.info("Add products to create a quotation.")
    
    with tab5:
        st.header("📄 View Saved Quotations")
        
        # Get all quotations
        quotations = db.get_quotations()
        
        if not quotations.empty:
            st.subheader(f"📊 Total Quotations: {len(quotations)}")
            
            # Display quotations
            for idx, quotation in quotations.iterrows():
                with st.expander(f"💼 {quotation['quotation_id']} - {quotation['customer_name']} - ₹{quotation['final_amount']:,.2f}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Quotation ID:** {quotation['quotation_id']}")
                        st.write(f"**Customer:** {quotation['customer_name']}")
                        st.write(f"**Date:** {quotation['quotation_date']}")
                    
                    with col2:
                        st.write(f"**Total Amount:** ₹{quotation['total_amount']:,.2f}")
                        st.write(f"**Final Amount:** ₹{quotation['final_amount']:,.2f}")
                    
                    # Get quotation items
                    items = db.get_quotation_items(quotation['quotation_id'])
                    if not items.empty:
                        st.subheader("📦 Items")
                        st.dataframe(items, use_container_width=True)
        else:
            st.info("No quotations found. Create quotations in the 'Create Quotation' tab.")
    
    with tab6:
        st.header("⬇️ Download Quotations")
        
        # Get all quotations
        quotations = db.get_quotations()
        
        if not quotations.empty:
            st.subheader("📋 Select Quotation to Download")
            
            # Create quotation selection dropdown
            quotation_options = []
            for idx, row in quotations.iterrows():
                option = f"{row['quotation_id']} - {row['customer_name']} - ₹{row['final_amount']:,.2f}"
                quotation_options.append(option)
            
            selected_quotation = st.selectbox("Choose quotation to download:", quotation_options)
            
            if selected_quotation:
                # Get selected quotation details
                selected_idx = quotation_options.index(selected_quotation)
                quotation_details = quotations.iloc[selected_idx]
                
                # Get quotation items
                quotation_items = db.get_quotation_items(quotation_details['quotation_id'])
                
                if not quotation_items.empty:
                    st.subheader("📄 Quotation Preview")
                    
                    # Display quotation details
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Quotation ID:** {quotation_details['quotation_id']}")
                        st.write(f"**Customer Name:** {quotation_details['customer_name']}")
                    
                    with col2:
                        st.write(f"**Date:** {quotation_details['quotation_date']}")
                        st.write(f"**Final Amount:** ₹{quotation_details['final_amount']:,.2f}")
                    
                    # Display items
                    st.dataframe(quotation_items, use_container_width=True)
                    
                    # Generate Excel download
                    if st.button("📥 Generate Excel Quotation", type="primary"):
                        try:
                            # Prepare quotation data for Excel export
                            quotation_data = []
                            
                            for _, item in quotation_items.iterrows():
                                # Calculate pricing
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
                            
                            # Write Terms & Conditions header spanning multiple columns
                            worksheet.merge_range(terms_start_row, 0, terms_start_row, 6, 'TERMS & CONDITIONS:', terms_header_format)
                            
                            # Terms & Conditions content
                            terms_conditions = [
                                "1. All prices are inclusive of taxes unless otherwise specified.",
                                "2. Payment terms: 50% advance, 50% on delivery.",
                                "3. Delivery period: 10-15 working days from confirmation.",
                                "4. Installation charges are extra if applicable.",
                                "5. Warranty: 2 years manufacturing defect warranty.",
                                "6. This quotation is valid for 30 days from the date of issue.",
                                "7. Transportation and packaging charges are included.",
                                "8. Any changes in government taxes will be charged extra."
                            ]
                            
                            # Write terms spanning multiple columns for better presentation
                            for i, term in enumerate(terms_conditions):
                                term_row = terms_start_row + 2 + i
                                worksheet.merge_range(term_row, 0, term_row, 8, term, terms_format)
                            
                            # Set column widths for better appearance
                            worksheet.set_column('A:A', 8)   # Sr. No.
                            worksheet.set_column('B:B', 20)  # Picture
                            worksheet.set_column('C:C', 25)  # Model
                            worksheet.set_column('D:D', 15)  # Body Color
                            worksheet.set_column('E:E', 15)  # Light Color
                            worksheet.set_column('F:F', 12)  # Size
                            worksheet.set_column('G:G', 10)  # Watt
                            worksheet.set_column('H:H', 15)  # Beam Angle
                            worksheet.set_column('I:I', 12)  # Cut Out
                            worksheet.set_column('J:J', 10)  # Quantity
                            worksheet.set_column('K:K', 15)  # Unit Price
                            worksheet.set_column('L:L', 15)  # Project Price
                            worksheet.set_column('M:M', 15)  # Final Price
                            
                            # Close workbook to finalize the file
                            workbook.close()
                            
                            # Prepare download
                            output.seek(0)
                            excel_data = output.getvalue()
                            
                            # Create download button
                            st.download_button(
                                label="📥 Download Excel Quotation",
                                data=excel_data,
                                file_name=f"Quotation_{quotation_details['quotation_id']}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            st.success("Excel quotation generated successfully!")
                            
                        except Exception as e:
                            st.error(f"Error generating Excel file: {str(e)}")
                            st.write("Debug info:", str(e))
                
                else:
                    st.error("No items found for this quotation.")
        else:
            st.info("No quotations available for download. Create quotations first.")

if __name__ == "__main__":
    main()