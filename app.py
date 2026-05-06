import os
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, session, flash, url_for, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_a_secure_value")

def db():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    
    # Create families table
    c.execute("""
    CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        invite_code TEXT UNIQUE,
        FOREIGN KEY(owner_id) REFERENCES users(id)
    )
    """)
    
    # Create users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        family_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(family_id) REFERENCES families(id)
    )
    """)
    
    # Migrate existing users to add missing columns
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    
    try:
        if 'email' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass  # Column might already exist
    
    try:
        if 'family_id' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN family_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column might already exist
    
    try:
        if 'created_at' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Column might already exist
    
    # Create budgets table
    c.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        limite REAL NOT NULL,
        mes INTEGER NOT NULL,
        ano INTEGER NOT NULL,
        FOREIGN KEY(family_id) REFERENCES families(id)
    )
    """)
    
    # Create transacoes table
    c.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        user_id INTEGER NOT NULL,
        valor REAL NOT NULL,
        descricao TEXT NOT NULL,
        categoria TEXT NOT NULL,
        data TEXT NOT NULL,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(family_id) REFERENCES families(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    # Create recurring transactions table
    c.execute("""
    CREATE TABLE IF NOT EXISTS recurring_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        frequency TEXT NOT NULL, -- 'monthly', 'weekly', 'yearly'
        start_date TEXT NOT NULL,
        end_date TEXT,
        is_active INTEGER DEFAULT 1,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(family_id) REFERENCES families(id)
    )
    """)
    
    # Create financial goals table
    c.execute("""
    CREATE TABLE IF NOT EXISTS financial_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0,
        category TEXT NOT NULL, -- 'emergency_fund', 'vacation', 'car', 'house', 'education', 'retirement', 'investment', 'other'
        priority TEXT DEFAULT 'medium', -- 'low', 'medium', 'high'
        target_date TEXT,
        is_completed INTEGER DEFAULT 0,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(family_id) REFERENCES families(id)
    )
    """)
    
    # Create achievements/badges table
    c.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        achievement_type TEXT NOT NULL, -- 'first_transaction', 'budget_master', 'saving_streak', 'goal_achiever', etc.
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        icon TEXT NOT NULL,
        unlocked_at TEXT NOT NULL,
        FOREIGN KEY(family_id) REFERENCES families(id)
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

CATEGORIES = [
    "Salário",
    "Alimentação",
    "Transporte",
    "Moradia",
    "Lazer",
    "Investimento",
    "Educação",
    "Saúde",
    "Utilidades",
    "Outro"
]

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        # Ensure all expected columns exist, defaulting to None if missing
        user_dict = dict(user)
        user_dict.setdefault('email', None)
        user_dict.setdefault('family_id', None)
        user_dict.setdefault('created_at', datetime.now().isoformat())
        return user_dict
    return None

def get_user_family():
    user = get_current_user()
    if not user or not user["family_id"]:
        return None
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM families WHERE id = ?", (user["family_id"],))
    family = c.fetchone()
    conn.close()
    return family

def get_family_members(family_id):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users WHERE family_id = ? ORDER BY username", (family_id,))
    members = c.fetchall()
    conn.close()
    return members

def generate_invite_code():
    return str(uuid.uuid4())[:8].upper()

def verify_password(stored_password, provided_password):
    return check_password_hash(stored_password, provided_password)

def generate_financial_alerts(user, all_dados, income, expense, balance, categories):
    alerts = []
    
    # Emergency fund alert
    emergency_fund_needed = income * 0.0833 * 6  # 6 months of income (monthly average)
    emergency_fund_current = max(0, balance)
    
    if emergency_fund_current < emergency_fund_needed:
        alerts.append({
            "type": "warning",
            "title": "Fundo de Emergência Baixo",
            "message": f"Seu fundo de emergência cobre apenas {emergency_fund_current/emergency_fund_needed*100:.1f}% do necessário (6 meses de renda).",
            "action": "Acesse o Consultor de Investimentos",
            "icon": "🛡️"
        })
    
    # Savings rate alert
    savings_rate = ((income - expense) / income * 100) if income > 0 else 0
    if savings_rate < 20:
        alerts.append({
            "type": "info",
            "title": "Taxa de Poupança Baixa",
            "message": f"Sua taxa de poupança é de {savings_rate:.1f}%. O ideal é acima de 20%.",
            "action": "Revise seus gastos",
            "icon": "💰"
        })
    
    # High expense categories
    total_expenses = expense
    high_expense_categories = []
    for cat, amount in categories.items():
        if amount < 0 and abs(amount) > total_expenses * 0.3:  # More than 30% of expenses
            high_expense_categories.append(cat)
    
    if high_expense_categories:
        alerts.append({
            "type": "warning",
            "title": "Gastos Elevados",
            "message": f"Categorias com gastos altos: {', '.join(high_expense_categories[:2])}",
            "action": "Verifique seu orçamento",
            "icon": "📊"
        })
    
    # Goal progress alerts
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM financial_goals WHERE family_id = ? AND is_completed = 0", (user["family_id"],))
    active_goals = c.fetchall()
    conn.close()
    
    for goal in active_goals:
        progress = (goal["current_amount"] / goal["target_amount"]) * 100
        if progress < 25:
            alerts.append({
                "type": "info",
                "title": f"Meta '{goal['name']}' Atrasada",
                "message": f"Você tem apenas {progress:.1f}% do progresso necessário.",
                "action": "Aumente os aportes",
                "icon": "🎯"
            })
    
    return alerts

@app.route("/")
def home():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if not user["family_id"]:
        return redirect(url_for("create_family"))
    
    family = get_user_family()
    conn = db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM transacoes WHERE family_id = ? ORDER BY data DESC",
        (user["family_id"],)
    )
    all_dados = c.fetchall()
    conn.close()

    # Recent transactions (last 5)
    dados = all_dados[:5]

    income = sum(item["valor"] for item in all_dados if item["valor"] > 0)
    expense = sum(-item["valor"] for item in all_dados if item["valor"] < 0)
    balance = income - expense

    categories = {}
    for item in all_dados:
        categories[item["categoria"]] = categories.get(item["categoria"], 0) + item["valor"]

    # Prepare chart data
    balance_data = []
    current_balance = 0
    dates = sorted(set(item["data"] for item in all_dados))
    for date in dates:
        day_transactions = [t for t in all_dados if t["data"] == date]
        current_balance += sum(t["valor"] for t in day_transactions)
        balance_data.append({"date": date, "balance": current_balance})

    category_labels = list(categories.keys())
    category_values = [abs(v) for v in categories.values()]
    
    # Generate financial insights
    insights = []
    
    # Check savings rate
    if income > 0:
        savings_rate = ((income - expense) / income) * 100
        if savings_rate > 20:
            insights.append({
                "type": "success",
                "icon": "💰",
                "title": "Excelente taxa de poupança!",
                "message": f"Você está poupando {savings_rate:.1f}% da sua renda. Continue assim!"
            })
        elif savings_rate > 10:
            insights.append({
                "type": "info",
                "icon": "📈",
                "title": "Boa taxa de poupança",
                "message": f"Você está poupando {savings_rate:.1f}% da sua renda. Que tal aumentar para 20%?"
            })
        elif savings_rate > 0:
            insights.append({
                "type": "warning",
                "icon": "⚠️",
                "title": "Atenção com os gastos",
                "message": f"Você está poupando apenas {savings_rate:.1f}%. Tente reduzir gastos desnecessários."
            })
        else:
            insights.append({
                "type": "danger",
                "icon": "🚨",
                "title": "Gastos acima da renda",
                "message": "Seus gastos estão acima da renda. Revise seu orçamento urgentemente!"
            })
    
    # Check largest expense categories
    expense_categories = {k: v for k, v in categories.items() if v < 0}
    if expense_categories:
        largest_category = max(expense_categories, key=lambda k: abs(expense_categories[k]))
        largest_amount = abs(expense_categories[largest_category])
        if largest_amount > expense * 0.3:  # More than 30% of expenses
            insights.append({
                "type": "info",
                "icon": "📊",
                "title": "Categoria de maior gasto",
                "message": f"{largest_category} representa uma parcela significativa dos seus gastos. Considere criar um orçamento para esta categoria."
            })
    
    # Check if they have transactions
    if not all_dados:
        insights.append({
            "type": "info",
            "icon": "🚀",
            "title": "Bem-vindo ao FinanceHub!",
            "message": "Comece adicionando suas primeiras transações para ver insights personalizados sobre suas finanças."
        })
    
    # Check for recent large expenses
    recent_large_expenses = [t for t in dados if t["valor"] < -100]  # Expenses over R$100
    if recent_large_expenses:
        insights.append({
            "type": "warning",
            "icon": "💸",
            "title": "Gasto significativo recente",
            "message": f"Você teve {len(recent_large_expenses)} gasto(s) acima de R$100 recentemente. Tudo necessário?"
        })
    
    members = get_family_members(user["family_id"])
    
    # Generate financial alerts
    alerts = generate_financial_alerts(user, all_dados, income, expense, balance, categories)

    return render_template(
        "index.html",
        user=user,
        family=family,
        members=members,
        dados=dados,
        income=income,
        expense=expense,
        balance=balance,
        categories=categories,
        categories_list=CATEGORIES,
        today_date=datetime.now().strftime("%Y-%m-%d"),
        balance_data=balance_data,
        category_labels=category_labels,
        category_values=category_values,
        insights=insights,
        alerts=alerts
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("senha", "").strip()
        
        if not username or not password:
            flash("Preencha usuário e senha.")
            return redirect(url_for("register"))

        conn = db()
        c = conn.cursor()
        try:
            hashed_password = generate_password_hash(password)
            c.execute(
                "INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)",
                (username, hashed_password, email, datetime.now().isoformat()),
            )
            conn.commit()
            flash("Conta criada com sucesso. Faça login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este usuário já existe.")
            return redirect(url_for("register"))
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("senha", "").strip()

        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if not user:
            flash("Usuário não encontrado.")
        elif not verify_password(user["password"], password):
            flash("Senha inválida.")
        else:
            session["user_id"] = user["id"]
            return redirect(url_for("home"))

        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# ============== FAMILY ROUTES ==============

@app.route("/create-family", methods=["GET", "POST"])
def create_family():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if user["family_id"]:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        family_name = request.form.get("family_name", "").strip()
        
        if not family_name:
            flash("Nome da família é obrigatório.")
            return redirect(url_for("create_family"))
        
        conn = db()
        c = conn.cursor()
        invite_code = generate_invite_code()
        c.execute(
            "INSERT INTO families (name, owner_id, created_at, invite_code) VALUES (?, ?, ?, ?)",
            (family_name, user["id"], datetime.now().isoformat(), invite_code)
        )
        conn.commit()
        family_id = c.lastrowid
        
        c.execute("UPDATE users SET family_id = ? WHERE id = ?", (family_id, user["id"]))
        conn.commit()
        conn.close()
        
        flash("Família criada com sucesso!")
        return redirect(url_for("home"))
    
    return render_template("create_family.html")

@app.route("/family-settings")
def family_settings():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    family = get_user_family()
    members = get_family_members(user["family_id"])
    
    return render_template(
        "family_settings.html",
        user=user,
        family=family,
        members=members
    )

@app.route("/join-family", methods=["GET", "POST"])
def join_family():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if user["family_id"]:
        flash("Você já pertence a uma família.")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        invite_code = request.form.get("invite_code", "").strip().upper()
        
        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM families WHERE invite_code = ?", (invite_code,))
        family = c.fetchone()
        
        if not family:
            flash("Código de convite inválido.")
            return redirect(url_for("join_family"))
        
        c.execute("UPDATE users SET family_id = ? WHERE id = ?", (family["id"], user["id"]))
        conn.commit()
        conn.close()
        
        flash(f"Você entrou na família {family['name']}!")
        return redirect(url_for("home"))
    
    return render_template("join_family.html")

@app.route("/api/invite-code")
def get_invite_code():
    user = get_current_user()
    if not user or not user["family_id"]:
        return jsonify({"error": "Unauthorized"}), 401
    
    family = get_user_family()
    return jsonify({"invite_code": family["invite_code"]})
def transactions():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes WHERE user_id = ? ORDER BY data DESC", (user["id"],))
    dados = c.fetchall()
    conn.close()

    return render_template("transactions.html", user=user, dados=dados)


# ============== TRANSACTION ROUTES ==============

@app.route("/add", methods=["POST"])
def add():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))

    try:
        valor = float(request.form.get("valor", "0").replace(",", "."))
    except ValueError:
        flash("Valor inválido.")
        return redirect(url_for("home"))

    descricao = request.form.get("descricao", "").strip()
    categoria = request.form.get("categoria", "Outro")
    data = request.form.get("data", datetime.now().strftime("%Y-%m-%d"))

    if not descricao:
        flash("Descrição é obrigatória.")
        return redirect(url_for("home"))

    conn = db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transacoes (family_id, user_id, valor, descricao, categoria, data, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user["family_id"], user["id"], valor, descricao, categoria, data, user["username"], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

@app.route("/delete/<int:id>")
def delete(id):
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))

    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM transacoes WHERE id = ? AND family_id = ?", (id, user["family_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))

