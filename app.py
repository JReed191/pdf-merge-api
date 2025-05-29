import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import shutil
from utils.pdf_merger import PDFMerger

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with file upload interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and merging"""
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            flash('No files selected', 'error')
            return redirect(url_for('index'))
        
        files = request.files.getlist('files')
        
        # Validate files
        if not files or len(files) == 0:
            flash('No files selected', 'error')
            return redirect(url_for('index'))
        
        # Check if all files are PDFs
        valid_files = []
        for file in files:
            if file.filename == '':
                continue
            if file and allowed_file(file.filename):
                valid_files.append(file)
            else:
                flash(f'Invalid file type: {file.filename}. Only PDF files are allowed.', 'error')
                return redirect(url_for('index'))
        
        if len(valid_files) < 2:
            flash('Please select at least 2 PDF files to merge', 'error')
            return redirect(url_for('index'))
        
        # Create temporary directory for this merge operation
        temp_dir = tempfile.mkdtemp()
        uploaded_files = []
        
        try:
            # Save uploaded files
            for file in valid_files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
                uploaded_files.append(file_path)
                app.logger.info(f'Saved file: {filename}')
            
            # Initialize PDF merger
            merger = PDFMerger()
            
            # Merge PDFs
            merged_file_path = merger.merge_pdfs(uploaded_files, temp_dir)
            
            if merged_file_path and os.path.exists(merged_file_path):
                # Send the merged file
                return send_file(
                    merged_file_path,
                    as_attachment=True,
                    download_name='merged_nec_contract.pdf',
                    mimetype='application/pdf'
                )
            else:
                flash('Error occurred during PDF merge', 'error')
                return redirect(url_for('index'))
                
        except Exception as e:
            app.logger.error(f'Error during merge: {str(e)}')
            flash(f'Error merging PDFs: {str(e)}', 'error')
            return redirect(url_for('index'))
        
        finally:
            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                app.logger.warning(f'Could not clean up temp directory: {str(e)}')
                
    except Exception as e:
        app.logger.error(f'Unexpected error: {str(e)}')
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('index'))

@app.route('/api/status')
def api_status():
    """API endpoint to check service status"""
    return jsonify({
        'status': 'online',
        'service': 'NEC PDF Merger',
        'max_file_size': '50MB',
        'supported_formats': ['PDF']
    })

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('File too large. Maximum file size is 50MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    app.logger.error(f'Internal server error: {str(e)}')
    flash('An internal server error occurred', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
