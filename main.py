from flask import Flask, render_template , request, redirect , flash 
import pymysql
from dynaconf import Dynaconf  

app = Flask(__name__) 

conf = Dynaconf(
    settings_file = ["settings.toml"] 
) 

app.secret_key = conf.secret_key 

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
     cursor.close() 
     conn.close() 

     return render_template("product.html.jinja", product = result)  
@app.route("/signin")
def signin(): 
     return render_template("signin.html.jinja") 

@app.route("/signup", methods = ["POST", "GET"])  
def signup(): 
     
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


    
    

