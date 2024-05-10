from datetime import  timedelta, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://chris:sirhc@172.16.181.31/fp180'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'accounts'
    User_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    Product_ID = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.Text, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    Price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)

    def __init__(self, Title, Description, Price, image_url, Quantity):
        self.Title = Title
        self.Description = Description
        self.Price = Price
        self.image_url = image_url
        self.Quantity = Quantity

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.User_ID'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Define the relationship with Product
    product = relationship('Product', backref='carts')

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            session['user_id'] = user.User_ID
            session.permanent = True
            if user.type == 'admin':
                return redirect(url_for('admin'))
            elif user.type == 'vendor':
                return redirect(url_for('vendor'))
            elif user.type == 'customer':
                return redirect(url_for('products'))
            else:
                flash('Invalid account type', 'error')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch the current user's cart items
    user_id = session['user_id']
    user = User.query.get(user_id)
    cart_items = user.carts  # Assuming 'carts' is the relationship name
    
    return render_template('cart.html', cart_items=cart_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    user_id = session['user_id']  # Get the user_id from the session

    # Extract product_id and quantity from the request
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])  # Convert quantity to integer

    # Now insert the product into the cart with the user_id
    cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
    db.session.add(cart_item)
    db.session.commit()

    flash('Product added to cart successfully', 'success')
    return redirect(url_for('cart'))  # Redirect to the cart page

from flask import flash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        account_type = request.form['account_type']
        
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'error')
            return redirect(url_for('register'))  # Redirect back to registration form
        
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            type=account_type
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.User_ID
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    products = Product.query.all()
    return render_template('products.html', user=user, products=products)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    cart_item_id = request.form['cart_item_id']

    # Retrieve the cart item from the database
    cart_item = Cart.query.get(cart_item_id)

    if cart_item:
        # Delete the cart item
        db.session.delete(cart_item)
        db.session.commit()
        flash('Product removed from cart successfully', 'success')
    else:
        flash('Failed to remove product from cart', 'error')

    # Redirect back to the cart page
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)