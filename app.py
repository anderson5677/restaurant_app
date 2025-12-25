from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = "super-secret-admin-key-123"

import os

basedir = os.path.abspath(os.path.dirname(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "database.db")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= ADMIN CREDENTIALS =================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ================= MODELS =================
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    status = db.Column(db.String(20), default="Pending")

    items = db.relationship("OrderItem", backref="order", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

MENU_ITEMS = [
    {
        "id": 1,
        "name": "Banku & Tilapia",
        "description": "Fresh grilled tilapia served with banku and hot pepper",
        "price": 45,
        "quantity": 1,
        "image": "banku.jpg"
    },
    {
        "id": 2,
        "name": "Jollof Rice & Chicken",
        "description": "Classic Ghanaian jollof rice with fried chicken",
        "price": 30,
        "quantity": 1,
        "image": "jollof.jpg"
    },
    {
        "id": 3,
        "name": "Yam & Palava Sauce",
        "description": "Boiled yam served with palava sauce",
        "price": 25,
        "quantity": 1,
        "image": "yam.jpg"
    },
    {
        "id": 4,
        "name": "Fried Rice & Chicken",
        "description": "Vegetable fried rice with crispy chicken",
        "price": 35,
        "quantity": 1,
        "image": "fried.jpg"
    },
    {
        "id": 5,
        "name": "Waakye Special",
        "description": "Waakye with spaghetti, egg, gari, fish and shito",
        "price": 30,
        "quantity": 1,
        "image": "waakye.jpg"
    },
    {
        "id": 6,
        "name": "Plain Rice & Stew",
        "description": "White rice served with tomato stew and meat",
        "price": 20,
        "quantity": 1,
        "image": "plain.jpg"
    },
    {
        "id": 7,
        "name": "Kelewele",
        "description": "Spicy fried ripe plantain",
        "price": 15,
        "quantity": 1,
        "image": "kelewele.jpg"
    },
    {
        "id": 8,
        "name": "Chicken Shawarma",
        "description": "Grilled chicken shawarma with sauce",
        "price": 25,
        "quantity": 1,
        "image": "chicken.jpg"
    },
    {
        "id": 9,
        "name": "Indomie & Egg",
        "description": "Stir-fried indomie noodles with egg",
        "price": 15,
        "quantity": 1,
        "image": "indomie.jpg"
    },
    {
        "id": 10,
        "name": "Assorted Fried Meat",
        "description": "Fried beef, gizzard and sausage",
        "price": 20,
        "quantity": 1,
        "image": "assorted.jpg"
    }
]

# ================= HOME ==============================
@app.route("/")
def home():
    return render_template("home.html")

# ================= MENU ==============================
@app.route("/menu")
def menu():
    return render_template("menu.html", foods=MENU_ITEMS)

# ================= CART COUNT ========================
@app.context_processor
def inject_cart_count():
    cart = session.get("cart", [])
    return dict(cart_count=len(cart))

# ================= ADD TO CART =======================
@app.route("/add-to-cart/<int:item_id>")
def add_to_cart(item_id):
    qty = int(request.args.get("qty", 1))
    cart = session.get("cart", [])

    for food in MENU_ITEMS:
        if food["id"] == item_id:
            for _ in range(qty):
                cart.append(food)

    session["cart"] = cart
    return redirect(url_for("menu"))

# ================= CART ==============================
@app.route("/cart")
def cart_page():
    cart = session.get("cart", [])
    total = sum(item["price"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

# ================= REMOVE ITEM =======================
@app.route("/remove/<int:index>")
def remove_item(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
    session["cart"] = cart
    return redirect(url_for("cart_page"))

@app.route("/success/<int:order_id>")
def success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("success.html", order=order)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", [])

    if not cart:
        flash("Your cart is empty")
        return redirect(url_for("menu"))

    total_price = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 1))
        for item in cart
    )

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")

        order = Order(
            name=name,
            phone=phone,
            total=total_price,
            status="Pending"
        )

        db.session.add(order)
        db.session.commit()

        order.order_number = f"AF-{order.id:06d}"

        db.session.commit()

        for item in cart:
            db.session.add(OrderItem(
                order_id=order.id,
                name=item.get("name"),
                price=float(item.get("price", 0)),
                quantity=int(item.get("quantity", 1))
            ))

        db.session.commit()
        session.pop("cart", None)

        return redirect(url_for("success", order_id=order.id))

    return render_template("checkout.html", cart=cart, total=total_price)
# ================= ADMIN ORDERS ======================
@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders)

# ================= ADMIN LOGIN =======================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        print("LOGIN:", username, password)   # DEBUG
        print("SESSION BEFORE:", dict(session))

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["is_admin"] = True

            print("SESSION AFTER:", dict(session))  # DEBUG

            return redirect(url_for("admin_orders"))

        return render_template("admin_login.html", error="Invalid credentials")

    return render_template("admin_login.html")

from sqlalchemy import func
from datetime import date

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_sales = db.session.query(func.sum(Order.total)).scalar() or 0
    total_orders = Order.query.count()
    completed_orders = Order.query.filter_by(status="Completed").count()
    pending_orders = Order.query.filter_by(status="Pending").count()

    today_sales = (
        db.session.query(func.sum(Order.total))
        .filter(func.date(Order.created_at) == date.today())
        .scalar()
    ) or 0

    return render_template(
        "admin_dashboard.html",
        total_sales=total_sales,
        total_orders=total_orders,
        completed_orders=completed_orders,
        pending_orders=pending_orders,
        today_sales=today_sales
    )


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)

    # Toggle status
    if order.status == "Pending":
        order.status = "Completed"
    else:
        order.status = "Pending"

    db.session.commit()
    return redirect(url_for("admin_orders"))

@app.route("/admin/order/<int:order_id>/delete", methods=["POST"])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)

    # delete related order items first (important)
    OrderItem.query.filter_by(order_id=order.id).delete()

    db.session.delete(order)
    db.session.commit()

    flash("Order deleted successfully", "success")
    return redirect(url_for("admin_orders"))

@app.route("/admin/confirm/<int:order_id>", methods=["POST"])
def confirm_payment(order_id):
    order = Order.query.get_or_404(order_id)

    order.payment = "Confirmed"
    db.session.commit()

    flash("Payment confirmed", "success")
    return redirect(url_for("admin_orders"))


# ================= ADMIN LOGOUT ======================
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

PAYSTACK_SECRET = "sk_test_xxxxxxxxxxxxxx"

@app.route("/pay", methods=["POST"])
def pay():
    email = request.form.get("email")
    amount = int(float(request.form.get("amount")) * 100)  # pesewas

    reference = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json"
    }

    data = {
        "email": email,
        "amount": amount,
        "reference": reference,
        "channels": ["mobile_money"],
        "metadata": {
            "custom_fields": [
                {
                    "display_name": "Payment Method",
                    "variable_name": "payment_method",
                    "value": "MTN MoMo"
                }
            ]
        }
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=data,
        headers=headers
    )

    res = response.json()
    return redirect(res["data"]["authorization_url"])

@app.route("/verify/<reference>")
def verify(reference):
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}"
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    )

    res = response.json()

    if res["data"]["status"] == "success":
        return "Payment Successful!"
    else:
        return "Payment Failed"


# ================= RUN APP ===========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