@app.route("/transactions")
def transactions():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes WHERE family_id = ? ORDER BY data DESC", (user["family_id"],))
    dados = c.fetchall()
    conn.close()
    
    family = get_user_family()

    return render_template("transactions.html", user=user, family=family, dados=dados)

# ============== BUDGETS ROUTES ==============

@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if not user["family_id"]:
        return redirect(url_for("create_family"))
    
    conn = db()
    c = conn.cursor()
    
    if request.method == "POST":
        categoria = request.form["categoria"]
        limite = float(request.form["limite"])
        mes = int(request.form["mes"])
        ano = int(request.form["ano"])
        
        # Check if budget already exists for this category/month/year
        c.execute(
            "SELECT id FROM budgets WHERE family_id = ? AND categoria = ? AND mes = ? AND ano = ?",
            (user["family_id"], categoria, mes, ano)
        )
        existing = c.fetchone()
        
        if existing:
            c.execute(
                "UPDATE budgets SET limite = ? WHERE id = ?",
                (limite, existing[0])
            )
        else:
            c.execute(
                "INSERT INTO budgets (family_id, categoria, limite, mes, ano) VALUES (?, ?, ?, ?, ?)",
                (user["family_id"], categoria, limite, mes, ano)
            )
        
        conn.commit()
        flash("Orçamento salvo com sucesso!", "success")
        return redirect(url_for("budgets"))
    
    # Get current budgets
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    c.execute(
        "SELECT * FROM budgets WHERE family_id = ? AND mes = ? AND ano = ?",
        (user["family_id"], current_month, current_year)
    )
    budgets_data = c.fetchall()
    
    # Calculate spending by category
    c.execute(
        "SELECT categoria, SUM(valor) as total FROM transacoes WHERE family_id = ? AND strftime('%m', data) = ? AND strftime('%Y', data) = ? AND valor < 0 GROUP BY categoria",
        (user["family_id"], f"{current_month:02d}", str(current_year))
    )
    spending = {row[0]: abs(row[1]) for row in c.fetchall()}
    
    conn.close()
    
    # Prepare budget status
    budget_status = []
    for budget in budgets_data:
        budget_dict = dict(budget)
        spent = spending.get(budget_dict["categoria"], 0)
        budget_dict["spent"] = spent
        budget_dict["remaining"] = budget_dict["limite"] - spent
        budget_dict["percentage"] = (spent / budget_dict["limite"] * 100) if budget_dict["limite"] > 0 else 0
        budget_status.append(budget_dict)
    
    return render_template("budgets.html", budgets=budget_status, categories=CATEGORIES)

