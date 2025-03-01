from flask import Flask, request, send_file, render_template, Response
import os
import uuid
import threading
import time
import qrcode
import shutil
import zipfile
from io import BytesIO

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store active file sessions
active_files = {}

def delayed_remove(file_path, delay=5):
    """Removes the file after a short delay to prevent permission errors."""
    time.sleep(delay)
    try:
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)  # Delete folder
        else:
            os.remove(file_path)  # Delete file
    except Exception as e:
        print(f"Error deleting: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload/file', methods=['POST'])
def upload_single_file():
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file_id + '_' + file.filename)
    file.save(file_path)
    
    active_files[file_id] = file_path
    file_url = f"{request.host_url}download/file/{file_id}"
    qr_url = f"{request.host_url}qr/{file_id}"  # Add QR Code URL
    
    return render_template('upload_success.html', file_url=file_url, qr_url=qr_url)

@app.route('/upload/folder', methods=['POST'])
def upload_folder():
    if 'files' not in request.files:
        return "No files uploaded", 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return "No selected files", 400
    
    folder_id = str(uuid.uuid4())
    folder_path = os.path.join(UPLOAD_FOLDER, folder_id)
    os.makedirs(folder_path, exist_ok=True)
    
    for file in files:
        file.save(os.path.join(folder_path, file.filename))
    
    # Zip the folder
    zip_path = f"{folder_path}.zip"
    shutil.make_archive(folder_path, 'zip', folder_path)
    shutil.rmtree(folder_path)  # Remove the original folder
    
    active_files[folder_id] = zip_path
    file_url = f"{request.host_url}download/folder/{folder_id}"
    qr_url = f"{request.host_url}qr/{folder_id}"  # Add QR Code URL
    
    return render_template('upload_success.html', file_url=file_url, qr_url=qr_url)

    
    # Zip the folder
    zip_path = f"{folder_path}.zip"
    shutil.make_archive(folder_path, 'zip', folder_path)
    shutil.rmtree(folder_path)  # Remove the original folder
    
    active_files[folder_id] = zip_path
    file_url = f"{request.host_url}download/folder/{folder_id}"
    
    return render_template('upload_success.html', file_url=file_url)

@app.route('/download/file/<file_id>')
def download_single_file(file_id):
    if file_id not in active_files:
        return "File not found or expired", 404
    
    file_path = active_files.pop(file_id, None)
    
    if os.path.exists(file_path):
        def generate():
            with open(file_path, "rb") as f:
                yield from f
            os.remove(file_path)  # Delete after sending
        
        response = Response(generate(), content_type="application/octet-stream")
        response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(file_path)}"
        return response
    else:
        return "File not found", 404

@app.route('/download/folder/<folder_id>')
def download_folder(folder_id):
    if folder_id not in active_files:
        return "File not found or expired", 404
    
    zip_path = active_files.pop(folder_id, None)
    
    if os.path.exists(zip_path):
        def generate():
            with open(zip_path, "rb") as f:
                yield from f
            os.remove(zip_path)  # Delete after sending
        
        response = Response(generate(), content_type="application/zip")
        response.headers["Content-Disposition"] = f"attachment; filename={folder_id}.zip"
        return response
    else:
        return "File not found", 404

@app.route('/qr/<file_id>')
def generate_qr(file_id):
    file_url = f"{request.host_url}download/file/{file_id}"
    qr = qrcode.make(file_url)
    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/contact-us')
def contact_us():
    return render_template('contact_us.html')


if __name__ == '__main__':
    app.run(debug=True)

    
