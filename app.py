from flask import Flask, render_template, request, redirect
import sqlite3
import os
import matplotlib.pyplot as plt

app = Flask(__name__)

# ---------- DATABASE ---------- #
def get_db():
    return sqlite3.connect("database.db")

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

    conn.commit()
    conn.close()

init_db()
def clean_empty_data():
    conn = get_db()
    cur = conn.cursor()

    # remove empty dishes / bad rows
    cur.execute("DELETE FROM recipes WHERE ingredient='' OR quantity=0")

    conn.commit()
    conn.close()

clean_empty_data()

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

# ---------- HOME ---------- #
@app.route('/')
def index():
    return render_template('index.html')

# ---------- INVENTORY ---------- #
@app.route('/inventory', methods=['GET','POST'])
def inventory():
    conn = get_db()
    cur = conn.cursor()

    message = ""

    if request.method == 'POST':
        name = request.form.get('name','').strip().lower()
        qty_input = request.form.get('quantity','').strip()
        unit = request.form.get('unit','g')

        if not name or not qty_input:
            message = "Enter item name and quantity."
        else:
            try:
                qty = float(qty_input)
                if qty <= 0:
                    message = "Quantity must be greater than 0."
                else:
                    qty, unit = convert_to_base(qty, unit)

                    cur.execute("SELECT * FROM inventory WHERE name=?", (name,))
                    if cur.fetchone():
                        cur.execute("UPDATE inventory SET quantity = quantity + ? WHERE name=?", (qty,name))
                    else:
                        cur.execute("INSERT INTO inventory VALUES (?,?,?)",(name,qty,unit))

                    conn.commit()
                    return redirect('/inventory')
            except:
                message = "Invalid quantity."

    cur.execute("SELECT * FROM inventory")
    data = cur.fetchall()
    conn.close()

    return render_template('inventory.html', data=data, message=message)

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
        qty_input = request.form.get('quantity','').strip()
        unit = request.form.get('unit','g')

        try:
            qty = float(qty_input)
            qty, unit = convert_to_base(qty, unit)

            cur.execute("UPDATE inventory SET quantity=?, unit=? WHERE name=?", (qty,unit,name))
            conn.commit()
            conn.close()
            return redirect('/inventory')
        except:
            pass

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
    message = ""

    if request.method == 'POST':
        dish = request.form.get('dish','').strip().lower()

        if not dish:
            message = "Please enter a dish name."
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO recipes (dish_name,ingredient,quantity,unit) VALUES (?, '',0,'g')",
                (dish,)
            )
            conn.commit()
            conn.close()
            return redirect('/recipe')

    return render_template('create_dish.html', message=message)

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
        ing = request.form.get('ingredient','').strip().lower()
        qty_input = request.form.get('quantity','').strip()
        unit = request.form.get('unit','g')

        if ing and qty_input:
            try:
                qty = float(qty_input)
                qty, unit = convert_to_base(qty, unit)

                cur.execute("INSERT INTO recipes VALUES (NULL,?,?,?,?)",(dish,ing,qty,unit))
                conn.commit()
            except:
                pass

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
        qty_input = request.form.get('quantity','')
        unit = request.form.get('unit')

        try:
            qty = float(qty_input)
            qty, unit = convert_to_base(qty, unit)

            cur.execute("UPDATE recipes SET ingredient=?,quantity=?,unit=? WHERE id=?",(ing,qty,unit,id))
            conn.commit()
            conn.close()
            return redirect(f'/dish/{dish}')
        except:
            pass

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
        dish = request.form.get('dish', '').strip().lower()
        people_input = request.form.get('people', '').strip()

        if not dish or not people_input:
            message = "Enter dish and number of people."
        else:
            try:
                people = float(people_input)
                if people <= 0:
                    message = "People must be greater than 0."
                else:
                    conn = get_db()
                    cur = conn.cursor()

                    cur.execute("SELECT ingredient,quantity,unit FROM recipes WHERE dish_name=?", (dish,))
                    items = cur.fetchall()

                    if not items:
                        message = "Dish not found."
                    else:
                        can_cook = True

                        for ing, qty, unit in items:
                            req = qty * people

                            cur.execute("SELECT quantity,unit FROM inventory WHERE name=?", (ing,))
                            row = cur.fetchone()

                            if row:
                                avail, inv_unit = row
                            else:
                                avail, inv_unit = 0, unit

                            status = "OK" if avail >= req else "NOT ENOUGH"
                            if status == "NOT ENOUGH":
                                can_cook = False

                            result.append((
                                ing,
                                f"{format_display(qty, unit)} × {int(people)}",
                                format_display(avail, inv_unit),
                                status
                            ))

                        if 'cook' in request.form and can_cook:
                            for ing, qty, unit in items:
                                req = qty * people
                                cur.execute("UPDATE inventory SET quantity = quantity - ? WHERE name=?", (req, ing))

                            conn.commit()
                            message = "Dish Cooked Successfully!"
                        elif 'cook' in request.form:
                            message = "Not enough ingredients."

                    conn.close()
            except:
                message = "Invalid number of people."

    return render_template('cook.html', result=result, message=message)

# ---------- CHART ---------- #
@app.route('/chart')
def chart():
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)