# ============== RECURRING TRANSACTIONS ROUTES ==============

@app.route("/recurring", methods=["GET", "POST"])
def recurring():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if not user["family_id"]:
        return redirect(url_for("create_family"))
    
    conn = db()
    c = conn.cursor()
    
    if request.method == "POST":
        descricao = request.form["descricao"]
        categoria = request.form["categoria"]
        valor = float(request.form["valor"])
        frequency = request.form["frequency"]
        start_date = request.form["start_date"]
        end_date = request.form.get("end_date") or None
        
        c.execute(
            "INSERT INTO recurring_transactions (family_id, descricao, categoria, valor, frequency, start_date, end_date, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["family_id"], descricao, categoria, valor, frequency, start_date, end_date, user["username"], datetime.now().isoformat())
        )
        
        conn.commit()
        flash("Transação recorrente criada com sucesso!", "success")
        return redirect(url_for("recurring"))
    
    # Get recurring transactions
    c.execute(
        "SELECT * FROM recurring_transactions WHERE family_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (user["family_id"],)
    )
    recurring_transactions = c.fetchall()
    
    conn.close()
    
    return render_template("recurring.html", recurring_transactions=recurring_transactions, categories=CATEGORIES)

@app.route("/recurring/<int:id>/delete")
def delete_recurring(id):
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Check if the recurring transaction belongs to the user's family
    c.execute(
        "SELECT id FROM recurring_transactions WHERE id = ? AND family_id = ?",
        (id, user["family_id"])
    )
    
    if c.fetchone():
        c.execute("UPDATE recurring_transactions SET is_active = 0 WHERE id = ?", (id,))
        conn.commit()
        flash("Transação recorrente removida com sucesso!", "success")
    
    conn.close()
    return redirect(url_for("recurring"))

@app.route("/process_recurring")
def process_recurring():
    """Process recurring transactions and create actual transactions for the current month"""
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    current_date = datetime.now()
    current_month = current_date.strftime("%Y-%m")
    
    # Get active recurring transactions
    c.execute(
        "SELECT * FROM recurring_transactions WHERE family_id = ? AND is_active = 1",
        (user["family_id"],)
    )
    recurring = c.fetchall()
    
    transactions_created = 0
    
    for rec in recurring:
        # Check if we should create a transaction for this recurring item this month
        start_date = datetime.fromisoformat(rec["start_date"])
        
        # For monthly transactions, create one per month
        if rec["frequency"] == "monthly":
            # Check if we've already created this month's transaction
            transaction_date = current_date.replace(day=start_date.day)
            if transaction_date > current_date:
                transaction_date = transaction_date.replace(month=transaction_date.month-1)
            
            transaction_date_str = transaction_date.strftime("%Y-%m-%d")
            
            # Check if transaction already exists for this recurring item this month
            c.execute(
                "SELECT id FROM transacoes WHERE family_id = ? AND descricao = ? AND data LIKE ?",
                (user["family_id"], f"{rec['descricao']} (Recorrente)", f"{current_month}%")
            )
            
            if not c.fetchone():
                c.execute(
                    "INSERT INTO transacoes (family_id, user_id, valor, descricao, categoria, data, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user["family_id"], user["id"], rec["valor"], f"{rec['descricao']} (Recorrente)", rec["categoria"], transaction_date_str, "Sistema", datetime.now().isoformat())
                )
                transactions_created += 1
    
    conn.commit()
    conn.close()
    
    flash(f"{transactions_created} transações recorrentes processadas!", "success")
    return redirect(url_for("home"))

# ============== FINANCIAL GOALS ROUTES ==============

