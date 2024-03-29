from flask import Flask, render_template, request, redirect, session, flash
from decouple import config
import uuid 
import hashlib
import firebase_admin
from firebase_admin import credentials, db
from pycpfcnpj import cpfcnpj
from datetime import datetime
import random

app = Flask(__name__, template_folder='view')
app.secret_key = 'secret'

# Configuração do Firebase
class FirebaseConfig:
    def __init__(self):
        firebaseConfig =  {
    'apiKey': config("FIREBASE_API_KEY"),
    'authDomain': config("FIREBASE_AUTH_DOMAIN"),
    'databaseURL':config("DATABASE_URL"),
    'projectId': config("FIREBASE_PROJECT_ID"),
    'storageBucket': config("FIREBASE_STORAGE_BUCKET"),
    'messagingSenderId': config("FIREBASE_MESSAGING_SENDER_ID"),
    'appId': config("FIREBASE_APP_ID"),
    'measurementId': config("FIREBASE_MEASUREMENT_ID"),
}

#initialize DB
        dbCredentials = {
  "type": config("TYPE"),
  "project_id": config("FIREBASE_PROJECT_ID"),
  "private_key_id": config("PRIVATE_KEY_ID"),
  "private_key": config("PRIVATE_KEY"),
  "client_id": config("CLIENT_ID"),
  "auth_uri": config("AUTH_URI"),
  "token_uri": config("TOKEN_URI"),
  "auth_provider_x509_cert_url": config("AUTH_PROVIDER_CERT"),
  "client_x509_cert_url": config("CLIENT_CERT"),
  "universe_domain": config("UNIVERSE_DOMAIN"),
  "client_email": config("CLIENT_EMAIL") 
}


        cred = credentials.Certificate(dbCredentials)
        firebase_admin.initialize_app(cred , {"databaseURL": "https://pet-hub-rs-default-rtdb.firebaseio.com"})

firebase_config = FirebaseConfig()
# creating reference to root node
ref = db.reference("/")
users = db.reference("/users")

def get_stores():
    all_users = users.get()
    listOfStores = []
    if all_users is not None:
    # Itera sobre cada usuário
        for user_key, user_data in all_users.items():
            if 'onSaleProducts' in user_data:
                store = []
                store.append(user_key)
                store.append(user_data)
                listOfStores.append(store)
        return listOfStores



# Classe Utils
class Utils:
    @staticmethod
    def get_date():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_order_id():
        date = Utils.get_date()
        random_string = ''.join(random.choices('0123456789', k=6))
        return f"{date}-{random_string}"

    @staticmethod
    def hash_password(password):
        sha1 = hashlib.sha1()
        sha1.update(password.encode('utf-8'))
        return sha1.hexdigest()

    @staticmethod
    def validate_document(document_number):
        return cpfcnpj.validate(document_number)
    
    @staticmethod
    def is_document_number_unique(document_number):
        try:
            query =  user_manager.query_user(document_number)
        except:
            query = None

        return True if query == None else False

    @staticmethod
    def document_password_invalid(password, password_confirmation, document_number):
        wrong_password = False
        wrong_document = False
        not_unique_document = False
        password_encoded = Utils.hash_password(password)
        password_confirmation_encoded = Utils.hash_password(password_confirmation)
        password_length = len(password)

        if  password_encoded != password_confirmation_encoded:
            flash("as senhas escolhidas divergem", "invalid_password_message")
            wrong_password = True
        elif password_length < 7:
            flash("senha inválida: a senha precisa ter no mínimo 6 caracteres", "invalid_password_message")
            wrong_password = True

        if not cpfcnpj.validate(document_number):
            flash("número de documento inválido", "invalid_document_message")
            wrong_document = True

        if  not Utils.is_document_number_unique(document_number):
            flash("documento já cadastrado", "invalid_document_message")
            not_unique_document = True

        if  wrong_password or wrong_document or  not_unique_document: 
            return True

    @staticmethod
    def invalid_password_change(password_encoded, password_confirmation_encoded, password_length):
      wrong_password = False
  
      if  password_encoded != password_confirmation_encoded:
          flash("as senhas escolhidas divergem", "invalid_password_message")
          wrong_password = True
      elif password_length < 7:
          flash("senha inválida: a senha precisa ter no mínimo 6 caracteres", "invalid_password_message")
          wrong_password = True
  
      if  wrong_password:
          return True
  

