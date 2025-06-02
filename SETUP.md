# Setup Guide for GitHub Upload

## Files to Upload to GitHub

Make sure you have these files in your local project folder:

### Core Application Files
- `app.py` - Main application
- `auth_manager.py` - Authentication system
- `database_manager.py` - Database operations
- `utils.py` - Utility functions

### Configuration Files
- `dependencies.txt` - Python package requirements
- `README.md` - Project documentation
- `.gitignore` - Files to exclude from Git
- `SETUP.md` - This setup guide

### Assets
- `company_logo.webp` - Company logo

## GitHub Upload Steps

1. **Initialize Git repository locally:**
```bash
git init
git add .
git commit -m "Initial commit: Quotation Management System"
```

2. **Connect to your GitHub repository:**
```bash
git remote add origin https://github.com/pradjhun/Quotation.git
git branch -M main
git push -u origin main
```

## For New Users Cloning the Repository

1. **Clone the repository:**
```bash
git clone https://github.com/pradjhun/Quotation.git
cd Quotation
```

2. **Install Python dependencies:**
```bash
pip install -r dependencies.txt
```

3. **Run the application:**
```bash
streamlit run app.py
```

4. **Access the application:**
Open browser to `http://localhost:8501`

5. **Login:**
- Username: admin
- Password: admin123

## Important Notes

- Database files (.db) are excluded from Git - they will be created automatically when the app runs
- The `uploaded_images` folder will be created automatically when products with images are added
- Default admin user is created automatically on first run

## File Structure After Setup
```
Quotation/
├── app.py
├── auth_manager.py
├── database_manager.py
├── utils.py
├── dependencies.txt
├── company_logo.webp
├── README.md
├── .gitignore
├── SETUP.md
└── (auto-created on first run)
    ├── quotation_database.db
    ├── users.db
    └── uploaded_images/
```