@app.route("/goals", methods=["GET", "POST"])
def goals():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if not user["family_id"]:
        return redirect(url_for("create_family"))
    
    conn = db()
    c = conn.cursor()
    
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description", "")
        target_amount = float(request.form["target_amount"])
        current_amount = float(request.form.get("current_amount", 0))
        category = request.form["category"]
        priority = request.form.get("priority", "medium")
        target_date = request.form.get("target_date")
        
        c.execute(
            "INSERT INTO financial_goals (family_id, name, description, target_amount, current_amount, category, priority, target_date, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["family_id"], name, description, target_amount, current_amount, category, priority, target_date, user["username"], datetime.now().isoformat(), datetime.now().isoformat())
        )
        
        conn.commit()
        flash("Meta financeira criada com sucesso!", "success")
        return redirect(url_for("goals"))
    
    # Get all goals
    c.execute(
        "SELECT * FROM financial_goals WHERE family_id = ? ORDER BY priority DESC, created_at DESC",
        (user["family_id"],)
    )
    goals_data = c.fetchall()
    
    # Calculate progress and insights for each goal
    goals_with_progress = []
    for goal in goals_data:
        goal_dict = dict(goal)
        
        # Calculate progress percentage
        progress = (goal_dict["current_amount"] / goal_dict["target_amount"] * 100) if goal_dict["target_amount"] > 0 else 0
        goal_dict["progress"] = progress
        
        # Calculate remaining amount
        goal_dict["remaining"] = goal_dict["target_amount"] - goal_dict["current_amount"]
        
        # Calculate days remaining if target date exists
        if goal_dict["target_date"]:
            target_dt = datetime.fromisoformat(goal_dict["target_date"])
            days_remaining = (target_dt - datetime.now()).days
            goal_dict["days_remaining"] = days_remaining
            
            # Calculate required monthly savings
            if days_remaining > 0:
                months_remaining = days_remaining / 30
                goal_dict["monthly_needed"] = goal_dict["remaining"] / months_remaining if months_remaining > 0 else 0
        else:
            goal_dict["days_remaining"] = None
            goal_dict["monthly_needed"] = None
        
        goals_with_progress.append(goal_dict)
    
    # Get achievements
    c.execute(
        "SELECT * FROM achievements WHERE family_id = ? ORDER BY unlocked_at DESC",
        (user["family_id"],)
    )
    achievements = c.fetchall()
    
    conn.close()
    
    goal_categories = [
        ("emergency_fund", "Fundo de Emergência", "🛡️"),
        ("vacation", "Férias", "🏖️"),
        ("car", "Carro", "🚗"),
        ("house", "Casa", "🏠"),
        ("education", "Educação", "🎓"),
        ("retirement", "Aposentadoria", "🏖️"),
        ("investment", "Investimentos", "📈"),
        ("business", "Negócio", "💼"),
        ("wedding", "Casamento", "💍"),
        ("other", "Outro", "🎯")
    ]
    
    return render_template("goals.html", goals=goals_with_progress, achievements=achievements, goal_categories=goal_categories)

@app.route("/goals/<int:goal_id>/update", methods=["POST"])
def update_goal(goal_id):
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Check if goal belongs to user's family
    c.execute(
        "SELECT id FROM financial_goals WHERE id = ? AND family_id = ?",
        (goal_id, user["family_id"])
    )
    
    if c.fetchone():
        current_amount = float(request.form["current_amount"])
        
        c.execute(
            "UPDATE financial_goals SET current_amount = ?, updated_at = ? WHERE id = ?",
            (current_amount, datetime.now().isoformat(), goal_id)
        )
        
        # Check if goal is completed
        c.execute("SELECT target_amount FROM financial_goals WHERE id = ?", (goal_id,))
        target = c.fetchone()[0]
        
        if current_amount >= target:
            c.execute(
                "UPDATE financial_goals SET is_completed = 1, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), goal_id)
            )
            
            # Award achievement
            c.execute(
                "INSERT INTO achievements (family_id, achievement_type, title, description, icon, unlocked_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user["family_id"], "goal_achiever", "Conquistador de Metas", "Parabéns! Você alcançou uma meta financeira!", "🏆", datetime.now().isoformat())
            )
        
        conn.commit()
        flash("Meta atualizada com sucesso!", "success")
    
    conn.close()
    return redirect(url_for("goals"))

@app.route("/goals/<int:goal_id>/delete")
def delete_goal(goal_id):
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Check if goal belongs to user's family
    c.execute(
        "SELECT id FROM financial_goals WHERE id = ? AND family_id = ?",
        (goal_id, user["family_id"])
    )
    
    if c.fetchone():
        c.execute("DELETE FROM financial_goals WHERE id = ?", (goal_id,))
        conn.commit()
        flash("Meta removida com sucesso!", "success")
    
    conn.close()
    return redirect(url_for("goals"))

# ============== INVESTMENT ADVISOR ROUTES ==============

