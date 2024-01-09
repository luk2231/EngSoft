from flask import Flask, render_template, request, redirect, session, flash
from decouple import config
import firebase_admin
from firebase_admin import db
import uuid
import hashlib

import firebase_admin
from firebase_admin import db, credentials

app = Flask(__name__, template_folder="view")
app.secret_key = "secret"

firebaseConfig = {
    "apiKey": config("FIREBASE_API_KEY"),
    "authDomain": config("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": config("DATABASE_URL"),
    "projectId": config("FIREBASE_PROJECT_ID"),
    "storageBucket": config("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": config("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": config("FIREBASE_APP_ID"),
    "measurementId": config("FIREBASE_MEASUREMENT_ID"),
}

# initialize DB
dbCredentials = {
    "type": config("TYPE"),
    "project_id": config("FIREBASE_PROJECT_ID"),
    "private_key_id": config("PRIVATE_KEY_ID"),
    "private_key": config("PRIVATE_KEY").replace("\\n", "\n"),
    "client_id": config("CLIENT_ID"),
    "auth_uri": config("AUTH_URI"),
    "token_uri": config("TOKEN_URI"),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_CERT"),
    "client_x509_cert_url": config("CLIENT_CERT"),
    "universe_domain": config("UNIVERSE_DOMAIN"),
    "client_email": config("CLIENT_EMAIL"),
}
cred = credentials.Certificate(dbCredentials)
firebase_admin.initialize_app(
    cred, {"databaseURL": "https://pet-hub-rs-default-rtdb.firebaseio.com"}
)

# creating reference to root node
ref = db.reference("/")
users = db.reference("/users")


@app.route("/", methods=["POST", "GET"])
def index():
    return render_template("index.html")


@app.route("/user", methods=["POST", "GET"])
def user():
    flash(session["user"], "user_name")
    return render_template("perfil.html")


def invalid_document_number(document_number):
    is_invalid_document_number = False
    if len(document_number) < 11:
        flash("número de documento inválido", "invalid_document_message")
        is_invalid_document_number = True

    if len(document_number) > 11 and len(document_number) < 14:
        flash("número de documento inválido", "invalid_document_message")
        is_invalid_document_number = True

    return is_invalid_document_number


@app.route("/login", methods=["POST", "GET"])
def login():
    if "user" in session:
        return redirect("/user")

    if request.method == "POST":
        document_number = request.form.get("document")
        password = request.form.get("password")
        try:
            document_number_formatted = (
                document_number.replace("-", "").replace(".", "").replace("/", "")
            )
            if invalid_document_number(document_number_formatted):
                return render_template("login.html")
            elif len(password) < 7:
                flash("senha ou usuário inválidos", "invalid_user_password_message")
                return render_template("login.html")
            else:
                # busca no banco de dados o usuário pelo número do documento
                loginUser = users.child(document_number_formatted).get()

                # encodifica a senha do usuário
                password_encoded = password.encode("utf-8")
                sha1 = hashlib.sha1()
                # Update the hash object with the encoded password
                sha1.update(password_encoded)
                # Get the hexadecimal representation of the hash
                hashed_password = sha1.hexdigest()

                if loginUser["userPassword"] == hashed_password:
                    session["user"] = loginUser["userName"]
                    return redirect("/user")
                else:
                    flash("senha ou usuário inválidos", "invalid_user_password_message")
        except:
            return render_template("login.html")
    if request.method == "GET":
        return render_template("login.html")


def is_document_number_unique(document_number):
    query = users.child(document_number).get()
    return True if query == None else False


def invalid_password_or_document(
    password_encoded, password_confirmation_encoded, password_length, document_number
):
    wrong_password = False
    unique_document = True
    is_invalid_document_number = False

    if password_encoded != password_confirmation_encoded:
        flash("as senhas escolhidas divergem", "invalid_password_message")
        wrong_password = True
    elif password_length < 7:
        flash(
            "senha inválida: a senha precisa ter no mínimo 6 caracteres",
            "invalid_password_message",
        )
        wrong_password = True

    if invalid_document_number(document_number):
        is_invalid_document_number = True

    if not is_document_number_unique(document_number):
        flash("documento já cadastrado", "invalid_document_message")
        unique_document = False

    if wrong_password or not unique_document or is_invalid_document_number:
        return True


@app.route("/cadastro", methods=["POST", "GET"])
def cadastro():
    if request.method == "POST":
        # generates Random UID for Database
        idx = uuid.uuid4()
        uid = str(idx)
        email = request.form.get("email")
        name = request.form.get("nome")
        document = request.form.get("cpfOuCnpj")
        document_formatted = document.replace("-", "").replace(".", "").replace("/", "")
        password = request.form.get("password1")
        password_length = len(password)
        password_confirmation = request.form.get("password2")
        # TODO: teremos profile picture?
        # profilePicture = request.form.get('profilePicture')

        # Hash that Passsword
        password_encoded = password.encode("utf-8")
        password_confirmation_encoded = password_confirmation.encode("utf-8")

        if invalid_password_or_document(
            password_encoded,
            password_confirmation_encoded,
            password_length,
            document_formatted,
        ):
            return redirect("/cadastro")
        else:
            # Create a SHA-1 hash object
            sha1 = hashlib.sha1()

            # Update the hash object with the encoded password
            sha1.update(password_encoded)

            # Get the hexadecimal representation of the hash
            hashed_password = sha1.hexdigest()

            # Database Directive
            users.child(document_formatted).set(
                {
                    "uid": uid,
                    "userName": name,
                    "userPassword": hashed_password,
                    "userEmail": email,
                    # 'profilePicture': profilePicture
                }
            )
            return redirect("/login")
    return render_template("cadastro.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("user")
    return redirect("/")
