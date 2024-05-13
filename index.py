from datetime import timedelta, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://chris:sirhc@172.16.180.214/fp180'
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
    review_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text)
    reviewer_name = db.Column(db.String(255), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('accounts.User_ID'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.Product_ID'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Add a price column
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
        
        if account:  # Check if account exists
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
            return redirect(url_for('login'))  # Redirect back to the login page
    
    # Render the login form template
    return render_template('login.html')


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    cart_items = Cart.query.filter_by(user_id=user_id).all()  # Retrieve all cart items for the user
    
    total_price = 0
    
    for item in cart_items:
        product = Product.query.get(item.product_id)  # Retrieve the product associated with the cart item
        if product is None:
            flash(f'Product not found for cart item with ID: {item.id}', 'error')
            return redirect(url_for('home'))
        
        # Add the product information to the cart item
        item.product = product
        
        # Calculate the total price for each item in the cart
        item.total_price = item.quantity * product.price
        total_price += item.total_price
    
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
            if product.price is None:
                flash(f'Price for item "{product.Title}" is not set. Please contact support.', 'error')
                return redirect(url_for('cart'))

            total_price += product.price * item.quantity
            items.append(f"{product.Title} (Quantity: {item.quantity})")

        # Create order status object
        order = OrderStatus(order_num=generate_order_number(), items=', '.join(items), total_price=f"${total_price:.2f}", status='Pending')
        db.session.add(order)
        db.session.commit()

        # Clear the cart after order placement
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        flash('Payment processed successfully. Your order has been placed.', 'success')
        return redirect(url_for('order_receipt', order_num=order.order_num))

    return render_template('payment_form.html')

def generate_order_number():
    # Generate a unique order number (you can implement your own logic)
    # For example, you can use a combination of timestamp and user ID
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
        # Check if the product price is None or not properly set
        if product.price is None:
            flash(f'Price for product "{product.Title}" is not set. Please contact support.', 'error')
            return redirect(url_for('home'))

        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity, price=product.price)
        db.session.add(cart_item)
        db.session.commit()

        flash('Product added to cart successfully', 'success')
    else:
        flash('Product not found', 'error')
    
    return redirect(url_for('cart'))  # Redirect to the cart page after adding the item

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
            first_name=first_name,  # Adjust field name
            last_name=last_name,    # Adjust field name
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

@app.route('/product/<int:product_id>/write_review', methods=['GET', 'POST'])
def write_review(product_id):
    product_image_url = request.args.get('product_image_url')
    if request.method == 'POST':
        rating = request.form['rating']
        description = request.form['description']
        reviewer_name = request.form['reviewer_name']
        
        # Now you have all the necessary data to save the review to the database
        # You can use the product_image_url, rating, description, reviewer_name, and product_id to save the review
        
        flash('Review added successfully', 'success')
        return redirect(url_for('product_details', product_id=product_id))
    
    return render_template('write_review.html', product_id=product_id, product_image_url=product_image_url)


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

    # Get the logged-in user
    user = User.query.get(session['user_id'])

    # Query products associated with the vendor
    products = Product.query.filter_by(vendor_id=user.User_ID).all()

    return render_template('vendor.html', user=user, products=products)

@app.route('/update_price', methods=['POST'])
def update_price():
    if 'user_id' not in session or User.query.get(session['user_id']).type != 'vendor':
        return redirect(url_for('login'))

    for key, value in request.form.items():
        if key.startswith('price_'):
            product_id = int(key.split('_')[1])
            product = Product.query.get(product_id)
            if product:
                product.price = float(value)
                db.session.commit()

    flash('Prices updated successfully', 'success')
    return redirect(url_for('vendor'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or User.query.get(session['user_id']).type != 'vendor':
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

    vendor_id = session['user_id']  # Assuming vendor_id is linked to the vendor logged in

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
    return redirect(url_for('vendor'))

if __name__ == '__main__':
    app.run(debug=True)