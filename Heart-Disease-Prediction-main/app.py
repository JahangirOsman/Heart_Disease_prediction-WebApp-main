from flask import Flask, render_template, request # type: ignore
import numpy as np
import pandas as pd
import joblib
import os
import plotly.express as px
import plotly.io as pio
import sqlite3
from werkzeug.security import generate_password_hash # type: ignore
import mysql.connector # type: ignore
from mysql.connector import Error # type: ignore
from werkzeug.security import check_password_hash # type: ignore


# Load the model
location = os.path.dirname(__file__)
fullpath = os.path.join(location, 'hdp_model.pkl')
model = joblib.load(fullpath)

# Load the dataset for visualization
data_path = os.path.join(location, 'hdp_data.csv')
hdp_data = pd.read_csv(data_path)

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DATABASE = "hdp_application"

# Initialize the Flask app
app = Flask(__name__)

def create_mysql_connection():
    """Creates and returns a MySQL connection"""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        if conn.is_connected():
            print("Connected to MySQL database")
        return conn
    except Error as e:
        print("Error connecting to MySQL:", e)
        return None

def init_db():
    conn = sqlite3.connect('users.db')  # Create or connect to SQLite database
    cursor = conn.cursor()

    # Create the `users` table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route("/")
def home():
    # Main page with a new visualization button
    return render_template("index.html")
    

@app.route("/detail", methods=["POST","GET"])
def submit():
    if request.method == "POST":
        # Get form data
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate input
        if not email or not password:
            return render_template("detail.html", message="Both email and password are required.")

        try:
            # Connect to the database
            conn = create_mysql_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)

                # Check if the user exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()

                if user:
                    # Verify the password
                    if check_password_hash(user["password"], password):
                        return render_template("detail.html", message="Login successful!")
                    else:
                        # Incorrect password
                        return render_template("index.html", message="Invalid password!")
                else:
                    # User not found
                    return render_template("index.html", message="Email not registered.")
        except Error as e:
            print("Database error:", e)
            return render_template("index.html", message="An error occurred. Please try again.")
        finally:
            if conn:
                cursor.close()
                conn.close()
    return render_template("detail.html")

@app.route('/predict', methods=["POST"])
def predict():
    if request.method == "POST":
        values = np.array([[int(request.form['age']),
                            int(request.form['sex']),
                            int(request.form['cp']),
                            int(request.form['trestbps']),
                            int(request.form['chol']),
                            int(request.form['fbs']),
                            int(request.form['restecg']),
                            int(request.form['thalach']),
                            int(request.form['exang']),
                            float(request.form['oldpeak']),
                            int(request.form['slope']),
                            int(request.form['ca']),
                            int(request.form['thal'])]])

        prediction = model.predict(values)
        return render_template('predict.html', prediction=prediction)

@app.route("/visualization")
def visualization():
    # Graph 1: Scatter Plot - Age vs. Cholesterol
    fig1 = px.scatter(hdp_data, x='age', y='chol', 
                      title='Cholesterol Levels by Age',
                      labels={'age': 'Age', 'chol': 'Cholesterol'},
                      color='sex', template='plotly_dark')

    # Graph 2: Bar Plot - Chest Pain Type Distribution
    fig2 = px.bar(hdp_data['cp'].value_counts().reset_index(), 
                  x='index', y='cp', 
                  title='Chest Pain Type Distribution',
                  labels={'index': 'Chest Pain Type', 'cp': 'Count'},
                  template='plotly_dark')

    # Graph 3: Histogram - Max Heart Rate Distribution
    fig3 = px.histogram(hdp_data, x='thalach', 
                        title='Distribution of Max Heart Rate',
                        labels={'thalach': 'Max Heart Rate'},
                        template='plotly_dark')

    # Graph 4: Box Plot - Cholesterol Levels by Sex
    fig4 = px.box(hdp_data, x='sex', y='chol', 
                  title='Cholesterol Levels by Sex',
                  labels={'sex': 'Sex (0=Female, 1=Male)', 'chol': 'Cholesterol'},
                  template='plotly_dark')

    # Convert plots to HTML
    plots = [pio.to_html(fig, full_html=False) for fig in [fig1, fig2, fig3, fig4]]

    return render_template('visualization.html', plots=plots)
    
@app.route("/register")
def register():
    return render_template('register.html')
    

@app.route("/register-redirect", methods=["POST"])
def register_redirect():
    if request.method == "POST":
        # Get form data
        username = request.form.get("Username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Hash the password for security
        hashed_password = generate_password_hash(password, method='sha256')

        # Save data to MySQL
        try:
            conn = create_mysql_connection()
            if conn:
                cursor = conn.cursor()

                # Insert user into the database
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )
                conn.commit()
                cursor.close()
                conn.close()

                # Success message
                return render_template("index.html", alert="Registration successful!")
        except Error as e:
            if "Duplicate entry" in str(e):
                # Handle duplicate email error
                return render_template("index.html", alert="Email already exists. Try a different one.")
            print("Database error:", e)
            return render_template("index.html", alert="An error occurred. Please try again.")



if __name__ == "__main__":
    create_mysql_connection()  # Initialize the database before running the app
    app.run(debug=True)
