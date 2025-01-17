from flask import Flask, render_template, request, redirect, flash, abort
import flask_login
import pymysql
from datetime import datetime  
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
        cursor.execute(f"SELECT * FROM `Product` WHERE `name` LIKE '%{query}%' OR `description` LIKE '%{query}%'")  

    results = cursor.fetchall()
    cursor.close()
    conn.close() 

    return render_template("browse.html.jinja", products=results)


@app.route("/product/<product_id>/", methods=["GET", "POST"])
@flask_login.login_required
def product_detail(product_id):
    conn = connect_dv()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT * FROM `Product` WHERE `id` = {product_id};
    """) 
    product = cursor.fetchone()

    cursor.execute(f"""
        SELECT r.rating, r.comment, r.timestamp, c.username
        FROM `Review` r
        JOIN `Customer` c ON r.customer_id = c.id
        WHERE r.product_id = {product_id}
        ORDER BY r.timestamp DESC;
    """)          

    product = cursor.fetchall()

    if request.method == "POST":
       
        customer_id = flask_login.current_user.id
        cursor.execute(f"SELECT * FROM `Review` WHERE `product_id` = '{product_id}' AND `customer_id` = '{customer_id}';")
        existing_review = cursor.fetchone()

        if existing_review:
            flash("You have already submitted a review for this product.", "error")
        else:
            rating = request.form["rating"]
            comment = request.form["comment"] 
            timestamp = datetime.now() 
            
            cursor.execute(f"""
                INSERT INTO `Review` (`product_id`, `customer_id`, `rating`, `comment`, `timestamp`)
                VALUES ('{product_id}', '{customer_id}', '{rating}', '{comment}', '{timestamp}');
            """)
            conn.commit()      
            
            flash("Your review has been submitted!", "success")
            return redirect(f"/product/{product_id}") 

    cursor.close()
    conn.close()

    return render_template("product.html.jinja", product = product,) 

@app.route("/addreview/<product_id>/", methods =["GET", "POST"])
def addreview(product_id): 
    conn = connect_dv()
    cursor = conn.cursor() 
    rating = request.form["rating"]
    comment = request.form["comment"] 
    timestamp = datetime.now() 
    customer_id = flask_login.current_user.id 
    cursor.execute(f"""
                INSERT INTO `Review` (`product_id`, `customer_id`, `rating`, `comment`, `timestamp`)
                VALUES
                    ('{product_id}', '{customer_id}', '{rating}', '{comment}','{timestamp}')
                    ON DUPLICATE KEY UPDATE `comment`= '{comment}', rating = '{rating}';   
            """,) 
    conn.close()      
    cursor.close() 
    return render_template("product.html.jinja")    

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
    return redirect('/')


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
    cursor.execute(f"""        
        SELECT
        `name`, `price`, `cart`.`quantity`, `image`, `product_id`, `cart`.`id`
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

    return render_template("cart.html.jinja", products=results, cart_total=cart_total)


@app.route("/product/<product_id>/cart", methods=["POST"])
@flask_login.login_required
def add_to_cart(product_id):
    
    quantity = request.form.get('quantity', type=int, default=1)
    customer_id = flask_login.current_user.id

    conn = connect_dv() 
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM `cart` WHERE `customer_id` = %s AND `product_id` = %s;
        """, (customer_id, product_id))
        existing_item = cursor.fetchone() 

        if existing_item:
            cursor.execute("""
                UPDATE `cart`
                SET `quantity` = `quantity` + %s
                WHERE `id` = %s;
            """, (quantity, existing_item['id']))
        else:
            cursor.execute("""
                INSERT INTO `cart` (`product_id`, `customer_id`, `quantity`)
                VALUES (%s, %s, %s);
            """, (product_id, customer_id, quantity))

        conn.commit()
        flash('Item successfully added to the cart!', 'success')
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        flash('There was an error adding the item to the cart.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect("/cart")


@app.route("/cart/<cart_id>/delete", methods=["POST"])
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
    customer_id = flask_login.current_user.id

    cursor.execute(f"""
        SELECT p.name, p.price, c.quantity
        FROM cart c
        JOIN Product p ON c.product_id = p.id
        WHERE c.customer_id = {customer_id};
    """) 
    cart_items = cursor.fetchall()
    
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    cursor.close() 
    conn.close()        
    
    return render_template("checkout.html.jinja", cart_items=cart_items, total_amount=total_amount)

@app.route("/complete_checkout", methods=["POST"])
@flask_login.login_required
def complete_checkout():
    flash("Thank you for your purchase! Your order has been placed.", "success")
    return redirect("/") 







