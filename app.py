from flask import Flask, render_template, request, redirect, url_for, session,flash
from flask_mysqldb import MySQL
from sklearn.feature_extraction.text import CountVectorizer
import MySQLdb.cursors
import re
import numpy as np
import pandas as pd
import pickle
import os
import hashlib



app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = '1a2b3c4d5e'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'sentiment_TA'

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'csv'}
# define template (html file) location
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ## TEXT PROCESSING
df = pd.read_csv('static/data_train_nb_full.csv')

# load model
model = pickle.load(open('static/model_izza_new.pkl','rb'))

# vectorize the 'text' data
vectorizer = CountVectorizer(min_df=2, ngram_range=(1,4))
fit_vec = vectorizer.fit(df['Tweet'])

# class
sentiment_dict = {1:'Positive',0:'Neutral',2:'Negative'}


# Intialize MySQL
mysql = MySQL(app)

# http://localhost:5000/pythonlogin/ - this will be the login page, we need to use both GET and POST requests
@app.route('/', methods=['GET', 'POST'])
def login():
# Output message if something goes wrong...
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        hash_p = hashlib.md5(password.encode())
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, hash_p.hexdigest()))
        # Fetch one record and return result
        account = cursor.fetchone()
                # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            flash("Incorrect username/password!", "danger")
    return render_template('auth/login.html',title="Login")



# http://localhost:5000/pythinlogin/register 
# This will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        hash_p = hashlib.md5(password.encode())
        email = request.form['email']
                # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # cursor.execute('SELECT * FROM accounts WHERE username = %s', (username))
        cursor.execute( "SELECT * FROM accounts WHERE username LIKE %s", [username] )
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            flash("Account already exists!", "danger")
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash("Invalid email address!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash("Username must contain only characters and numbers!", "danger")
        elif not username or not password or not email:
            flash("Incorrect username/password!", "danger")
        else:
        # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (%s, %s, %s, %s)', (cursor.lastrowid, username,email, hash_p.hexdigest()))
            mysql.connection.commit()
            flash("You have successfully registered!", "success")
            return redirect(url_for('login'))

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash("Please fill out the form!", "danger")
    # Show registration form with message (if any)
    return render_template('auth/register.html',title="Register")

@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # cursor.execute('SELECT * FROM accounts WHERE username = %s', (username))
        cursor.execute("SELECT * FROM prediksi")
        data = cursor.fetchall()
        print(data)
        return render_template('home/home.html', data=data, title="Home")
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))    

@app.route('/prediksi', methods=['GET','POST'])
def prediksi():
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST' and 'a' in request.form:
            # get input text
            input_text = np.array([request.form['a']])
            print(input_text)
            # encode text
            encode_text = fit_vec.transform(input_text)
            # prediction
            prediction = model.predict(encode_text)
            tweet = request.form['a']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO prediksi VALUES (%s, %s, %s)', (cursor.lastrowid, tweet, prediction[0]))
            mysql.connection.commit()
            # User is loggedin show them the home page
            return render_template('home/prediksi.html', data=prediction[0], tweet=tweet, title="Prediksi")
        return render_template('home/prediksi.html', title="Prediksi")
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))  


@app.route('/upload', methods=['GET','POST'])
def upload():
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST':
            if os.path.exists("static/uploads/databaru.csv"):
                os.remove("static/uploads/databaru.csv")
            f = request.files['file']
            f.filename = "databaru.csv"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],f.filename))
            df = pd.read_csv('static/uploads/databaru.csv', sep=',')
            
            data_predict = list(df['Tweet'].values)
            input_text = np.array(data_predict)
            encode_text = fit_vec.transform(input_text)
            # prediction
            prediction = model.predict(encode_text)
            df2 = df.assign(prediksi = prediction)
            data = list(df2.values)
            return render_template('home/upload.html', data=data, title="Upload")
        # User is loggedin show them the home page
        return render_template('home/upload.html', title="Upload")
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('auth/profile.html', data=session,title="Profile")
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))  

@app.route('/logout')
def logout():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        session.clear()
        print(session)
        return render_template('auth/login.html', title="Logout")
    # User is not loggedin redirect to login page
    return redirect(url_for('login')) 

if __name__ =='__main__':
	app.run(debug=True)
