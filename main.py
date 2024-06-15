from flask import Flask, request, make_response
from werkzeug.utils import secure_filename
import datetime
import os
import subprocess
import shutil

app = Flask(__name__)

# Set the allowed video formats
ALLOWED_EXTENSIONS = {'mp4'}

# Set the maximum file size in MB
MAX_FILE_SIZE = 100

# Set the upload and output folder paths
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'

# Initialize the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'

        file = request.files['file']

        # Check the file extension
        if file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
            return 'Invalid file format. Only MP4 files are allowed.'

        # Check the file size
        if file.content_length > MAX_FILE_SIZE * 1024 * 1024:
            return 'File size exceeds the maximum limit of 100 MB.'

        # Get the current date and time
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        # Save the file with a unique name using the timestamp
        filename, file_extension = os.path.splitext(file.filename)
        unique_filename = f"{filename}_{timestamp}{file_extension}"
        input_video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(input_video_path)

        # Create temporary folders using the timestamp
        tmp_frames_folder = f'tmp_frames_{timestamp}'
        out_frames_folder = f'out_frames_{timestamp}'
        os.makedirs(tmp_frames_folder)
        os.makedirs(out_frames_folder)

        # Execute the commands
        video_file_name = os.path.splitext(unique_filename)[0]
        subprocess.run(['ffmpeg', '-i', input_video_path, '-qscale:v', '1', '-qmin', '1', '-qmax', '1', '-vsync', '0', f'{tmp_frames_folder}/frame%08d.jpg'])
        subprocess.run(['./realesrgan-ncnn-vulkan', '-i', f'./{tmp_frames_folder}', '-o', f'./{out_frames_folder}', '-n', 'realesrgan-x4plus', '-s', '4', '-f', 'jpg'])
        subprocess.run(['ffmpeg', '-i', f'{out_frames_folder}/frame%08d.jpg', '-i', input_video_path, '-map', '0:v:0', '-map', '1:a:0', '-c:a', 'copy', '-c:v', 'libx264', '-r', '23.98', '-pix_fmt', 'yuv420p', os.path.join(app.config['OUTPUT_FOLDER'], f'{video_file_name}.out.mp4')])

        # Remove the temporary folders
        shutil.rmtree(tmp_frames_folder)
        shutil.rmtree(out_frames_folder)

        # Return a success response
        response = make_response('Video processing completed successfully.', 200)
        return response

if __name__ == '__main__':
    app.run(debug=True)
