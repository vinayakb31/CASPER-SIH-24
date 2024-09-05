import requests
import json
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user


def SearchAndResponse(search_str):
    global soup

    search_url = f"https://www.google.com/search?tbm=shop&q={search_str.replace(' ', '+')}"
    HEADERS = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0', 'Accepted-Language':'en-US, en;q=0.5'})

    response = requests.get(search_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')

    return soup


def GoogleShopScraping(soup):
    global products_list
    products_list = []
    
    titles = soup.find_all('h3', {'class':'tAxDx'})
    prices = soup.find_all('span', {'class':'a8Pemb OFFNJ'})
    source_name = soup.find_all('div', {'class':'aULzUe IuHnof'})
    jumbled_links = soup.find_all('div', {'class':'mnIHsc'})
    source_link = []

    for i in jumbled_links:
        jumbled_links_content = BeautifulSoup(str(i), 'html.parser')
        href_tag = jumbled_links_content.find('a', {'class': 'shntl'})
        source_link.append(href_tag.get('href'))
    source_link = ["https://www.google.com"+i for i in source_link]

    for i in range(len(titles)):
        products_list.append([i+1, titles[i].text.strip(), prices[i].text.strip(), source_name[i].text.strip(), source_link[i]])
    
    return products_list


def jsonInfoDump(products_list):
    with open('product_details.json', 'w') as f:
        json.dump(products_list, f)


def Webpage():
    global app

    app = Flask(__name__)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///user_information.sqlite?timeout=5"
    app.config["SECRET_KEY"] = "Enter your secret key"

    db = SQLAlchemy(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    class Users(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(250), unique=True, nullable=False)
        password = db.Column(db.String(250), nullable=False)

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def loader_user(user_id):
        return Users.query.get(int(user_id))

    @app.route('/register', methods=["GET", "POST"])    
    def register():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")

            existing_user = Users.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already exists. Please choose another one.", "error")
                return redirect(url_for('register'))
            
            if password != confirm_password:
                flash("Passwords do not match. Please try again.", "error")
                return redirect(url_for('register'))
    
            user = Users(username=username, password=password)

            db.session.add(user)
            db.session.commit()
            
            return redirect(url_for('login'))
        
        return render_template("sign_up.html")

    @app.route('/login', methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = Users.query.filter_by(username=username).first()

            if user and user.password == password:
                login_user(user)
                return redirect(url_for("home"))
            
            else:
                flash("Incorrect username or password", "error")
            
        return render_template("login.html")

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route('/')
    def index():
        return redirect(url_for("login"))

    @app.route('/home')
    @login_required
    def home():
        return render_template("home.html")
    
    @app.route('/search', methods=["GET", "POST"])
    def search():
        if request.method == "POST":
            # Get the form data
            item_name = request.form.get("item_name")
            item_type = request.form.get("item_type")
            make = request.form.get("make")
            model = request.form.get("model")

            print(f"Item Name: {item_name}")
            print(f"Item Type: {item_type}")
            print(f"Make: {make}")
            print(f"Model: {model}")

            return redirect(url_for('results', item_name=item_name, item_type=item_type, make=make, model=model))

        return render_template("home.html")
    
    @app.route('/results')
    def results():
        item_name = request.args.get('item_name')
        item_type = request.args.get('item_type')
        make = request.args.get('make')
        model = request.args.get('model')

        SearchAndResponse(str(item_name + model + make))
        GoogleShopScraping(soup)
        jsonInfoDump(products_list)

        with open('product_details.json', 'r') as f:
            product_details = json.load(f)

        page = request.args.get('page', 1, type=int)
        per_page = 20

        start = (page - 1) * per_page
        end = start + per_page

        if start >= len(product_details):
            start = len(product_details) - per_page
            page = (len(product_details) + per_page - 1) // per_page

        if end > len(product_details):
            end = len(product_details)

        current_products = product_details[start:end]
        total_pages = (len(product_details) + per_page - 1) // per_page


        return render_template("results.html", product_details=current_products,page=page, total_pages=total_pages,
                               item_name=item_name, item_type=item_type, make=make, model=model)

if __name__ == "__main__":
    app = Flask(__name__)
    Webpage()
    app.run(debug=True)


Webpage()
