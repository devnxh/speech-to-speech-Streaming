from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import subprocess
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'outputs/'
app.config['FINAL_OUTPUT']='static/processed'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def unique_filename(filename):
    """Generate a unique filename by appending a timestamp and UUID."""
    name, ext = os.path.splitext(filename)
    unique_id = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"

@app.route('/')
def index():
    language = {
        'en': 'English',
        'hi': 'Hindi',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh-cn': 'Chinese (Simplified)'
    }
    return render_template('index.html', languages=language)

@app.route('/process', methods=['POST'])
def process():
    # Upload video
    video = request.files['video']
    target_language = request.form['language']
    
    if video:
        # Generate unique filenames for each step
        video_filename = unique_filename(video.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video.save(video_path)

        audio_filename = f"extracted_audio_{uuid.uuid4().hex}.wav"
        audio_path = os.path.join(app.config['OUTPUT_FOLDER'], audio_filename)

        transcription_filename = f"transcription_{uuid.uuid4().hex}.txt"
        text_path = os.path.join(app.config['OUTPUT_FOLDER'], transcription_filename)

        translated_text_filename = f"translated_{target_language}_{uuid.uuid4().hex}.txt"
        translated_text_path = os.path.join(app.config['OUTPUT_FOLDER'], translated_text_filename)

        translated_audio_filename = f"translated_audio_{uuid.uuid4().hex}.mp3"
        translated_audio_path = os.path.join(app.config['OUTPUT_FOLDER'], translated_audio_filename)

        output_video_filename = f"final_video_{uuid.uuid4().hex}.mp4"
        output_video_path = os.path.join(app.config['FINAL_OUTPUT'], output_video_filename)

        # Extract audio from video
        subprocess.run([
            "ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path
        ], check=True)

        # Convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            transcription = recognizer.recognize_google(audio)

        with open(text_path, 'w', encoding='utf-8') as file:
            file.write(transcription)

        # Translate text
        translator = Translator()
        translated = translator.translate(transcription, dest=target_language)

        with open(translated_text_path, 'w', encoding='utf-8') as file:
            file.write(translated.text)

        # Convert translated text to audio
        tts = gTTS(text=translated.text, lang=target_language)
        tts.save(translated_audio_path)

        # Merge audio and video
        subprocess.run([
            "ffmpeg",
            "-i", video_path,        # Input video
            "-i", translated_audio_path,  # Input translated audio
            "-map", "0:v:0",         # Select video from the first input
            "-map", "1:a:0",         # Select audio from the second input
            "-c:v", "copy",          # Copy video stream without re-encoding
            "-c:a", "aac",           # Use AAC codec for audio
            "-shortest",             # Ensure the output duration matches the shortest stream
            output_video_path        # Output file
        ], check=True)
        
        # Return specific file paths to the client
        return render_template('result.html', 
                               original_video_url=url_for('static', filename=f'uploads/{video_filename}'),
                               translated_video_url=url_for('static', filename=f'processed/{output_video_filename}'))
    
    return redirect(url_for('index'))

@app.route('/download/<file_type>')
def download(file_type):
    file_map = {
        'text': request.args.get('text_file'),
        'translated_text': request.args.get('translated_file'),
        'audio': request.args.get('audio_file'),
        'video': request.args.get('video_file')
    }
    file_path = os.path.join(app.config['FINAL_OUTPUT'], file_map[file_type])
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