# Classe UserManager
class UserManager:
    def __init__(self):
        self.users_ref = db.reference("/users")

    def query_user(self, document_number):
        return self.users_ref.child(document_number).get()

    def add_user(self, document_number, user_data):
        self.users_ref.child(document_number).set(user_data)

    def delete_user(self, document_number):
        self.users_ref.child(document_number).delete()

    def update_user(self, document_number, update_data):
        self.users_ref.child(document_number).update(update_data)

    def set_history(self, document_number, update_data, orderId):
        self.users_ref.child(document_number).child('userHistory').child('orders').child(orderId).set(update_data)

    def query_history(self, document_number):
        orders =user_manager.users_ref.child(document_number).child('userHistory').child('orders').get()
        listOfOrders = []
        if orders is not None:
        # Itera sobre cada usuário
            for order_key, order_data in orders.items():
                listOfOrders.append(order_data)

        return listOfOrders

    def query_completed_purchases(self, document_number):
        completedPurchasesQuery = self.users_ref.child(document_number).child('userHistory').order_by_key().equal_to('completedPurchases').get()
        completedPurchases = 0
        if completedPurchasesQuery:
            for key, value in completedPurchasesQuery.items():
                completedPurchases = value
        return completedPurchases

    def update_purchases(self, document_number, completedPurchases):
        self.users_ref.child(document_number).child('userHistory').update({'completedPurchases': int(completedPurchases) + 1})

    def alterarCadastroUsuario(self, password, password_confirmation, document,  name, email, must_change_password):
        password_encoded = password.encode('utf-8')
        password_confirmation_encoded = password_confirmation.encode('utf-8')
        password_length = len(password)
        
        if must_change_password is True:
            if Utils.invalid_password_change(password_encoded, password_confirmation_encoded, password_length):
                return redirect('/alterarDados')
            else:
                # Create a SHA-1 hash object
                sha1 = hashlib.sha1()
    
                # Update the hash object with the encoded password
                sha1.update(password_encoded)
    
                # Get the hexadecimal representation of the hash
                hashed_password = sha1.hexdigest()
    
            
                self.users_ref.child(document).update(
                    {
                            "userName": name,
                            "userEmail": email,
                            "userPassword": hashed_password
                    }
                )
        else:
            self.users_ref.child(document).update(
                    {
                            "userName": name,
                            "userEmail": email,
                    }
                )
        session.pop("user")
        return redirect("/")
        # ... Métodos da classe UserManager como já definidos anteriormente ...
class productManager:
    def __init__(self):
        self.product_ref = db.reference("/users")

    def query_products(self):
        users =self.product_ref.get()
        listOfProducts = []
        if users is not None:
        # Itera sobre cada usuário
            for user_key, user_data in users.items():
                # Verifica se o usuário tem o nó 'onSaleProducts'
                if 'onSaleProducts' in user_data:
                    if user_data['onSaleProducts'] is not None:
                        on_sale_products = user_data['onSaleProducts']
                        if 'products' in on_sale_products:
                            products = on_sale_products['products']
                    # Itera sobre cada produto em 'onSaleProducts'
                            for product_key, product_data in products.items():
                                # Verifica se o produto tem o campo 'nome'
                                listOfProducts.append(product_data)
            return listOfProducts

    def queryNumberOfProducts(self, user_document_number):
        numberOfProductsQuery = self.product_ref.child(user_document_number).child('onSaleProducts').order_by_key().equal_to('numberOfProducts').get()
        numberOfProducts = 0

        if numberOfProductsQuery:
            for key, value in numberOfProductsQuery.items():
                numberOfProducts = value

        return numberOfProducts

    def query_user_products_with_key(self, user_document_number):
        products =self.product_ref.child(user_document_number).child('onSaleProducts').child('products').get()
        if products is not None:
          listOfProducts = list(products.items())
        else: 
          listOfProducts = []

        return listOfProducts

    def update_product(self, user_document_number, product_key, product_data):
        self.product_ref.child(user_document_number).child('onSaleProducts').child('products').child(product_key).update(product_data)

    def delete_product(self, user_document_number, product_key):
        self.product_ref.child(user_document_number).child('onSaleProducts').child('products').child(product_key).delete()
        numberOfProducts = product_manager.queryNumberOfProducts(user_document_number)
        self.product_ref.child(user_document_number).child('onSaleProducts').update({'numberOfProducts': int(numberOfProducts) - 1})


    def add_product(self, user_document_number, product):
        on_sale_products = self.product_ref.child(user_document_number).child('onSaleProducts')

        on_sale_products.child('products').child(product['title']).set(product)

        numberOfProducts = product_manager.queryNumberOfProducts(user_document_number)

        on_sale_products.update({'numberOfProducts': int(numberOfProducts) + 1})
    
