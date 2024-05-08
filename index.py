from flask import Flask, redirect, url_for, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://chris:sirhc@172.16.181.82/fp180'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://chris:sirhc@172.16.181.82/fp180'
db = SQLAlchemy(app)

class Product(db.Model):
    __tablename__ = 'products'
    Product_ID = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.Text, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    Price = db.Column(db.Numeric(10, 2), nullable=False)  # Use db.Numeric for decimals
    image_url = db.Column(db.Text, nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)

    def __init__(self, Title, Description, Price, image_url, Quantity):
        self.Title = Title
        self.Description = Description
        self.Price = Price  # Price is now a decimal type, so no conversion is needed
        self.image_url = image_url
        self.Quantity = Quantity



class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/home')
def base():
    return render_template('base.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register ():
    return render_template('register.html')

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    csrf_token = generate_csrf()
    return render_template('products.html', user=user, csrf_token=csrf_token)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)