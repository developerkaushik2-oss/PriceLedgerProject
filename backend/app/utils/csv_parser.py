import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import os


ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_csv_file(file_path):
    """
    Parse CSV file and return dataframe with validation
    Expected columns: Store ID, SKU, Product Name, Price, Date
    Returns: (dataframe, error_message, invalid_records_info)
    """
    try:
        df = pd.read_csv(file_path)
        original_count = len(df)
        
        # Normalize column names (case-insensitive)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validate required columns
        required_cols = ['store id', 'sku', 'product name', 'price', 'date']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Add row index before processing
        df['_row_number'] = range(2, len(df) + 2)  # Line numbers (1-based + header)
        
        # Track invalid rows
        invalid_rows = []
        
        # Data type validation
        df['store id'] = df['store id'].astype(str).str.strip()
        df['sku'] = df['sku'].astype(str).str.strip()
        df['product name'] = df['product name'].astype(str).str.strip()
        
        # Convert price and date, track errors
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Find and track rows with invalid price or date
        invalid_price_date = df[df['price'].isna() | df['date'].isna()]
        for idx, row in invalid_price_date.iterrows():
            reason = []
            if pd.isna(row['price']):
                reason.append('invalid price')
            if pd.isna(row['date']):
                reason.append('invalid date')
            invalid_rows.append({
                'line': int(row['_row_number']),
                'store_id': str(row['store id']),
                'sku': str(row['sku']),
                'reason': ', '.join(reason)
            })
        
        # Remove rows with invalid data
        df = df.dropna(subset=['price', 'date'])
        
        # Track rows with non-positive price
        negative_price_rows = df[df['price'] <= 0]
        for idx, row in negative_price_rows.iterrows():
            invalid_rows.append({
                'line': int(row['_row_number']),
                'store_id': str(row['store id']),
                'sku': str(row['sku']),
                'reason': f'non-positive price ({row["price"]})'
            })
        
        # Validate price is positive
        df = df[df['price'] > 0]
        
        # Remove temporary row number column
        df = df.drop(columns=['_row_number'])
        
        if df.empty:
            invalid_info = {
                'total_rows': original_count,
                'invalid_rows': len(invalid_rows),
                'invalid_details': invalid_rows
            }
            raise ValueError(f"No valid records found in CSV file. {len(invalid_rows)} row(s) had invalid data")
        
        invalid_info = {
            'total_rows': original_count,
            'invalid_rows': len(invalid_rows),
            'invalid_details': invalid_rows
        }
        
        return df, None, invalid_info
        
    except Exception as e:
        return None, f"CSV Parse Error: {str(e)}", None


def validate_csv_data(df):
    """
    Validate CSV data integrity
    Returns tuple: (is_valid, errors_list)
    Note: Duplicates are allowed - they'll be skipped during import
    """
    errors = []
    
    # Check for empty dataframe
    if df.empty:
        errors.append("CSV file is empty")
        return False, errors
    
    # Warn about duplicates but don't fail (import service will skip them)
    duplicates = df[['store id', 'sku', 'date']].duplicated().sum()
    if duplicates > 0:
        errors.append(f"Warning: Found {duplicates} duplicate records - these will be skipped during import")
    
    # Validate specific columns - only fail for critical errors
    if (df['store id'].str.len() == 0).any():
        errors.append("Found empty Store IDs")
        return False, errors
    
    if (df['sku'].str.len() == 0).any():
        errors.append("Found empty SKUs")
        return False, errors
    
    if (df['price'] <= 0).any():
        errors.append("Found zero or negative prices")
        return False, errors
    
    # Always return True - let import service handle duplicates
    return True, errors


def save_uploaded_file(file):
    """Save uploaded file to disk"""
    if not allowed_file(file.filename):
        return None, "File must be a CSV file"
    
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    
    filename = secure_filename(file.filename)
    # Add timestamp to filename to ensure uniqueness
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    
    file_path = os.path.join('uploads', filename)
    file.save(file_path)
    
    return file_path, None
