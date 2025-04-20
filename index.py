from datetime import timedelta, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'accounts'
    User_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(45), unique=True, nullable=False)
    username = db.Column(db.String(45), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)
    carts = db.relationship('Cart', backref='user', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    Product_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.Text, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)
    warranty = db.Column(db.String(45))
    discount = db.Column(db.String(45))
    vendor_id = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(45))
    size = db.Column(db.String(45))

class Review(db.Model):
    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    reviewer_name = db.Column(db.String(255), nullable=False)

    def __init__(self, product_id, rating, description, reviewer_name):
        self.product_id = product_id
        self.rating = rating
        self.description = description
        self.reviewer_name = reviewer_name

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('accounts.User_ID'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    product = db.relationship('Product', backref='cart_items', lazy=True)

class OrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_num = db.Column(db.Integer, nullable=False)
    items = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        account = User.query.filter_by(username=username, password=password).first()
        
        if account:
            session['user_id'] = account.User_ID
            session.permanent = True
            if account.type == 'admin':
                return redirect(url_for('admin'))
            elif account.type == 'vendor':
                return redirect(url_for('vendor'))
            elif account.type == 'customer':
                return redirect(url_for('products'))
            else:
                flash('Invalid account type', 'error')
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    total_price = 0

    for item in cart_items:
        product = Product.query.get(item.product_id)
        if not product:
            flash(f'Product not found for cart item ID: {item.id}', 'error')
            return redirect(url_for('home'))

        item.product = product

        # Process discount 
        discount_percentage = 0
        if product.discount:
            try:
                discount_clean = product.discount.strip().replace('%', '')
                discount_percentage = float(discount_clean) / 100
            except ValueError:
                discount_percentage = 0

        discounted_price = float(product.price) * (1 - discount_percentage)
        item.discounted_price = round(discounted_price, 2)
        item.total_price = round(item.quantity * item.discounted_price, 2)

        total_price += item.total_price

    total_price = round(total_price, 2)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/proceed_to_payment', methods=['GET', 'POST'])
def proceed_to_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        user = User.query.get(user_id)
        cart_items = user.carts  

        items = []
        total_price = 0

        for item in cart_items:
            product = item.product
            if not product or product.price is None:
                flash(f'Invalid product or missing price for "{product.Title}".', 'error')
                return redirect(url_for('cart'))

            if product.Quantity < item.quantity:
                flash(f'Not enough stock for "{product.Title}". Available: {product.Quantity}', 'error')
                return redirect(url_for('cart'))

            # Reduce stock
            product.Quantity -= item.quantity

            # Calculate discount
            try:
                discount_clean = product.discount.strip().replace('%', '') if product.discount else '0'
                discount_percentage = float(discount_clean) / 100
            except ValueError:
                discount_percentage = 0

            discounted_price = float(product.price) * (1 - discount_percentage)
            item_total = round(discounted_price * item.quantity, 2)
            total_price += item_total

            items.append(f"{product.Title} (x{item.quantity}) @ ${discounted_price:.2f}")

        # Create order
        order = OrderStatus(
            order_num=generate_order_number(),
            items=', '.join(items),
            total_price=f"${total_price:.2f}",
            status='Pending'
        )
        db.session.add(order)
        db.session.commit()

        # Clear cart
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        flash('Payment processed successfully. Your order has been placed.', 'success')
        return redirect(url_for('order_receipt', order_num=order.order_num))

    return render_template('payment_form.html')



def generate_order_number():
    return int(datetime.now().timestamp())

@app.route('/order_receipt/<int:order_num>')
def order_receipt(order_num):
    order = OrderStatus.query.filter_by(order_num=order_num).first()
    if order:
        return render_template('order_receipt.html', order=order)
    else:
        flash('Invalid order number', 'error')
        return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    user_id = session['user_id']  

    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])  

    product = Product.query.get(product_id)
    if product:
        if product.price is None:
            flash(f'Price for product "{product.Title}" is not set. Please contact support.', 'error')
            return redirect(url_for('home'))

        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity, price=product.price)
        db.session.add(cart_item)
        db.session.commit()

        flash('Product added to cart successfully', 'success')
    else:
        flash('Product not found', 'error')
    
    return redirect(url_for('cart'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        account_type = request.form['account_type']
        firstName = request.form.get('first_name')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'error')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username,
            first_name=firstName,
            email=email,
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

@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product_details.html', product=product, reviews=reviews)


@app.route('/write_review/<int:product_id>', methods=['GET', 'POST'])
def write_review(product_id):
    if request.method == 'POST':
        rating = request.form['rating']
        description = request.form['description']
        reviewer_name = request.form['reviewer_name']
        
        review = Review(product_id=product_id, rating=rating, description=description, reviewer_name=reviewer_name)
        
        db.session.add(review)
        db.session.commit()
        
        return redirect(url_for('product_details', product_id=product_id))
    
    return render_template('write_review.html', product_id=product_id)

@app.route('/product/<int:product_id>/reviews')
def product_reviews(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product_reviews.html', product=product, reviews=reviews)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    cart_item_id = request.form['cart_item_id']
    
    cart_item = Cart.query.get(cart_item_id)

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Product removed from cart successfully', 'success')
    else:
        flash('Failed to remove product from cart', 'error')

    return redirect(url_for('cart'))

@app.route('/vendor')
def vendor():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    products = Product.query.filter_by(vendor_id=user.User_ID).all()

    return render_template('vendor.html', user=user, products=products)

@app.route('/update_price', methods=['POST'])
def update_price():
    if 'user_id' not in session or User.query.get(session['user_id']).type not in ['vendor', 'admin']:
        return redirect(url_for('login'))

    for key, value in request.form.items():
        if key.startswith('price_'):
            product_id = int(key.split('_')[1])
            product = Product.query.get(product_id)
            if product:
                product.price = float(value)
                db.session.commit()

    flash('Prices updated successfully', 'success')

    # Redirect based on user type
    if User.query.get(session['user_id']).type == 'vendor':
        return redirect(url_for('vendor'))
    else:
        return redirect(url_for('admin'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.type not in ['vendor', 'admin']:
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    quantity = request.form['quantity']
    warranty = request.form['warranty']
    discount = request.form['discount']
    size = request.form['size']
    color = request.form['color']

    if user.type == 'vendor':
        vendor_id = user.User_ID
    else:
        vendor_id = request.form['vendor_id']

    new_product = Product(
        Title=title,
        Description=description,
        price=price,
        image_url=image_url,
        Quantity=quantity,
        warranty=warranty,
        discount=discount,
        vendor_id=vendor_id,
        size=size,
        color=color
    )

    db.session.add(new_product)
    db.session.commit()

    flash('Product added successfully', 'success')

    if user.type == 'vendor':
        return redirect(url_for('vendor'))
    else:
        return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if 'user_id' not in session or User.query.get(session['user_id']).type != 'admin':
        return redirect(url_for('login'))

    products = Product.query.all()

    return render_template('admin.html', products=products)
    
if __name__ == '__main__':
    app.run(debug=True)
