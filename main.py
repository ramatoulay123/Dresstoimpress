from flask import Flask, render_template, request, redirect, flash, abort
import flask_login
import pymysql
from datetime import datetime  # Added for handling timestamps
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
   settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/signin"


class User:
    is_authenticated = True
    is_anonymous = True
    is_active = True

    def __init__(self, user_id, username, email, full_name):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name 

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = connect_dv()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id};")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result is not None:
        return User(result["id"], result["username"], result["email"], result["full_name"])

def connect_dv():
    conn = pymysql.connect(
        host="10.100.34.80",
        database="rbarry_Dresstoimpress",
        user="rbarry",
        password=conf.password,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn


@app.route("/")
def index():
    return render_template("homepage.html.jinja")


@app.route("/browse")
def product_browse():
    query = request.args.get("query") 
    conn = connect_dv() 
    cursor = conn.cursor()

    if query is None:
        cursor.execute("SELECT * FROM `Product`;")
    else:
        cursor.execute(f"SELECT * FROM `Product` WHERE `name` LIKE '%{query}%' OR `description` ;")  

    results = cursor.fetchall()
    cursor.close()
    conn.close() 

    return render_template("browse.html.jinja", products=results)


@app.route("/product/<int:product_id>", methods=["GET", "POST"])
@flask_login.login_required
def product_page(product_id):
    conn = connect_dv()
    cursor = conn.cursor()

    # Fetch product details
    cursor.execute(f"SELECT * FROM `Product` WHERE `id` = {product_id};")
    product = cursor.fetchone()

    if not product:
        abort(404)

    # Fetch reviews for the product
    cursor.execute(f"""
        SELECT r.rating, r.comment, r.timestamp, c.username
        FROM Review r
        JOIN Customer c ON r.customer_id = c.id
        WHERE r.product_id = {product_id}
        ORDER BY r.timestamp DESC;
    """)
    reviews = cursor.fetchall()

    if request.method == "POST":
        # Check if the user already reviewed the product
        customer_id = flask_login.current_user.id
        cursor.execute(f"SELECT * FROM Review WHERE product_id = {product_id} AND customer_id = {customer_id};")
        existing_review = cursor.fetchone()

        if existing_review:
            flash("You have already submitted a review for this product.", "error")
        else:
            # Handle form submission for new review
            rating = request.form["rating"]
            comment = request.form["comment"]
            timestamp = datetime.now()

            # Insert the new review into the database
            cursor.execute(f"""
                INSERT INTO Review (product_id, customer_id, rating, comment, timestamp)
                VALUES ({product_id}, {customer_id}, {rating}, %s, %s);
            """, (comment, timestamp))
            conn.commit()

            flash("Your review has been submitted!", "success")
            return redirect(url_for('product_page', product_id=product_id))

    cursor.close()
    conn.close()

    return render_template("product.html.jinja", product=product, reviews=reviews)


@app.route("/signin", methods=["POST", "GET"])
def signin():
    if flask_login.current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = connect_dv()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}';")
        result = cursor.fetchone()

        if result is None:
            flash("Your username/password is incorrect")
        elif password != result["password"]:
            flash("Your username/password is incorrect")
        else:
            user = User(result["id"], result["username"], result["email"], result["full_name"])
            flask_login.login_user(user)

        cursor.close()
        conn.close()

    return render_template("signin.html.jinja")


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return ('/')


@app.route("/signup", methods=["POST", "GET"])
def signup(): 
    if flask_login.current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST": 
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]
        username = request.form["username"]
        phone = request.form["phone"]
        confirm_password = request.form["confirm_password"]

        if password == confirm_password:
            redirect("/signin")
        else:
            flash("Password does not match the confirmation.")
            return render_template("signup.html.jinja")

        conn = connect_dv()
        cursor = conn.cursor() 

        try:
            cursor.execute(f"""
                INSERT INTO `Customer` (`username`, `address`, `phone`, `password`, `full_name`, `email`)
                VALUES ('{username}', '{address}', '{phone}', '{password}', '{full_name}', '{email}');
            """)
        except pymysql.err.IntegrityError:
            flash("Sorry, that username/email is already in use.")
            return render_template("signup.html.jinja")
        else:
            return redirect("/signin")
        finally:
            cursor.close()
            conn.close()

    return render_template("signup.html.jinja")


@app.route("/cart")
@flask_login.login_required
def cart():
    conn = connect_dv()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.id
    cursor.execute(f"SELECT * FROM `cart` WHERE `customer_id` = {customer_id};")
    cursor.execute(f"""
     SELECT
     `name`,
     `price`,
     `cart`. `quantity`,  
     `image`, 
     `product_id`,
     `cart`.`id`
     FROM `cart`
     JOIN `Product` ON `product_id` = `Product`.`id`
     WHERE `customer_id` = {customer_id};
    """)

    results = cursor.fetchall() 
    cart_total = 0
    for item in results:
        cart_total += (item['price'] * item['quantity'])

    cursor.close()
    conn.close()  

    return render_template("cart.html.jinja", product=results, cart_total=cart_total)  


@app.route("/product/<product_id>/cart", methods=["POST"])
@flask_login.login_required
def add_to_cart(product_id):  
    quantity = request.form['quantity']
    customer_id = flask_login.current_user.id
    conn = connect_dv()
    cursor = conn.cursor() 

    cursor.execute("""
    INSERT INTO `cart` (`product_id`, `customer_id`, `quantity`)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
    `quantity` = `quantity` + %s
    """, (product_id, customer_id, quantity, quantity))     

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/cart")


@app.route("/cart/<cart_id>/del", methods=["POST"])
@flask_login.login_required
def delete_cart(cart_id):
    conn = connect_dv()
    cursor = conn.cursor()
    cursor.execute(f"""DELETE FROM `cart` WHERE `id` = {cart_id};""")  
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/cart") 


@app.route("/cart/<cart_id>/update", methods=["POST"])
@flask_login.login_required
def update_cart(cart_id):
    cart_item_quantity = request.form['quantity']
    conn = connect_dv()
    cursor = conn.cursor()
    cursor.execute(f"""UPDATE `cart` SET `quantity`= {cart_item_quantity} WHERE `id` = {cart_id};""")
    conn.commit()
    cursor.close()
    conn.close() 
    return redirect("/cart")


@app.route("/checkout")
@flask_login.login_required
def checkout_page():
    conn = connect_dv()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM cart WHERE customer_id = {flask_login.current_user.id}")
    cart_items = cursor