@app.route("/investment-advisor", methods=["GET", "POST"])
def investment_advisor():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Get user's financial data for analysis
    c.execute(
        "SELECT * FROM transacoes WHERE family_id = ? ORDER BY data DESC LIMIT 100",
        (user["family_id"],)
    )
    recent_transactions = c.fetchall()
    
    # Calculate financial metrics
    total_income = sum(t["valor"] for t in recent_transactions if t["valor"] > 0)
    total_expenses = sum(-t["valor"] for t in recent_transactions if t["valor"] < 0)
    savings_rate = (total_income - total_expenses) / total_income * 100 if total_income > 0 else 0
    
    # Get user's goals
    c.execute("SELECT * FROM financial_goals WHERE family_id = ? AND is_completed = 0", (user["family_id"],))
    active_goals = c.fetchall()
    
    # Get current balance
    c.execute("SELECT SUM(valor) FROM transacoes WHERE family_id = ?", (user["family_id"],))
    current_balance = c.fetchone()[0] or 0
    
    conn.close()
    
    recommendations = []
    
    if request.method == "POST":
        # Get user preferences
        risk_tolerance = request.form.get("risk_tolerance", "moderate")
        time_horizon = request.form.get("time_horizon", "medium")
        primary_goal = request.form.get("primary_goal", "growth")
        monthly_investment = float(request.form.get("monthly_investment", 0))
        emergency_fund_months = int(request.form.get("emergency_fund_months", 6))
        
        # Emergency fund check - use positive balance or calculate from savings
        emergency_fund_needed = total_income * emergency_fund_months
        # Consider emergency fund as positive balance or savings available
        emergency_fund_current = max(0, current_balance)  # Only count positive balance
        
        recommendations.append({
            "type": "emergency_fund",
            "title": "Fundo de Emergência",
            "priority": "critical" if emergency_fund_current < emergency_fund_needed else "completed",
            "description": f"Você precisa de R$ {emergency_fund_needed:.2f} para {emergency_fund_months} meses de renda. Atualmente tem R$ {emergency_fund_current:.2f} disponível para emergência.",
            "action": "Priorize construir seu fundo de emergência antes de investir." if emergency_fund_current < emergency_fund_needed else "Seu fundo de emergência está adequado!",
            "icon": "🛡️"
        })
        
        # Investment recommendations based on risk and goals
        if risk_tolerance == "conservative":
            if time_horizon == "short":
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "CDB/LC",
                        "risk": "Baixo",
                        "return": "6-9% ao ano",
                        "description": "Certificado de Depósito Bancário ou Letra de Crédito. Segurança alta com rendimento superior à poupança.",
                        "examples": ["CDB DI Liquidez Diária (Banco do Brasil)", "LC Itaú 90% CDI", "CDB Santander 100% CDI"],
                        "suitability": 95,
                        "pros": ["Segurança garantida pelo FGC até R$ 250.000", "Liquidez diária em muitos casos", "Rendimento superior à poupança"],
                        "cons": ["Rendimento pode ficar abaixo da inflação", "Imposto de renda regressivo"],
                        "icon": "🏦"
                    },
                    {
                        "type": "investment",
                        "title": "Tesouro SELIC",
                        "risk": "Muito Baixo",
                        "return": "SELIC + 0.1%",
                        "description": "Título público indexado à taxa SELIC. Ideal para preservação de capital de curto prazo.",
                        "examples": ["Tesouro SELIC 2026", "Tesouro SELIC 2027"],
                        "suitability": 90,
                        "pros": ["Segurança total do governo federal", "Liquidez diária", "Rendimento competitivo"],
                        "cons": ["Rendimento segue a SELIC", "Imposto de renda sobre juros"],
                        "icon": "🇧🇷"
                    }
                ])
            elif time_horizon == "medium":
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "CDB/LC",
                        "risk": "Baixo",
                        "return": "6-9% ao ano",
                        "description": "Certificado de Depósito Bancário ou Letra de Crédito. Segurança alta com rendimento superior à poupança.",
                        "examples": ["CDB DI Liquidez Diária (Banco do Brasil)", "LC Itaú 90% CDI", "CDB Santander 100% CDI"],
                        "suitability": 95,
                        "pros": ["Segurança garantida pelo FGC até R$ 250.000", "Liquidez diária em muitos casos", "Rendimento superior à poupança"],
                        "cons": ["Rendimento pode ficar abaixo da inflação", "Imposto de renda regressivo"],
                        "icon": "🏦"
                    },
                    {
                        "type": "investment",
                        "title": "Fundos Multimercado Conservadores",
                        "risk": "Baixo a Médio",
                        "return": "8-12% ao ano",
                        "description": "Fundos que investem em diversos ativos com estratégia conservadora, focando em renda fixa.",
                        "examples": ["Fundo Multimercado XP Conservative", "Caixa FI Multimercado Conservador", "Itaú Personnalité Conservative"],
                        "suitability": 85,
                        "pros": ["Diversificação automática", "Gestão profissional", "Rendimento superior a renda fixa pura"],
                        "cons": ["Taxas de administração (1-2% ao ano)", "Não há garantia de rentabilidade"],
                        "icon": "📊"
                    }
                ])
            else:  # long term
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "Fundos de Previdência",
                        "risk": "Baixo a Médio",
                        "return": "7-10% ao ano",
                        "description": "Plano de aposentadoria com benefícios fiscais e rentabilidade composta.",
                        "examples": ["Previdência Privada Itaú", "Bradesco Previdência PGBL", "Caixa Previdência VGBL"],
                        "suitability": 90,
                        "pros": ["Dedução no IR até 12% da renda", "Rendimento composto ao longo do tempo", "Segurança relativa"],
                        "cons": ["Resgate antecipado tem penalidades", "Carência de 60-120 dias para resgate"],
                        "icon": "🏖️"
                    },
                    {
                        "type": "investment",
                        "title": "ETFs de Renda Fixa",
                        "risk": "Baixo",
                        "return": "6-8% ao ano",
                        "description": "Fundos de índice que replicam índices de renda fixa, oferecendo diversificação automática.",
                        "examples": ["iShares IFIX FI (IFIX11)", "XP IFIX FI (XFIX11)", "Hashdex RFIX FI (RFIX11)"],
                        "suitability": 80,
                        "pros": ["Diversificação instantânea em títulos públicos/privados", "Baixo custo (0.1-0.5% ao ano)", "Liquidez alta"],
                        "cons": ["Rendimento limitado pela composição do IFIX", "Variação de preço conforme mercado"],
                        "icon": "📈"
                    }
                ])
        
        elif risk_tolerance == "moderate":
            if time_horizon == "short":
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "CDB/LC",
                        "risk": "Baixo",
                        "return": "6-9% ao ano",
                        "description": "Certificado de Depósito Bancário ou Letra de Crédito. Segurança alta com rendimento superior à poupança.",
                        "examples": ["CDB DI Liquidez Diária (Banco do Brasil)", "LC Itaú 90% CDI", "CDB Santander 100% CDI"],
                        "suitability": 90,
                        "pros": ["Segurança garantida pelo FGC até R$ 250.000", "Liquidez diária em muitos casos", "Rendimento superior à poupança"],
                        "cons": ["Rendimento pode ficar abaixo da inflação", "Imposto de renda regressivo"],
                        "icon": "🏦"
                    },
                    {
                        "type": "investment",
                        "title": "Fundos Multimercado Moderados",
                        "risk": "Médio",
                        "return": "10-15% ao ano",
                        "description": "Fundos balanceados entre renda fixa e variável, com exposição moderada a ações.",
                        "examples": ["XP Multimercado Moderate", "Caixa FI Multimercado Moderate", "Itaú Personnalité Moderate"],
                        "suitability": 85,
                        "pros": ["Diversificação entre ativos", "Potencial de maior retorno que renda fixa", "Gestão profissional"],
                        "cons": ["Volatilidade maior que renda fixa pura", "Não há garantia de rentabilidade"],
                        "icon": "⚖️"
                    }
                ])
            elif time_horizon == "medium":
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "Fundos Multimercado",
                        "risk": "Médio",
                        "return": "10-15% ao ano",
                        "description": "Fundos que investem em diversos ativos com estratégia balanceada entre renda fixa e ações.",
                        "examples": ["XP Multimercado Balance", "Caixa FI Multimercado", "Itaú Personnalité"],
                        "suitability": 90,
                        "pros": ["Diversificação automática entre classes de ativos", "Gestão profissional", "Potencial de crescimento"],
                        "cons": ["Volatilidade conforme mercado", "Taxas de administração"],
                        "icon": "📊"
                    },
                    {
                        "type": "investment",
                        "title": "ETFs de Ações",
                        "risk": "Médio-Alto",
                        "return": "12-18% ao ano (histórico)",
                        "description": "Fundos de índice que replicam índices de ações brasileiras, oferecendo exposição ao mercado acionário.",
                        "examples": ["iShares Ibovespa (BOVA11)", "XP Ibovespa (XBOV11)", "Hashdex Ibovespa (BOVV11)"],
                        "suitability": 75,
                        "pros": ["Diversificação em 50+ ações brasileiras", "Baixo custo (0.3-0.5% ao ano)", "Liquidez alta"],
                        "cons": ["Volatilidade alta do mercado acionário", "Risco de perda temporária", "Não paga dividendos"],
                        "icon": "📈"
                    }
                ])
            else:  # long term
                recommendations.extend([
                    {
                        "type": "investment",
                        "title": "Ações Individuais",
                        "risk": "Alto",
                        "return": "15-20% ao ano (histórico)",
                        "description": "Investimento direto em ações de empresas sólidas do mercado brasileiro.",
                        "examples": ["PETR4 (Petrobras)", "VALE3 (Vale)", "ITUB4 (Itaú)", "WEGE3 (Weg)", "MGLU3 (Magazine Luiza)"],
                        "suitability": 70,
                        "pros": ["Potencial de alto retorno", "Dividendos trimestrais", "Participação em empresas brasileiras"],
                        "cons": ["Risco de perda significativa", "Requer análise fundamentalista", "Volatilidade alta"],
                        "icon": "🏢"
                    },
                    {
                        "type": "investment",
                        "title": "Fundos de Ações",
                        "risk": "Alto",
                        "return": "14-20% ao ano (histórico)",
                        "description": "Fundos que investem majoritariamente em ações, com gestão profissional.",
                        "examples": ["XP Small Caps", "Caixa FIA Ibovespa", "Itaú FIA Ações"],
                        "suitability": 80,
                        "pros": ["Diversificação em ações", "Gestão profissional especializada", "Acesso a diferentes estratégias"],
                        "cons": ["Volatilidade alta", "Taxas de administração maiores", "Não há garantia de rentabilidade"],
                        "icon": "📊"
                    }
                ])
        
        else:  # aggressive
            recommendations.extend([
                {
                    "type": "investment",
                    "title": "Ações de Crescimento",
                    "risk": "Alto",
                    "return": "18-25% ao ano (histórico)",
                    "description": "Ações de empresas com alto potencial de crescimento, especialmente em setores tecnológicos e inovadores.",
                    "examples": ["NU (Nubank)", "CASH3 (Méliuz)", "LWSA3 (Locaweb)", "TOTS3 (Totvs)", "BBDC4 (Bradesco)"],
                    "suitability": 60,
                    "pros": ["Potencial de retornos extraordinários", "Participação no crescimento econômico brasileiro"],
                    "cons": ["Risco muito alto de perda", "Volatilidade extrema", "Possibilidade de perdas significativas"],
                    "icon": "🚀"
                },
                {
                    "type": "investment",
                    "title": "Criptomoedas",
                    "risk": "Muito Alto",
                    "return": "Altamente volátil",
                    "description": "Moedas digitais como Bitcoin, Ethereum, etc. através de corretoras regulamentadas.",
                    "examples": ["Bitcoin (BTC)", "Ethereum (ETH)", "BNB (Binance)", "ADA (Cardano)"],
                    "suitability": 30,
                    "pros": ["Potencial de retornos muito altos", "Tecnologia inovadora e disruptiva"],
                    "cons": ["Extrema volatilidade", "Risco de perda total do investimento", "Regulamentação ainda em desenvolvimento"],
                    "icon": "₿"
                },
                {
                    "type": "investment",
                    "title": "Fundos de Private Equity",
                    "risk": "Alto",
                    "return": "15-25% ao ano",
                    "description": "Investimento em empresas privadas não listadas, através de fundos especializados.",
                    "examples": ["XP Private Equity", "BTG Pactual Private Equity", "Patria Private Equity"],
                    "suitability": 40,
                    "pros": ["Potencial de altos retornos", "Acesso a oportunidades únicas", "Diversificação setorial"],
                    "cons": ["Baixa liquidez (5-10 anos)", "Risco de concentração", "Horizonte de investimento longo"],
                    "icon": "💼"
                }
            ])
        
        # Goal-based recommendations
        if primary_goal == "retirement":
            recommendations.append({
                "type": "strategy",
                "title": "Estratégia para Aposentadoria",
                "description": "Para aposentadoria, foque em investimentos de longo prazo com crescimento consistente e benefícios fiscais.",
                "action": "Considere aumentar gradualmente a exposição a ações conforme se aproxima da aposentadoria. Utilize Previdência Privada para deduções fiscais.",
                "icon": "🏖️"
            })
        elif primary_goal == "house":
            recommendations.append({
                "type": "strategy",
                "title": "Estratégia para Compra da Casa",
                "description": "Para compra de imóvel, mantenha uma carteira conservadora até ter o valor necessário, preservando o capital acumulado.",
                "action": "Use uma combinação de renda fixa (CDB/LC) e multimercado conservador para preservar o capital enquanto rende acima da inflação.",
                "icon": "🏠"
            })
        elif primary_goal == "education":
            recommendations.append({
                "type": "strategy",
                "title": "Estratégia para Educação",
                "description": "Para educação dos filhos, considere planos educacionais ou investimentos com horizonte definido que coincidam com o cronograma educacional.",
                "action": "Invista em opções que rendam acima da inflação e tenham liquidez quando necessário. Considere Previdência Educacional se disponível.",
                "icon": "🎓"
            })
        
        # Monthly investment planning
        if monthly_investment > 0:
            years_to_goal = 10  # assuming 10 years
            future_value_conservative = monthly_investment * (((1 + 0.08/12)**(years_to_goal*12) - 1) / (0.08/12))
            future_value_moderate = monthly_investment * (((1 + 0.12/12)**(years_to_goal*12) - 1) / (0.12/12))
            future_value_aggressive = monthly_investment * (((1 + 0.18/12)**(years_to_goal*12) - 1) / (0.18/12))
            
            recommendations.append({
                "type": "projection",
                "title": "Projeção de Investimentos",
                "description": f"Investindo R$ {monthly_investment:.2f} mensalmente por {years_to_goal} anos (com aportes mensais):",
                "projections": {
                    "conservative": f"R$ {future_value_conservative:.2f} (8% ao ano)",
                    "moderate": f"R$ {future_value_moderate:.2f} (12% ao ano)",
                    "aggressive": f"R$ {future_value_aggressive:.2f} (18% ao ano)"
                },
                "icon": "💡"
            })
    
    return render_template(
        "investment_advisor.html",
        recommendations=recommendations,
        total_income=total_income,
        total_expenses=total_expenses,
        savings_rate=savings_rate,
        active_goals=active_goals,
        current_balance=current_balance
    )

