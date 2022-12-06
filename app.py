# server.py

from flask import Flask, render_template, request, flash, redirect, url_for, session, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from bs4 import BeautifulSoup
import os
import requests
import openai
import hashlib

app = Flask(__name__)
# Create a Flask app instance

# Set the secret key for encrypting cookies
app.secret_key = bytes(os.environ.get('SECRET_KEY', ''), 'utf-8')

# Set the OpenAI API key
openai.api_key = os.environ.get('API_KEY')

#Set up the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'

    def check_password(self, password):
        return check_password_hash(self.password, password)

def hash(password, secret):
  # Create a new hash object
  h = hashlib.new('sha256')

  # Update the hash with the password and secret key
  h.update(password.encode('utf-8') + secret)

  # Return the hexadecimal digest of the hash
  return h.hexdigest()

def check_password_hash(hash_text, password):
  # Hash the password using the same secret key
  password_hash = hash(password, app.secret_key)

  # Compare the two hashes
  return password_hash == hash_text

@app.route('/')
def index():
    # Redirect unauthenticated users to the login page
    if not session.get('email'):
        return redirect(url_for('login'))

    # Check if the generate query string parameter is present
    generate = request.args.get('generate') is not None

    if generate:

        # Make a GET request to the New York Times front page
        response = requests.get('https://www.nytimes.com')

        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(response.text)

        # Extract the front page layout and article titles from the HTML
        layout = soup.find('div', class_='layout')
        article_titles = soup.find_all('h3', class_='indicate-hover')

        # Create a list of articles to pass to the template
        articles = []
        for title in article_titles[:20]:
            # Generate the AI-generated content for the article
            print(f"WRITING ARTICLE TITLED {title.text}")
            if not os.path.exists(f"{title.text}.txt"):
                completions = openai.Completion.create(
                    engine='text-davinci-003',
                    prompt=f"Write an article for the New York Times titled '{title.text}'",
                    max_tokens=1024,
                    temperature=0.5
                )

                # Save the AI-generated content to a file
                filename = f'{title.text}.txt'
                with open(filename, 'w') as f:
                    f.write(completions.choices[0].text)

            # Add the article to the list of articles
            text = ""
            with open(f"{title.text}.txt", "r") as f:
                text = f.read()
            articles.append({
                'title': title.text,
                'content': text
            })
    else:
        cwd = os.getcwd()

        # Extract the front page layout and article titles from the files in the current directory
        layout = ""
        article_titles = [f[:-4] for f in os.listdir(cwd) if f.endswith('.txt') and not f == "runtime.txt" and not f == requirements.txt]

        # Create a list of articles to pass to the template
        articles = []
        for title in article_titles[:20]:
            filename = f'{title}.txt'
            with open(filename, 'r') as f:
                text = f.read()
            # Add the article to the list of articles
            articles.append({
                'title': title,
                'content': text
            })
    return render_template('index.html', layout=layout, articles=articles, messages=get_flashed_messages(), title="NYTimes: OpenAI Edition")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Validate the form input and create a new user account
        email = request.form['email']
        password = request.form['password']

        # Validate the email and password and create a new user account
        if not email or not password:
            flash('Please enter a valid email and password')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash(f'User with email address ({email}) already present, login')
            return redirect(url_for('login'))

        # Create a new user account
        user = User(email=email, password=hash(password, app.secret_key))
        db.session.add(user)
        db.session.commit()

        flash('Successfully registered! You can now log in.')
        return redirect(url_for('login'))
    else:
        if 'email' in session:
            flash('Already logged in')
            return redirect('/')
        # Render the register.html template
        return render_template('register.html', messages=get_flashed_messages(), title="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Validate the form input and log the user in
        email = request.form['email']
        password = request.form['password']

        # Validate the email and password and log the user in
        if not email or not password:
            flash('Please enter a valid email and password')
            return redirect(url_for('login'))

        # Attempt to authenticate the user
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Incorrect email or password')
            return redirect(url_for('login'))

        # Log the user in
        session['email'] = email
        flash('Successfully logged in!')
        return redirect(url_for('index'))
    else:
        if 'email' in session:
            flash('Already logged in')
            return redirect('/')
        # Render the login.html template
        return render_template('login.html', messages=get_flashed_messages(), title="Log In")

@app.route('/logout')
def logout():
    # Remove the email from the session and redirect to the login page
    session.pop('email', None)
    flash('Successfully logged out!')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()

