from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

def get_db():
    return sqlite3.connect("database.db")

# ---------- UNIT SYSTEM ---------- #
def convert_to_base(qty, unit):
    unit = unit.lower()

    if unit == "kg": return qty * 1000, "g"
    if unit == "g": return qty, "g"

    if unit == "l": return qty * 1000, "ml"
    if unit == "ml": return qty, "ml"

    if unit == "pieces": return qty, "pieces"

    return qty, unit


def format_display(qty, unit):
    if unit == "g" and qty >= 1000:
        return f"{qty/1000:.2f} kg"
    if unit == "ml" and qty >= 1000:
        return f"{qty/1000:.2f} L"
    return f"{qty:.0f} {unit}"


# ---------- DATABASE ---------- #
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory(
        name TEXT PRIMARY KEY,
        quantity REAL,
        unit TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dish_name TEXT,
        ingredient TEXT,
        quantity REAL,
        unit TEXT
    )
    """)

    cur.execute("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)")

    cur.execute("SELECT * FROM users")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES ('admin','admin')")

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ---------- #
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = u
            return redirect('/')
        return "Invalid Login"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------- HOME ---------- #
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html')


# ---------- INVENTORY ---------- #
@app.route('/inventory', methods=['GET','POST'])
def inventory():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name','').lower()
        qty = float(request.form.get('quantity',0))
        unit = request.form.get('unit','g')

        qty, unit = convert_to_base(qty, unit)

        cur.execute("SELECT * FROM inventory WHERE name=?", (name,))
        if cur.fetchone():
            cur.execute("UPDATE inventory SET quantity = quantity + ? WHERE name=?", (qty,name))
        else:
            cur.execute("INSERT INTO inventory VALUES (?,?,?)",(name,qty,unit))

        conn.commit()

    cur.execute("SELECT * FROM inventory")
    data = cur.fetchall()
    conn.close()

    return render_template('inventory.html', data=data)


@app.route('/delete_inventory/<name>')
def delete_inventory(name):
    conn = get_db()
    conn.execute("DELETE FROM inventory WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return redirect('/inventory')


@app.route('/edit_inventory/<name>', methods=['GET','POST'])
def edit_inventory(name):
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        qty = float(request.form.get('quantity',0))
        unit = request.form.get('unit','g')

        qty, unit = convert_to_base(qty, unit)

        cur.execute("UPDATE inventory SET quantity=?, unit=? WHERE name=?", (qty,unit,name))
        conn.commit()
        conn.close()
        return redirect('/inventory')

    cur.execute("SELECT * FROM inventory WHERE name=?", (name,))
    item = cur.fetchone()
    conn.close()

    return render_template('edit_inventory.html', item=item)


# ---------- DISH ---------- #
@app.route('/recipe')
def recipe():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT dish_name FROM recipes")
    dishes = cur.fetchall()
    conn.close()
    return render_template('recipe.html', dishes=dishes)


@app.route('/create_dish', methods=['GET','POST'])
def create_dish():
    if request.method == 'POST':
        dish = request.form.get('dish','').lower()

        conn = get_db()
        conn.execute("INSERT INTO recipes (dish_name,ingredient,quantity,unit) VALUES (?, '',0,'g')",(dish,))
        conn.commit()
        conn.close()
        return redirect('/recipe')

    return render_template('create_dish.html')


@app.route('/delete_dish/<dish>')
def delete_dish(dish):
    conn = get_db()
    conn.execute("DELETE FROM recipes WHERE dish_name=?", (dish,))
    conn.commit()
    conn.close()
    return redirect('/recipe')


# ---------- INGREDIENT ---------- #
@app.route('/dish/<dish>', methods=['GET','POST'])
def dish_detail(dish):
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        ing = request.form.get('ingredient','').lower()
        qty = float(request.form.get('quantity',0))
        unit = request.form.get('unit','g')

        qty, unit = convert_to_base(qty, unit)

        cur.execute("INSERT INTO recipes VALUES (NULL,?,?,?,?)",(dish,ing,qty,unit))
        conn.commit()

    cur.execute("SELECT id,ingredient,quantity,unit FROM recipes WHERE dish_name=?", (dish,))
    items = cur.fetchall()
    conn.close()

    return render_template('dish.html', dish=dish, items=items)


@app.route('/delete_ingredient/<int:id>/<dish>')
def delete_ingredient(id, dish):
    conn = get_db()
    conn.execute("DELETE FROM recipes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(f'/dish/{dish}')


@app.route('/edit_ingredient/<int:id>/<dish>', methods=['GET','POST'])
def edit_ingredient(id, dish):
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        ing = request.form.get('ingredient')
        qty = float(request.form.get('quantity',0))
        unit = request.form.get('unit')

        qty, unit = convert_to_base(qty, unit)

        cur.execute("UPDATE recipes SET ingredient=?,quantity=?,unit=? WHERE id=?",(ing,qty,unit,id))
        conn.commit()
        conn.close()
        return redirect(f'/dish/{dish}')

    cur.execute("SELECT * FROM recipes WHERE id=?", (id,))
    item = cur.fetchone()
    conn.close()

    return render_template('edit_ingredient.html', item=item, dish=dish)


# ---------- COOK ---------- #
@app.route('/cook', methods=['GET','POST'])
def cook():
    result = []
    message = ""

    if request.method == 'POST':
        dish = request.form.get('dish','').lower()
        units = float(request.form.get('units',1))

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT ingredient,quantity,unit FROM recipes WHERE dish_name=?", (dish,))
        items = cur.fetchall()

        can_cook = True

        for ing, qty, unit in items:
            req = qty * units

            cur.execute("SELECT quantity,unit FROM inventory WHERE name=?", (ing,))
            row = cur.fetchone()

            if row:
                avail, inv_unit = row
            else:
                avail, inv_unit = 0, unit

            status = "OK" if avail >= req else "NOT ENOUGH"
            if status == "NOT ENOUGH":
                can_cook = False

            result.append((ing, format_display(req, unit), format_display(avail, inv_unit), status))

        if 'cook' in request.form and can_cook:
            for ing, qty, unit in items:
                req = qty * units
                cur.execute("UPDATE inventory SET quantity = quantity - ? WHERE name=?", (req,ing))

            conn.commit()
            message = "Dish Cooked Successfully!"

        conn.close()

    return render_template('cook.html', result=result, message=message)

import matplotlib.pyplot as plt
import os

@app.route('/chart')
def chart():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT name, quantity FROM inventory")
    data = cur.fetchall()

    names = [i[0] for i in data]
    qtys = [i[1] for i in data]

    plt.figure(figsize=(8,5))
    plt.bar(names, qtys)
    plt.xticks(rotation=45)

    if not os.path.exists("static"):
        os.makedirs("static")

    plt.tight_layout()
    plt.savefig("static/chart.png")
    plt.close()

    conn.close()

    return render_template('chart.html')

# ---------- RUN ---------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)