# ============== FINANCIAL HEALTH ROUTES ==============

@app.route("/financial-health")
def financial_health():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Get recent transactions (last 3 months)
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    c.execute(
        "SELECT * FROM transacoes WHERE family_id = ? AND data >= ? ORDER BY data DESC",
        (user["family_id"], three_months_ago)
    )
    transactions = c.fetchall()
    
    # Calculate financial metrics
    total_income = sum(t["valor"] for t in transactions if t["valor"] > 0)
    total_expenses = sum(-t["valor"] for t in transactions if t["valor"] < 0)
    net_income = total_income - total_expenses
    
    # Savings rate
    savings_rate = (net_income / total_income * 100) if total_income > 0 else 0
    
    # Expense breakdown by category
    expense_categories = {}
    for t in transactions:
        if t["valor"] < 0:
            cat = t["categoria"]
            expense_categories[cat] = expense_categories.get(cat, 0) + abs(t["valor"])
    
    # Calculate financial health score (0-100)
    health_score = 0
    
    # Savings rate component (40% weight)
    if savings_rate >= 20:
        health_score += 40
    elif savings_rate >= 15:
        health_score += 30
    elif savings_rate >= 10:
        health_score += 20
    elif savings_rate >= 5:
        health_score += 10
    
    # Expense control component (30% weight)
    essential_expenses = expense_categories.get("Moradia", 0) + expense_categories.get("Alimentação", 0) + expense_categories.get("Transporte", 0) + expense_categories.get("Saúde", 0)
    if total_income > 0:
        essential_ratio = essential_expenses / total_income
        if essential_ratio <= 0.5:
            health_score += 30
        elif essential_ratio <= 0.6:
            health_score += 20
        elif essential_ratio <= 0.7:
            health_score += 10
    
    # Diversification component (20% weight)
    unique_categories = len([t for t in transactions if t["valor"] > 0])
    if unique_categories >= 2:
        health_score += 20
    elif unique_categories == 1:
        health_score += 10
    
    # Goal progress component (10% weight)
    c.execute("SELECT COUNT(*) FROM financial_goals WHERE family_id = ? AND is_completed = 1", (user["family_id"],))
    completed_goals = c.fetchone()[0]
    if completed_goals > 0:
        health_score += 10
    
    # Get goals for progress display
    c.execute("SELECT * FROM financial_goals WHERE family_id = ? AND is_completed = 0 ORDER BY priority DESC LIMIT 3", (user["family_id"],))
    active_goals = c.fetchall()
    
    conn.close()
    
    # Generate health insights
    insights = []
    
    if health_score >= 80:
        insights.append({
            "type": "success",
            "icon": "🌟",
            "title": "Saúde Financeira Excelente!",
            "message": "Parabéns! Suas finanças estão em excelente estado."
        })
    elif health_score >= 60:
        insights.append({
            "type": "info",
            "icon": "👍",
            "title": "Saúde Financeira Boa",
            "message": "Você está no caminho certo. Continue assim!"
        })
    elif health_score >= 40:
        insights.append({
            "type": "warning",
            "icon": "⚠️",
            "title": "Atenção Necessária",
            "message": "Há oportunidades de melhoria em sua saúde financeira."
        })
    else:
        insights.append({
            "type": "danger",
            "icon": "🚨",
            "title": "Revisão Urgente Necessária",
            "message": "Suas finanças precisam de atenção imediata."
        })
    
    if savings_rate < 10:
        insights.append({
            "type": "warning",
            "icon": "💰",
            "title": "Taxa de Poupança Baixa",
            "message": "Considere aumentar sua taxa de poupança para pelo menos 20% da renda."
        })
    
    return render_template(
        "financial_health.html",
        health_score=int(health_score),
        total_income=total_income,
        total_expenses=total_expenses,
        savings_rate=savings_rate,
        insights=insights,
        active_goals=active_goals,
        expense_categories=expense_categories
    )