# Classe CartManager
class CartManager:
    def __init__(self, user_manager):
        self.user_manager = user_manager

    def queryCart(self, document_number):
        products =user_manager.users_ref.child(document_number).child('userCart').child('products').get()
        print(products)
        listOfProducts = []
        totalValue = 0
        if products is not None:
        # Itera sobre cada usuário
            for product_key, product_data in products.items():
                # Verifica se o produto tem o campo 'nome'
                if 'price' in product_data:
                    totalValue += float(product_data['price'])
                product_complete = []
                product_complete.append(product_key)
                product_complete.append(product_data)
                listOfProducts.append(product_complete)

        totalValueFormatted = "{:.{}f}".format(totalValue, 2)

        return listOfProducts, totalValueFormatted
    
    def add_product_to_cart(self, document_number, product_data):
        product_key = product_data['title']
        existing_product = self.user_manager.users_ref.child(document_number).child('userCart').child('products').child(product_key).get()

        while existing_product:
            product_key += "'"
            existing_product = self.user_manager.users_ref.child(document_number).child('userCart').child('products').child(product_key).get()

        self.user_manager.users_ref.child(document_number).child('userCart').child('products').child(product_key).set(product_data)
        number_of_products = self.user_manager.users_ref.child(document_number).child('userCart').child('numberOfProducts').get() or 0
        self.user_manager.users_ref.child(document_number).child('userCart').update({'numberOfProducts': int(number_of_products) + 1})

    def remove_product_from_cart(self, document_number, product_key):
        self.user_manager.users_ref.child(document_number).child('userCart').child('products').child(product_key).delete()
        number_of_products = self.user_manager.users_ref.child(document_number).child('userCart').child('numberOfProducts').get() or 0
        self.user_manager.users_ref.child(document_number).child('userCart').update({'numberOfProducts': int(number_of_products) - 1})

    def clear_cart(self, document_number):
        self.user_manager.users_ref.child(document_number).child('userCart').child('products').delete()
        self.user_manager.users_ref.child(document_number).child('userCart').update({'numberOfProducts': 0})

    def get_cart_products_and_total(self, document_number):
        cart_ref = db.reference(f"/users/{document_number}/cart")
        cart_data = cart_ref.get()
        cart_products = []

        if cart_data:
            total_price = 0
            for product_key, product_data in cart_data.items():
                cart_products.append({
                    "key": product_key,
                    "data": product_data
                })
                total_price += product_data.get("price", 0)

            return cart_products, total_price
    # ... Métodos da classe CartManager como já definidos anteriormente ...

user_manager = UserManager()
cart_manager = CartManager(user_manager)
product_manager = productManager()

@app.route("/", methods =['POST', 'GET'])
def index():
    return render_template('index.html')

@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'user' in session:
        return redirect('/user')

    if request.method == 'POST':
        document_number = request.form.get('document').replace("-", "").replace(".", "").replace("/", "")
        password = request.form.get('password')
        loginUser = user_manager.query_user(document_number)

        if loginUser and loginUser["userPassword"] == Utils.hash_password(password):
            session["user"] = loginUser["userName"]
            session["documentNumber"] = document_number
            session["userType"] = "pessoaJuridica" if len(document_number) > 11 else "pessoaFisica"
            session["email"] = loginUser["userEmail"]
            return redirect('/user')
        else:
            flash("Senha ou usuário inválidos", "invalid_user_password_message")
            return redirect('/login')
    else:
        return render_template('login.html')
    # ... Implementação da rota de login ...

@app.route("/cadastro", methods=['POST', 'GET'])
def cadastro():
    if request.method == 'POST':
        uid = str(uuid.uuid4())
        email = request.form.get('email')
        name = request.form.get('nome')
        document = request.form.get('cpf').replace("-", "").replace(".", "").replace("/", "")
        password = request.form.get('password1')
        password_confirmation = request.form.get('password2')

        if Utils.document_password_invalid(password, password_confirmation, document):
            return redirect('/cadastro')

        hashed_password = Utils.hash_password(password)
        user_data = {
            "uid": uid,
            "userName": name,
            "userPassword": hashed_password,
            "userEmail": email,
            "userCart": {"products": {}, "numberOfProducts": 0},
            "userHistory": {"completedPurchases": 0}
        }
        user_manager.add_user(document, user_data)
        return redirect('/login')
    else:
        return render_template('cadastro.html')
    # ... Implementação da rota de cadastro ...

