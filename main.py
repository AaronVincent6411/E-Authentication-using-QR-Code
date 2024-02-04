from flask import Flask, jsonify, render_template, request, redirect, url_for
import pyotp
import firebase_admin
from firebase_admin import credentials, auth
import base64
import qrcode
from io import BytesIO

app = Flask(__name__)

cred = credentials.Certificate("e-authentication-using-qr-code-firebase-service-key.json")
firebase_admin.initialize_app(cred)

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

if __name__ == '__main__':
    app.run(debug=True)