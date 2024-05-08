from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import flash


app = Flask(__name__)

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

@app.route('/products')
def show_products():
    all_products = Product.query.all()
    return render_template('products.html', items=all_products)  # Pass items instead of products


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.Quantity > 0:  # Ensure the product is in stock
        existing_item = Cart.query.filter_by(product_id=product_id).first()
        if existing_item:
            existing_item.quantity += 1
        else:
            new_item = Cart(product_id=product_id, quantity=1)
            db.session.add(new_item)
        product.Quantity -= 1
        db.session.commit()
        flash('Item added to cart', 'success')  # Flash success message
    else:
        flash('Item is out of stock', 'danger')  # Flash error message if item is out of stock
    return redirect(url_for('show_products'))

@app.route('/cart')
def show_cart():
    cart_items = Cart.query.all()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    db.session.delete(cart_item)
    db.session.commit()
    return redirect(url_for('show_cart'))

if __name__ == '__main__':
    app.run(debug=True)