@app.route("/meuCarrinho", methods=['GET', 'POST'])
def meuCarrinho():
    if 'user' not in session:
        flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
        return redirect('/login')
    
    if (session["userType"] == "pessoaJuridica"):
       flash("Você não tem acesso a esta sessão logado como pessoa jurídica.", "unauthorized_user_message_lojas")
       return redirect("/")
    if request.method == 'GET':
        cart_products= True

        cart_data, _ = cart_manager.queryCart(session['documentNumber'])
        print(cart_data)

        if cart_data == None or cart_data == []:
            cart_products = False

        print(cart_products)
        return render_template("meuCarrinho.html", lista_de_itens=cart_data, canBuy=bool(cart_products))

    elif request.method == 'POST':
        product_key = request.form.get('chaveProduto')
        cart_manager.remove_product_from_cart(session['documentNumber'], product_key)
        flash("Produto removido do carrinho com sucesso!", 'cart_updated_success')
        return redirect("/meuCarrinho")
    # ... Implementação da rota do carrinho de compras ...


@app.route("/meuHistorico", methods=['GET'])
def meuHistorico():
    if 'user' not in session:
        return redirect('/login')

    if user_manager.query_completed_purchases(session['documentNumber']) == 0:
        flash("Nenhuma compra efetuada.", "empty_history_message")
        return render_template("/meuHistorico.html")
    else:
        user_history = user_manager.query_history(session['documentNumber'])
        return render_template("/meuHistorico.html", lista_de_pedidos=user_history)



@app.route("/alterarDados", methods=["GET", "POST"])
def alterarDados():
    must_change_name = False
    must_change_email = False
    must_change_password = False

    if request.method == 'POST': 
        email = request.form.get('email')
        name = request.form.get('nome')
        password = request.form.get('password1')
        password_confirmation = request.form.get('password2')

        if('user' in session):
            if session["email"] != email:
                must_change_email = True

            if session["user"] != name:
                must_change_name = True

            if password is not None and password != '':
                must_change_password = True

            document_formatted = session["documentNumber"]

        if must_change_name or must_change_email or must_change_password:  
            return user_manager.alterarCadastroUsuario(password, password_confirmation, document_formatted, name, email, must_change_password)
        else:
            if('user' in session):
                if(session["userType"] == "pessoaJuridica"):
                    is_juridica = True
                    mask = "00.000.000/0000-00"
                    flash("Você não realizou nenhuma alteração.", "bad_request_user_message_no_changes")
                    return render_template("/alterarDados.html", is_juridica=is_juridica, mask=mask, user_name=session["user"], document_number=session["documentNumber"], email=session["email"], user_type = session["userType"])
                elif(session["userType"] == "pessoaFisica"):
                    is_juridica = False
                    mask = "000.000.000-00"
                    flash("Você não realizou nenhuma alteração.",  "bad_request_user_message_no_changes")
                    return render_template("/alterarDados.html", is_juridica=is_juridica, mask=mask, user_name=session["user"], document_number=session["documentNumber"], email=session["email"], user_type = session["userType"])

    else:
        if('user' in session):
            if(session["userType"] == "pessoaJuridica"):
                is_juridica = True
                mask = "00.000.000/0000-00"
                return render_template("/alterarDados.html", is_juridica=is_juridica, mask=mask, user_name=session["user"], document_number=session["documentNumber"], email=session["email"], user_type = session["userType"])
            elif(session["userType"] == "pessoaFisica"):
                is_juridica = False
                mask = "000.000.000-00"
                return render_template("/alterarDados.html", is_juridica=is_juridica, mask=mask, user_name=session["user"], document_number=session["documentNumber"], email=session["email"], user_type = session["userType"])


@app.route("/lojista")
def lojista():
    return render_template("/lojistaMenu.html")

@app.route("/minhaLoja")
def loja():
    if 'user' in session and session["userType"] == "pessoaJuridica":
        flash(session["user"], "user_name")
        return render_template("/minhaLoja.html")
        print("OIOIOIO")

    else:
        print("OIOIOIO")
        flash("Você não tem acesso a esta sessão logado como pessoa física.", "unauthorized_user_message")
        return render_template("/lojistaMenu.html")


