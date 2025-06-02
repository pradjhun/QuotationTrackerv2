# Quotation Management System

A comprehensive Streamlit-based quotation management application designed to streamline product quoting, pricing, and export processes for businesses.

## Features

- **User Authentication**: Role-based access control with admin and user roles
- **Product Management**: Import and manage product data from Excel files
- **Quotation Creation**: Create professional quotations with product selection
- **Excel Export**: Generate professional quotation documents with embedded images
- **Database Management**: SQLite-based storage for products and quotations
- **Image Handling**: Support for product images in quotations

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/pradjhun/Quotation.git
cd Quotation
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r dependencies.txt
```

## Usage

1. **Start the application:**
```bash
streamlit run app.py
```

2. **Open your browser** to `http://localhost:8501`

3. **Login with default credentials:**
   - Username: `admin`
   - Password: `admin123`

## Project Structure

```
Quotation/
├── app.py                  # Main application
├── auth_manager.py         # User authentication
├── database_manager.py     # Database operations
├── utils.py               # Utility functions
├── dependencies.txt       # Python dependencies
├── company_logo.webp      # Company logo
├── README.md             # This file
└── uploaded_images/      # Product images (auto-created)
```

## Tech Stack

- **Frontend**: Streamlit
- **Database**: SQLite
- **Data Processing**: Pandas
- **Excel Export**: OpenPyXL, XlsxWriter
- **Image Processing**: Pillow

## Key Features

### Authentication System
- Secure user management with hashed passwords
- Role-based access (Admin/User)
- Session management

### Product Management
- Excel file import for product data
- Search and filter functionality
- Image support for products

### Quotation System
- Interactive product selection
- Real-time calculation with GST
- Professional Excel export with company branding
- Customer information management

### Excel Export Features
- Professional table formatting with borders
- Center-aligned content
- Embedded product images
- Company logo integration
- Currency formatting with Rupee symbols
- Automatic calculations (Subtotal, GST, Total)

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team.