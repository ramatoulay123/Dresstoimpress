from flask import Flask, render_template , request, redirect , flash, abort
import flask_login
import pymysql
from dynaconf import Dynaconf  

app = Flask(__name__) 

conf = Dynaconf(
    settings_file = ["settings.toml"] 
) 

app.secret_key = conf.secret_key 
login_manager= flask_login.LoginManager() 
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

    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id}; ")

    result = cursor.fetchone() 
    cursor.close()
    conn.close() 

    if result is not None:
        return User(result["id"], result["username"], result["email"], result["full_name"]) 
     
          

def connect_dv():
    conn = pymysql.connect( 
        host = "10.100.34.80",
        database = "rbarry_Dresstoimpress" ,
        user = "rbarry",
        password = conf.password, 
        autocommit= True, 
        cursorclass= pymysql.cursors.DictCursor
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

           cursor.execute(f"SELECT * FROM `Product` WHERE `name` LIKE '%{query}%' OR `description` ; ")   

    results = cursor.fetchall() 

    cursor.close()
    conn.close()  


    return render_template("browse.html.jinja", products = results)  


@app.route("/product/<product_id>")

def product_page(product_id): 
     

     conn = connect_dv()
     cursor = conn.cursor() 

     cursor.execute(f"SELECT * FROM `Product` WHERE `id` = {product_id};") 

     result = cursor.fetchone() 
     if result is None: 
        abort(404)
     cursor.close() 
     conn.close() 

     return render_template("product.html.jinja", product = result)  
@app.route("/signin", methods = ["POST", "GET"]) 
def signin():
      if flask_login.current_user.is_authenticated:
         return redirect("/")
      else:  
       if request.method == "POST" :   
        username = request.form["username"].strip()     
        password = request.form["password"]     

        conn = connect_dv()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}';") 
        result = cursor.fetchone() 
        if result is None:
             
             flash("your username/password is incorrect") 

        elif password != result["password"]: 
             flash("your username/password is incorrect")
        else: 
             user = User(result["id"], result["username"], result["email"], result["full_name"]) 
             flask_login.login_user(user)

             return redirect('/')
        

@app.route('/logout')

def logout(): 
     flask_login.logout_user() 
     return ('/')

@app.route("/signup", methods = ["POST", "GET"])  
def signup():  
    if flask_login.current_user.is_authenticated:
         return redirect("/")
    else:
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
             flash("password is not the same") 

             return render_template("signup.html.jinja")
             

        conn = connect_dv() 
        cursor = conn.cursor()  

        try: 
            cursor.execute(f"""
                INSERT INTO `Customer` 
                (  `username`, `address`,`phone`, `password`, `full_name`, `email`  )
                Values
                ( '{username}', '{address}', '{phone}', '{password}', '{full_name}', '{email}' )
            """)

        except pymysql.err.IntegrityError:
                flash("sorry that username/email is already in use")
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
      `qty`,
      `image`,
      `product_id`,
      `Cart`.`id` 
      FROM `Cart`
      JOIN `Product` ON `product_id` = `Product`.`id`
      WHERE `customer_id = 12 
     """
         
     )
     results = cursor.fetchall() 
    
     cursor.close() 
     conn.close() 

     


     return render_template("cart.html.jinja", products = results)  