@app.route("/finalizarCompra", methods=['GET', 'POST'])
def finalizarCompra():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'GET':
        cart_products= False

        cart_data, total_value = cart_manager.queryCart(session['documentNumber'])
        
        if cart_data != None:
            cart_products = True

        return render_template("finalizarCompra.html", lista_de_itens=cart_data, totalValue=total_value, canBuy=bool(cart_products))

    elif request.method == 'POST':
        delivery_address = request.form.get('endereco')
        payment_method = request.form.get('tipoPagamento')
        order_id = Utils.get_order_id()
        date = Utils.get_date()

        # Atualiza o histórico de compras
        user_manager.update_user(session['documentNumber'], {
            'userHistory.orders': {
                order_id: {
                    'totalValue': sum(float(product['price']) for product in cart_products.values()),
                    'deliveryAddress': delivery_address,
                    'payment': payment_method,
                    'orderDate': date
                }
            }
        })
        user_manager.update_purchases(session['documentNumber'], user_manager.query_completed_purchases(session['documentNumber']) + 1)

        # Limpa o carrinho
        cart_manager.clear_cart(session['documentNumber'])

        flash(f'Pedido "{order_id}" efetuado com sucesso!', 'order_success')
        return redirect("/meuHistorico")
    # ... Implementação da rota de finalização da compra ...

@app.route("/cadastroLoja", methods =['POST', 'GET'])
def cadastroLoja():

    if("user" in session):
        if(session["userType"] == "pessoaJuridica"):
            flash("Você não tem acesso a esta sessão já logado como pessoa jurídica.", "unauthorized_user_message_cadastroLoja")
            return render_template("/lojistaMenu.html")
        elif(session["userType"] == "pessoaFisica"):
             flash("Você não tem acesso a esta sessão logado como pessoa física.", "unauthorized_user_message_cadastroLoja")
             return render_template("/lojistaMenu.html")
     
    if request.method == 'POST':
        uid = str(uuid.uuid4())
        email = request.form.get('email')
        name = request.form.get('nome')
        document = request.form.get('cnpj').replace("-", "").replace(".", "").replace("/", "")
        password = request.form.get('password1')
        password_confirmation = request.form.get('password2')
       
        if Utils.document_password_invalid(password, password_confirmation, document):
            return redirect('/cadastroLoja')

        hashed_password = Utils.hash_password(password)
        user_data = {
            "uid": uid,
            "userName": name,
            "userPassword": hashed_password,
            "userEmail": email,
            "onSaleProducts": {"products": {}, "numberOfProducts": 0},
        }
        user_manager.add_user(document, user_data)
        return redirect('/login')
    else:
        return render_template('cadastroLoja.html')

@app.route("/user", methods=['POST', 'GET'])
def user():
    if 'userType' not in session:
        return redirect('/login')

    if session["userType"] == "pessoaJuridica":
        return redirect("/minhaLoja")
    elif session["userType"] == "pessoaFisica":
        flash(session["user"], "user_name")
        return render_template("perfil.html")
    else:
        return redirect('/')



@app.route("/lojas", methods=['GET'])
def lojas():
    if request.method == 'GET':
            if "user" not in session:
                flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
                return redirect("/login")
            if (session["userType"] == "pessoaJuridica"):
                flash("Você não tem acesso a esta sessão logado como pessoa jurídica.", "unauthorized_user_message_lojas")
                return redirect("/")
            else:
                stores = get_stores()
                return render_template("/lojas.html", stores_list=stores)
    
    
@app.route("/logout", methods =['GET'])

def logout():
    session.clear()
    return redirect("/")

@app.route("/excluirConta", methods=["GET"])
def deletarConta():
    user_manager.delete_user(session["documentNumber"])
    session.clear()
    return redirect("/")

@app.route("/produtos", methods=['GET', 'POST'])
def produto():
    if request.method == 'GET':
        if "user" not in session:
            flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
            return redirect("/login")
        if session["userType"] == "pessoaJuridica":
            return redirect("/")
        else:
            lista_de_itens = product_manager.query_products()
            return render_template("/produtos.html", lista_de_itens=lista_de_itens)
    elif request.method == 'POST':
        product_title = request.form.get('tituloProduto')
        product_price = request.form.get('precoProduto')
        product_description = request.form.get('descricaoProduto')

        product_data = {
            'title': product_title,
            'price': product_price,
            'description': product_description
        }
        cart_manager.add_product_to_cart(session['documentNumber'], product_data)

        flash(f'Produto "{product_title}" adicionado ao carrinho com sucesso!', 'cart_updated_success')
        return redirect("/produtos")

