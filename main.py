from flask import Flask, jsonify, render_template, request, redirect, url_for, send_file
import pyotp
import firebase_admin
from firebase_admin import credentials, auth
import base64
import qrcode
from io import BytesIO
import wave
import os

app = Flask(__name__)

cred = credentials.Certificate("e-authentication-using-qr-code-firebase-service-key.json")
firebase_admin.initialize_app(cred)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'static/output'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        # password = request.form['password']
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']

        try:
            user = auth.create_user(email=email)
            # , password=password
            totp_secret = pyotp.random_base32()
            auth.update_user(
                user.uid,
                display_name=name,
                custom_claims={"age": age, "gender": gender, "totp_secret": totp_secret}
            )

            key = "EAuthenticationUsingQRCode"

            uri = pyotp.totp.TOTP(key).provisioning_uri(
                name=email,
                issuer_name='E-Authentication-Using-QR-Code'
            )

            print(uri)

            qr = qrcode.make(uri)
            buffered = BytesIO()
            qr.save(buffered)
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

            return render_template('register_success.html', qr_code_base64=qr_code_base64)
        except Exception as e:
            return render_template('error.html', error=str(e))

    return render_template('register.html')

@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        totp_code = request.form.get('totp_code')
        print(totp_code)

        try:
            key = "EAuthenticationUsingQRCode"

            print(totp_code)
            totp = pyotp.TOTP(key) 

            if totp.verify(totp_code):
                return render_template('signin_success.html', user_email=email)
            else:
                return render_template('error.html', error='Invalid TOTP code')
        except Exception as e:
            return render_template('error.html', error=str(e))

    return render_template('signin.html')

def hide_message(input_audio, secret_message, output_audio):
    waveaudio = wave.open(input_audio, mode='rb')
    frame_bytes = bytearray(list(waveaudio.readframes(waveaudio.getnframes())))
    secret_message = secret_message + int((len(frame_bytes)-(len(secret_message)*8*8))/8) *'#'
    bits = list(map(int, ''.join([bin(ord(i)).lstrip('0b').rjust(8,'0') for i in secret_message])))
    for i, bit in enumerate(bits):
        frame_bytes[i] = (frame_bytes[i] & 254) | bit
    frame_modified = bytes(frame_bytes)
    with wave.open(output_audio, 'wb') as fd:
        fd.setparams(waveaudio.getparams())
        fd.writeframes(frame_modified)
    waveaudio.close()

@app.route('/hide', methods=['POST'])
def upload_file():
    uploaded_file = request.files['audio_file']
    secret_message = request.form['secret_message']

    if uploaded_file.filename != '':
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        uploaded_file.save(audio_path)

        output_audio_path = os.path.join(app.config['OUTPUT_FOLDER'], 'modified_audio.wav')
        hide_message(audio_path, secret_message, output_audio_path)

        modified_audio_path = os.path.join(app.config['OUTPUT_FOLDER'], 'modified_audio.wav')

        return send_file(modified_audio_path, as_attachment=True)

@app.route('/extract', methods=['POST'])
def extract_message():
    uploaded_file = request.files['audio_file']
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
    uploaded_file.save(audio_path)

    waveaudio = wave.open(audio_path, mode='rb')
    frame_bytes = bytearray(list(waveaudio.readframes(waveaudio.getnframes())))
    extracted = [frame_bytes[i] & 1 for i in range(len(frame_bytes))]
    string = "".join(chr(int("".join(map(str,extracted[i:i+8])),2)) for i in range(0,len(extracted),8))
    msg = string.split("###")[0]
    waveaudio.close()

    if not msg or not msg.isprintable():
        return " "

    return f"{msg}"

if __name__ == '__main__':
    app.run(debug=True)