# ============== ADVANCED ANALYTICS ROUTES ==============

@app.route("/analytics")
def analytics():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Get all transactions for analysis
    c.execute("SELECT * FROM transacoes WHERE family_id = ? ORDER BY data ASC", (user["family_id"],))
    all_transactions = c.fetchall()
    
    # Monthly trends (last 12 months)
    monthly_data = []
    for i in range(11, -1, -1):
        date = datetime.now() - timedelta(days=i*30)
        month_start = date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_transactions = [t for t in all_transactions if month_start.strftime("%Y-%m") <= t["data"] <= month_end.strftime("%Y-%m-%d")]
        
        income = sum(t["valor"] for t in month_transactions if t["valor"] > 0)
        expenses = sum(-t["valor"] for t in month_transactions if t["valor"] < 0)
        
        monthly_data.append({
            "month": month_start.strftime("%b %Y"),
            "income": income,
            "expenses": expenses,
            "net": income - expenses
        })
    
    # Seasonal analysis
    seasonal_data = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for t in all_transactions:
        month = datetime.fromisoformat(t["data"]).month
        quarter = f"Q{(month-1)//3 + 1}"
        seasonal_data[quarter].append(t)
    
    seasonal_summary = {}
    for quarter, transactions in seasonal_data.items():
        income = sum(t["valor"] for t in transactions if t["valor"] > 0)
        expenses = sum(-t["valor"] for t in transactions if t["valor"] < 0)
        seasonal_summary[quarter] = {
            "income": income,
            "expenses": expenses,
            "net": income - expenses,
            "transactions": len(transactions)
        }
    
    # Spending predictions (simple linear regression)
    if len(monthly_data) >= 3:
        expenses_trend = [m["expenses"] for m in monthly_data[-6:]]  # Last 6 months
        if len(expenses_trend) >= 2:
            # Simple trend calculation
            recent_avg = sum(expenses_trend[-3:]) / 3
            previous_avg = sum(expenses_trend[:3]) / 3 if len(expenses_trend) >= 3 else recent_avg
            trend = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
        else:
            trend = 0
    else:
        trend = 0
    
    # Top spending categories
    category_totals = {}
    for t in all_transactions:
        if t["valor"] < 0:
            category_totals[t["categoria"]] = category_totals.get(t["categoria"], 0) + abs(t["valor"])
    
    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    conn.close()
    
    return render_template(
        "analytics.html",
        monthly_data=monthly_data,
        seasonal_summary=seasonal_summary,
        trend=trend,
        top_categories=top_categories
    )

