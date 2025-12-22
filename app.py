from flask import Flask, render_template, redirect, url_for, session, request, flash
import requests
import uuid
app = Flask(__name__)
app.secret_key = "secret123"

# ================= ADMIN CREDENTIALS =================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ================= GLOBAL STORAGE ====================
orders = []

MENU_ITEMS = [
    {
        "id": 1,
        "name": "Banku & Tilapia",
        "price": 45,
        "image": "banku.jpg",
        "description": "Freshly grilled tilapia served with soft banku and pepper"
    },
    {
        "id": 2,
        "name": "Yam & Palava Sauce",
        "price": 25,
        "image": "yam.jpg",
        "description": "Boiled yam with palava sauce"
    },
    {
        "id": 3,
        "name": "Jollof Rice & Chicken",
        "price": 30,
        "image": "jollof.jpg",
        "description": "Classic Ghanaian jollof with fried chicken"
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

# ================= CHECKOUT ==========================
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", [])

    if not cart:
        return redirect(url_for("cart_page"))

    total = sum(item["price"] for item in cart)

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        payment_method = request.form.get("payment_method")

        order = {
            "id": len(orders),
            "name": name,
            "phone": phone,
            "items": cart.copy(),   # IMPORTANT
            "total": total,
            "status": "Pending",
            "payment": payment_method,
            "status": "Awaiting Payment"
        }

        orders.append(order)
        session.pop("cart", None)

        return render_template("success.html", name=name, total=total)

    return render_template("checkout.html", cart=cart, total=total)

# ================= ADMIN ORDERS ======================
@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("orders.html", orders=orders)

# ================= ADMIN LOGIN =======================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_orders"))
        else:
            flash("Invalid admin credentials")

    return render_template("admin_login.html")

@app.route("/admin/order/<int:order_id>/status")
def update_order_status(order_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    for order in orders:
        if order["id"] == order_id:
            order["status"] = "Delivered" if order["status"] == "Pending" else "Pending"
            break

    return redirect(url_for("admin_orders"))

@app.route("/admin/order/<int:order_id>/delete", methods=["POST"])
def delete_order(order_id):
    global orders
    orders = [o for o in orders if o["id"] != order_id]

    return redirect(url_for("admin_orders"))

@app.route("/admin/confirm/<int:order_id>", methods=["POST"])
def confirm_payment(order_id):
    for order in orders:
        if order["id"] == order_id:
            order["status"] = "Paid"
    return redirect(url_for("admin_orders"))


# ================= ADMIN LOGOUT ======================
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
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
    app.run(debug=True)