@app.route("/processarFinalizarCompra", methods=['POST'])
def processPurchase():
    # Esta rota pode incluir lógicas adicionais, como verificação de estoque ou aplicação de descontos
    return redirect('/finalizarCompra')

@app.route("/efetuarPedido", methods=['POST'])
def purchaseDone():
    # Coletar informações do formulário
    totalValue = request.form.get('valorTotal')
    deliveryAddress = request.form.get('endereco')
    payment = request.form.get('tipoPagamento')

    # Gerar ID de pedido e obter data atual
    orderId = Utils.get_order_id()
    date = Utils.get_date()

    # Atualizar histórico de pedidos do usuário
    user_manager.set_history(session['documentNumber'], {
        
                'totalValue': totalValue,
                'deliveryAddress': deliveryAddress,
                'payment': payment,
                'orderDate': date
            }, orderId
    )
    user_manager.update_purchases(session['documentNumber'], user_manager.query_completed_purchases(session['documentNumber']))

    # Limpar o carrinho
    cart_manager.clear_cart(session['documentNumber'])

    flash(f'Pedido "{orderId}" efetuado com sucesso!', 'order_success')
    return redirect("/meuHistorico")

# ... (outras rotas conforme necessário) ...
@app.route("/navbar")
def navbar():
    return render_template("/navbar.html")


@app.route("/cadastrarProduto", methods =['GET', 'POST'])
def cadastrarProduto():
    if "user" not in session:
        flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
        return redirect("/")
    if (session["userType"] == "pessoaFisica"):
        return redirect("/")
    
    if request.method == 'GET':
            return render_template("/cadastrarProduto.html")

    elif request.method == 'POST':
        productTitle = request.form.get('tituloProduto')
        productDescription = request.form.get('descricaoProduto')
        productPrice = request.form.get('precoProduto')

        product = {
            'price': productPrice,
            'description': productDescription,
            'title': productTitle
        }

        product_manager.add_product(user_document_number=session['documentNumber'], product = product)

        return redirect('/editarProduto')


@app.route("/editarProduto", methods=['GET', 'POST'])
def editarProduto():
    # Checagem de permissão
    if request.method == 'GET':
        if "user" not in session:
            flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
            return redirect("/")
        if (session["userType"] == "pessoaFisica"):
            return redirect("/")

        else:
            productsList = product_manager.query_user_products_with_key(session['documentNumber'])

            if productsList is not None:
              numberOfProducts = len(productsList)
            else:
              numberOfProducts = 0

            return render_template("editarProduto.html",
                                    numberOfProducts = numberOfProducts,
                                    productsList = productsList)


    # Edit or Delete products / service
    elif request.method == 'POST':
        productKey = request.form.get('chaveProduto')
        productTitle = request.form.get('tituloProduto')
        productPrice = request.form.get('precoProduto')
        productDescription = request.form.get('descricaoProduto')

        product = {
            'productKey' : productKey,
            'title': productTitle,
            'price': productPrice,
            'description': productDescription
        }

        if request.form.get('Action') == "Editar":
            print('Editar')

            session['product'] = product

            return redirect('/alterarProduto')
        
        elif request.form.get('Action') == "Deletar":
            print('Deletar')
            product_manager.delete_product(session['documentNumber'], productKey)

            # Delets product / service
            #actualQuantity = users.child(session['documentNumber']).child('onSaleProducts').child('numberOfProducts').get()
            #users.child(session['documentNumber']).child('onSaleProducts').set({'numberOfproducts': actualQuantity - 1})

            return redirect('/editarProduto')


@app.route("/alterarProduto", methods=['GET', 'POST'])
def alterarProduto():
    # Checagem de permissão
    if "user" not in session:
        flash("Você precisa estar logado para acessar esse recurso", "unauthorized_user")
        return redirect("/")
    if session["userType"] == "pessoaFisica":
        return redirect("/")
    
    product = session.get('product')  # Obter o produto da sessão


    if request.method == 'POST':
        productTitle = request.form.get('tituloProduto')
        productPrice = request.form.get('precoProduto')
        productDescription = request.form.get('descricaoProduto')
        
        if (product['title'] != productTitle or product['description'] != productDescription or product['price'] != productPrice):
            product_manager.update_product(session['documentNumber'], product['productKey'], {
                'description': productDescription, 
                'title': productTitle, 
                'price': productPrice, 
            })

        
        session.pop('product')
        return redirect('/editarProduto')
    else:
    # Move a operação session.pop para o final da função
        return render_template("alterarProduto.html", product=product)
    
if __name__ == "__main__":
    app.run(debug=True)