@app.route("/export")
def export():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes WHERE family_id = ? ORDER BY data DESC", (user["family_id"],))
    transactions = c.fetchall()
    conn.close()
    
    # Create CSV content
    output = "Data,Descricao,Categoria,Valor,Criado_por\n"
    for t in transactions:
        # Escape commas in description
        desc = str(t['descricao']).replace(',', ';')
        output += f"{t['data']},{desc},{t['categoria']},{t['valor']},{t['created_by']}\n"
    
    response = make_response(output)
    response.headers["Content-Disposition"] = f"attachment; filename=financehub_transacoes_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

@app.route("/reports")
def reports():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    family = get_user_family()
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM transacoes WHERE family_id = ? ORDER BY data DESC", (user["family_id"],))
    all_dados = c.fetchall()
    conn.close()
    
    # Monthly summary
    current_month = datetime.now().strftime("%Y-%m")
    month_transactions = [t for t in all_dados if t["data"].startswith(current_month)]
    
    month_income = sum(t["valor"] for t in month_transactions if t["valor"] > 0)
    month_expense = sum(-t["valor"] for t in month_transactions if t["valor"] < 0)
    
    # Last 6 months summary
    monthly_data = {}
    for i in range(6):
        date = (datetime.now() - timedelta(days=30*i)).strftime("%Y-%m")
        transactions = [t for t in all_dados if t["data"].startswith(date)]
        monthly_data[date] = {
            "income": sum(t["valor"] for t in transactions if t["valor"] > 0),
            "expense": sum(-t["valor"] for t in transactions if t["valor"] < 0),
        }
    
    return render_template(
        "reports.html",
        user=user,
        family=family,
        month_income=month_income,
        month_expense=month_expense,
        monthly_data=monthly_data,
        all_dados=all_dados
    )

# ============== PROFILE ROUTES ==============

@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "").strip()
        
        conn = db()
        c = conn.cursor()
        
        if new_password:
            hashed_password = generate_password_hash(new_password)
            c.execute("UPDATE users SET email = ?, password = ? WHERE id = ?", 
                     (email, hashed_password, user["id"]))
        else:
            c.execute("UPDATE users SET email = ? WHERE id = ?", 
                     (email, user["id"]))
        
        conn.commit()
        conn.close()
        
        flash("Perfil atualizado com sucesso!")
        return redirect(url_for("profile"))
    
    family = get_user_family()
    
    return render_template("profile.html", user=user, family=family)

# ============== BACKUP/EXPORT ROUTES ==============

@app.route("/backup")
def backup():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    conn = db()
    c = conn.cursor()
    
    # Get all user data
    c.execute("SELECT * FROM transacoes WHERE family_id = ?", (user["family_id"],))
    transactions = c.fetchall()
    
    c.execute("SELECT * FROM financial_goals WHERE family_id = ?", (user["family_id"],))
    goals = c.fetchall()
    
    c.execute("SELECT * FROM budgets WHERE family_id = ?", (user["family_id"],))
    budgets = c.fetchall()
    
    c.execute("SELECT * FROM recurring_transactions WHERE family_id = ?", (user["family_id"],))
    recurring = c.fetchall()
    
    conn.close()
    
    # Create backup data
    backup_data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "family_id": user["family_id"],
        "transactions": transactions,
        "goals": goals,
        "budgets": budgets,
        "recurring_transactions": recurring
    }
    
    # Convert to JSON
    import json
    backup_json = json.dumps(backup_data, indent=2, default=str)
    
    # Create response
    from flask import Response
    response = Response(
        backup_json,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=finance_backup_{datetime.now().strftime("%Y%m%d")}.json'}
    )
    
    return response

# ============== REPORTS ROUTES ==============

@app.route("/monthly-reports")
def monthly_reports():
    user = get_current_user()
    if not user or not user["family_id"]:
        return redirect(url_for("login"))
    
    # Get current month data
    current_month = datetime.now().strftime("%Y-%m")
    conn = db()
    c = conn.cursor()
    
    # Monthly summary
    c.execute("""
        SELECT 
            strftime('%Y-%m', data) as month,
            SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as income,
            SUM(CASE WHEN valor < 0 THEN -valor ELSE 0 END) as expenses
        FROM transacoes 
        WHERE family_id = ? 
        GROUP BY strftime('%Y-%m', data)
        ORDER BY month DESC
        LIMIT 12
    """, (user["family_id"],))
    
    monthly_data = c.fetchall()
    
    # Current month detailed breakdown
    c.execute("""
        SELECT categoria, 
               SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as income,
               SUM(CASE WHEN valor < 0 THEN -valor ELSE 0 END) as expenses
        FROM transacoes 
        WHERE family_id = ? AND strftime('%Y-%m', data) = ?
        GROUP BY categoria
        ORDER BY (income + expenses) DESC
    """, (user["family_id"], current_month))
    
    category_breakdown = c.fetchall()
    
    # Goals progress
    c.execute("SELECT * FROM financial_goals WHERE family_id = ? AND is_completed = 0", (user["family_id"],))
    active_goals = c.fetchall()
    
    conn.close()
    
    # Calculate insights
    if monthly_data:
        current_month_data = monthly_data[0] if monthly_data[0][0] == current_month else None
        previous_month_data = monthly_data[1] if len(monthly_data) > 1 else None
        
        insights = []
        
        if current_month_data and previous_month_data:
            income_change = ((current_month_data[1] - previous_month_data[1]) / previous_month_data[1] * 100) if previous_month_data[1] > 0 else 0
            expense_change = ((current_month_data[2] - previous_month_data[2]) / previous_month_data[2] * 100) if previous_month_data[2] > 0 else 0
            
            if income_change > 10:
                insights.append({"type": "success", "message": f"Receita aumentou {income_change:.1f}% em relação ao mês passado!"})
            elif income_change < -10:
                insights.append({"type": "warning", "message": f"Receita diminuiu {abs(income_change):.1f}% em relação ao mês passado."})
                
            if expense_change > 15:
                insights.append({"type": "warning", "message": f"Gastos aumentaram {expense_change:.1f}% em relação ao mês passado."})
            elif expense_change < -10:
                insights.append({"type": "success", "message": f"Gastos diminuíram {abs(expense_change):.1f}% em relação ao mês passado!"})
    else:
        insights = []
    
    return render_template(
        "monthly_reports.html",
        monthly_data=monthly_data,
        category_breakdown=category_breakdown,
        active_goals=active_goals,
        insights=insights,
        current_month=current_month
    )

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))