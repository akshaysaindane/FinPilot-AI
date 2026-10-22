from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "finpilot_secret_key"
DATABASE = "finpilot.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            income REAL NOT NULL,
            expenses REAL NOT NULL,
            savings REAL NOT NULL,
            investments REAL NOT NULL,
            goal TEXT NOT NULL,
            age INTEGER NOT NULL,
            retirement_age INTEGER NOT NULL,
            risk TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL,
            years INTEGER NOT NULL,
            expected_return REAL NOT NULL,
            monthly_required REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


def generate_financial_plan(profile):
    income = float(profile["income"])
    expenses = float(profile["expenses"])
    savings = float(profile["savings"])
    investments = float(profile["investments"])
    age = int(profile["age"])
    retirement_age = int(profile["retirement_age"])
    risk = profile["risk"].lower()
    goal = profile["goal"].strip()

    monthly_surplus = income - expenses

    # -------------------------------------------------
    # Emergency Fund
    # -------------------------------------------------

    emergency_fund_target = expenses * 6
    emergency_fund_gap = max(
        emergency_fund_target - savings,
        0,
    )

    if emergency_fund_target > 0:
        emergency_fund_ratio = (
            savings / emergency_fund_target
        )
    else:
        emergency_fund_ratio = 1

    emergency_fund_ratio = min(
        max(emergency_fund_ratio, 0),
        1,
    )

    # -------------------------------------------------
    # SIP Recommendation
    # -------------------------------------------------

    if risk == "low":
        sip_percentage = 0.15
    elif risk == "medium":
        sip_percentage = 0.20
    else:
        sip_percentage = 0.25

    recommended_sip = max(
        monthly_surplus * sip_percentage,
        0,
    )

    # -------------------------------------------------
    # Retirement
    # -------------------------------------------------

    retirement_years = max(
        retirement_age - age,
        0,
    )

    # -------------------------------------------------
    # Investment Strategy
    # -------------------------------------------------

    if risk == "low":
        investment_strategy = (
            "Focus on conservative investments, debt-oriented options "
            "and stable long-term growth."
        )
    elif risk == "medium":
        investment_strategy = (
            "Maintain a balanced portfolio with a mix of equity and "
            "debt-oriented investments."
        )
    else:
        investment_strategy = (
            "You can consider a higher equity allocation for long-term "
            "growth, while maintaining proper diversification."
        )

    # -------------------------------------------------
    # Goal Advice
    # -------------------------------------------------

    goal_message = (
        f"Your primary financial goal is {goal}. "
        "Maintain disciplined monthly investing towards this goal."
    )

    # -------------------------------------------------
    # Emergency Fund Message
    # -------------------------------------------------

    if emergency_fund_gap > 0:
        emergency_message = (
            f"Your emergency fund target is ₹{emergency_fund_target:,.0f}. "
            f"You may need approximately ₹{emergency_fund_gap:,.0f} more "
            "to reach a six-month expense buffer."
        )
    else:
        emergency_message = (
            "Your current savings cover approximately six months of "
            "expenses. Your emergency fund position looks healthy."
        )

    # -------------------------------------------------
    # Surplus Message
    # -------------------------------------------------

    if monthly_surplus > 0:
        surplus_message = (
            f"Your estimated monthly surplus is ₹{monthly_surplus:,.0f}. "
            "Consider directing a portion towards investments and goals."
        )
    elif monthly_surplus == 0:
        surplus_message = (
            "Your income and expenses are currently equal. "
            "Try creating a monthly surplus before increasing investments."
        )
    else:
        surplus_message = (
            "Your expenses exceed your income by approximately "
            f"₹{abs(monthly_surplus):,.0f} per month. "
            "Focus on improving cash flow before increasing investments."
        )

    # -------------------------------------------------
    # Financial Health Score
    # -------------------------------------------------

    score = 0

    # 1. Monthly surplus — 25 points
    if income > 0:
        surplus_ratio = monthly_surplus / income
    else:
        surplus_ratio = 0

    if surplus_ratio >= 0.30:
        surplus_score = 25
    elif surplus_ratio >= 0.20:
        surplus_score = 20
    elif surplus_ratio >= 0.10:
        surplus_score = 15
    elif surplus_ratio > 0:
        surplus_score = 10
    else:
        surplus_score = 0

    score += surplus_score

    # 2. Emergency fund — 25 points
    emergency_score = round(
        emergency_fund_ratio * 25
    )

    emergency_score = min(
        max(emergency_score, 0),
        25,
    )

    score += emergency_score

    # 3. Investments — 20 points
    if income > 0:
        annual_income = income * 12
        investment_ratio = (
            investments / annual_income
        )
    else:
        investment_ratio = 0

    if investment_ratio >= 1:
        investment_score = 20
    elif investment_ratio >= 0.75:
        investment_score = 16
    elif investment_ratio >= 0.50:
        investment_score = 12
    elif investment_ratio > 0:
        investment_score = 7
    else:
        investment_score = 0

    score += investment_score

    # 4. Retirement timeline — 15 points
    if retirement_years >= 25:
        retirement_score = 15
    elif retirement_years >= 15:
        retirement_score = 12
    elif retirement_years >= 10:
        retirement_score = 9
    elif retirement_years >= 5:
        retirement_score = 5
    else:
        retirement_score = 2

    score += retirement_score

    # 5. Goal + positive surplus — 15 points
    if goal and monthly_surplus > 0:
        goal_score = 15
    elif goal:
        goal_score = 8
    else:
        goal_score = 0

    score += goal_score

    score = min(
        max(score, 0),
        100,
    )

    # -------------------------------------------------
    # Health Status
    # -------------------------------------------------

    if score >= 80:
        health_status = "Excellent"
    elif score >= 65:
        health_status = "Good"
    elif score >= 50:
        health_status = "Needs Improvement"
    else:
        health_status = "Needs Attention"

    # -------------------------------------------------
    # Smart Priority-Based Recommendations
    # -------------------------------------------------

    recommendations = []

    # -------------------------------------------------
    # Priority 1: Negative Cash Flow
    # -------------------------------------------------

    if monthly_surplus < 0:
        recommendations.append(
            (
                100,
                "Your expenses are higher than your income. "
                f"Focus on reducing your monthly deficit of "
                f"₹{abs(monthly_surplus):,.0f} before increasing investments."
            )
        )

    # -------------------------------------------------
    # Priority 2: No Monthly Surplus
    # -------------------------------------------------

    elif monthly_surplus == 0:
        recommendations.append(
            (
                95,
                "Create a positive monthly surplus first. "
                "Review discretionary expenses and look for ways "
                "to increase your monthly income."
            )
        )

    # -------------------------------------------------
    # Priority 3: Emergency Fund
    # -------------------------------------------------

    if emergency_fund_gap > 0:
        if emergency_fund_ratio < 0.50:
            priority = 94
        elif emergency_fund_ratio < 0.80:
            priority = 85
        else:
            priority = 75

        recommendations.append(
            (
                priority,
                f"Build your emergency fund. You are approximately "
                f"₹{emergency_fund_gap:,.0f} away from a six-month "
                "expense buffer."
            )
        )

    # -------------------------------------------------
    # Priority 4: Investments
    # -------------------------------------------------

    if investments <= 0:
        recommendations.append(
            (
                90,
                "Start building a diversified investment portfolio "
                "based on your risk profile. Even a small consistent "
                "monthly investment can help build long-term wealth."
            )
        )

    elif monthly_surplus > 0:
        if investment_ratio < 0.25:
            recommendations.append(
                (
                    82,
                    f"Your investment corpus is still relatively low "
                    f"compared with your income. Consider starting or "
                    f"increasing your monthly investment towards "
                    f"₹{recommended_sip:,.0f}."
                )
            )
        else:
            recommendations.append(
                (
                    60,
                    "Continue growing your investment corpus and "
                    "increase contributions gradually as your income "
                    "and surplus improve."
                )
            )

    # -------------------------------------------------
    # Priority 5: Retirement
    # -------------------------------------------------

    if retirement_years < 5:
        recommendations.append(
            (
                98,
                "Your planned retirement is less than five years away. "
                "Prioritize retirement corpus planning, adequate liquidity "
                "and a review of your current investment allocation."
            )
        )

    elif retirement_years < 10:
        recommendations.append(
            (
                88,
                "Your retirement timeline is relatively close. "
                "Review your retirement corpus and consider increasing "
                "long-term contributions where your cash flow allows."
            )
        )

    elif retirement_years < 15:
        recommendations.append(
            (
                68,
                "Keep retirement planning on track by maintaining "
                "consistent long-term investments and reviewing your "
                "progress periodically."
            )
        )

    # -------------------------------------------------
    # Priority 6: Goal Planning
    # -------------------------------------------------

    if monthly_surplus > 0 and goal:
        recommendations.append(
            (
                72,
                f"Stay consistent with your {goal} goal. "
                f"Your suggested starting investment is around "
                f"₹{recommended_sip:,.0f} per month based on your "
                "current surplus and risk level."
            )
        )

    # -------------------------------------------------
    # Priority 7: Risk-Based Advice
    # -------------------------------------------------

    if risk == "low":
        recommendations.append(
            (
                45,
                "Because your risk profile is conservative, prioritize "
                "capital preservation and diversified lower-volatility "
                "investments while keeping your long-term goals in mind."
            )
        )

    elif risk == "medium":
        recommendations.append(
            (
                45,
                "Maintain a balanced portfolio and review your equity "
                "and debt allocation periodically as your goals change."
            )
        )

    else:
        recommendations.append(
            (
                45,
                "Your higher risk profile may support greater equity "
                "exposure for long-term goals, but keep diversification "
                "and emergency liquidity in place."
            )
        )

    # -------------------------------------------------
    # Sort by Priority
    # -------------------------------------------------

    recommendations.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # Remove duplicate recommendation text
    seen = set()
    top_actions = []

    for priority, message in recommendations:
        if message not in seen:
            seen.add(message)
            top_actions.append(message)

        if len(top_actions) == 3:
            break

    # Fallback
    if not top_actions:
        top_actions = [
            "Continue following your financial plan consistently.",
            "Review your savings and investments regularly.",
            "Keep your emergency fund and long-term goals on track.",
        ]

    # -------------------------------------------------
    # Return Financial Plan
    # -------------------------------------------------

    return {
        "monthly_surplus": monthly_surplus,
        "emergency_fund_target": emergency_fund_target,
        "emergency_fund_gap": emergency_fund_gap,
        "emergency_fund_ratio": emergency_fund_ratio,
        "recommended_sip": recommended_sip,
        "retirement_years": retirement_years,
        "investment_strategy": investment_strategy,
        "goal_message": goal_message,
        "emergency_message": emergency_message,
        "surplus_message": surplus_message,
        "financial_health_score": score,
        "health_status": health_status,
        "top_actions": top_actions,
        "current_investments": investments,
    }


# -------------------------------------------------
# Home
# -------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------------------------------------
# Register
# -------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash(
                "Password must be at least 6 characters long.",
                "error",
            )
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    hashed_password,
                ),
            )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            flash(
                "An account with this email already exists.",
                "error",
            )
            return redirect(url_for("register"))

        conn.close()

        flash(
            "Registration successful. Please login.",
            "success",
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# -------------------------------------------------
# Login
# -------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password,
        ):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            flash(
                "Login successful.",
                "success",
            )

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "error",
        )

        return redirect(url_for("login"))

    return render_template("login.html")


# -------------------------------------------------
# Dashboard
# -------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()

    profile = conn.execute(
        """
        SELECT *
        FROM financial_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    financial_plan = None

    if profile:
        financial_plan = generate_financial_plan(profile)

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name"),
        user_email=session.get("user_email"),
        profile=profile,
        financial_plan=financial_plan,
    )


# -------------------------------------------------
# Financial Profile
# -------------------------------------------------

@app.route("/financial-profile", methods=["GET", "POST"])
def financial_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()

    existing_profile = conn.execute(
        """
        SELECT *
        FROM financial_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    if request.method == "POST":
        try:
            income = float(
                request.form.get("income", 0)
            )

            expenses = float(
                request.form.get("expenses", 0)
            )

            savings = float(
                request.form.get("savings", 0)
            )

            investments = float(
                request.form.get("investments", 0)
            )

            goal = request.form.get(
                "goal",
                "",
            ).strip()

            age = int(
                request.form.get("age", 0)
            )

            retirement_age = int(
                request.form.get(
                    "retirement_age",
                    0,
                )
            )

            risk = request.form.get(
                "risk",
                "",
            ).strip().lower()

        except (ValueError, TypeError):
            flash(
                "Please enter valid financial information.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if (
            income < 0
            or expenses < 0
            or savings < 0
            or investments < 0
        ):
            flash(
                "Financial amounts cannot be negative.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if age < 18 or age > 100:
            flash(
                "Please enter a valid age between 18 and 100.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if retirement_age < 40 or retirement_age > 100:
            flash(
                "Please enter a retirement age between 40 and 100.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if retirement_age <= age:
            flash(
                "Retirement age must be greater than your current age.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if not goal:
            flash(
                "Please enter your primary financial goal.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        if risk not in [
            "low",
            "medium",
            "high",
        ]:
            flash(
                "Please select a valid risk level.",
                "error",
            )

            return redirect(
                url_for("financial_profile")
            )

        conn = get_db()

        if existing_profile:
            conn.execute(
                """
                UPDATE financial_profiles
                SET income = ?,
                    expenses = ?,
                    savings = ?,
                    investments = ?,
                    goal = ?,
                    age = ?,
                    retirement_age = ?,
                    risk = ?
                WHERE user_id = ?
                """,
                (
                    income,
                    expenses,
                    savings,
                    investments,
                    goal,
                    age,
                    retirement_age,
                    risk,
                    user_id,
                ),
            )

        else:
            conn.execute(
                """
                INSERT INTO financial_profiles (
                    user_id,
                    income,
                    expenses,
                    savings,
                    investments,
                    goal,
                    age,
                    retirement_age,
                    risk
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    income,
                    expenses,
                    savings,
                    investments,
                    goal,
                    age,
                    retirement_age,
                    risk,
                ),
            )

        conn.commit()
        conn.close()

        flash(
            "Financial profile saved successfully.",
            "success",
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "financial_profile.html",
        profile=existing_profile,
    )


# -------------------------------------------------
# SIP Planning
# -------------------------------------------------

@app.route("/sip-planning", methods=["GET", "POST"])
def sip_planning():
    if "user_id" not in session:
        return redirect(url_for("login"))

    sip_result = None

    if request.method == "POST":
        try:
            goal_amount = float(
                request.form.get(
                    "goal_amount",
                    0,
                )
            )

            current_investment = float(
                request.form.get(
                    "current_investment",
                    0,
                )
            )

            years = int(
                request.form.get(
                    "years",
                    0,
                )
            )

            annual_return = float(
                request.form.get(
                    "annual_return",
                    0,
                )
            )

            if goal_amount <= 0:
                raise ValueError

            if current_investment < 0:
                raise ValueError

            if years <= 0:
                raise ValueError

            if annual_return < 0:
                raise ValueError

        except (ValueError, TypeError):
            flash(
                "Please enter valid SIP values.",
                "error",
            )

            return redirect(
                url_for("sip_planning")
            )

        months = years * 12
        monthly_rate = annual_return / 100 / 12

        current_value = current_investment

        for _ in range(months):
            current_value *= 1 + monthly_rate

        remaining_amount = max(
            goal_amount - current_value,
            0,
        )

        if monthly_rate > 0:
            monthly_sip = (
                remaining_amount
                * monthly_rate
                / (
                    (1 + monthly_rate) ** months - 1
                )
            )
        else:
            monthly_sip = (
                remaining_amount / months
            )

        total_sip = monthly_sip * months

        sip_result = {
            "monthly_sip": monthly_sip,
            "current_value": current_value,
            "remaining_amount": remaining_amount,
            "total_sip": total_sip,
            "goal_amount": goal_amount,
            "years": years,
        }

    return render_template(
        "sip_planning.html",
        sip_result=sip_result,
    )


# -------------------------------------------------
# SWP Planning
# -------------------------------------------------

@app.route("/swp-planning", methods=["GET", "POST"])
def swp_planning():
    if "user_id" not in session:
        return redirect(url_for("login"))

    swp_result = None

    if request.method == "POST":
        try:
            initial_corpus = float(
                request.form.get(
                    "initial_corpus",
                    0,
                )
            )

            monthly_withdrawal = float(
                request.form.get(
                    "monthly_withdrawal",
                    0,
                )
            )

            years = int(
                request.form.get(
                    "years",
                    0,
                )
            )

            annual_return = float(
                request.form.get(
                    "annual_return",
                    0,
                )
            )

            if initial_corpus <= 0:
                raise ValueError

            if monthly_withdrawal <= 0:
                raise ValueError

            if years <= 0:
                raise ValueError

            if annual_return < 0:
                raise ValueError

        except (ValueError, TypeError):
            flash(
                "Please enter valid SWP values.",
                "error",
            )

            return redirect(
                url_for("swp_planning")
            )

        months = years * 12
        monthly_rate = annual_return / 100 / 12

        corpus = initial_corpus
        total_withdrawal = 0
        months_completed = 0

        for _ in range(months):
            corpus *= 1 + monthly_rate

            if corpus <= 0:
                break

            withdrawal = min(
                monthly_withdrawal,
                corpus,
            )

            corpus -= withdrawal

            total_withdrawal += withdrawal
            months_completed += 1

            if corpus <= 0:
                corpus = 0
                break

        if (
            months_completed >= months
            and corpus > 0
        ):
            status_message = (
                "Your corpus is projected to support the planned "
                "withdrawals for the selected period."
            )

        elif corpus <= 0:
            status_message = (
                "Your corpus may be exhausted before the planned "
                "withdrawal period ends."
            )

        else:
            status_message = (
                "The projection was completed based on the selected "
                "withdrawal period."
            )

        swp_result = {
            "initial_corpus": initial_corpus,
            "monthly_withdrawal": monthly_withdrawal,
            "years": years,
            "annual_return": annual_return,
            "remaining_corpus": corpus,
            "total_withdrawal": total_withdrawal,
            "months_completed": months_completed,
            "status_message": status_message,
        }

    return render_template(
        "swp_planning.html",
        swp_result=swp_result,
    )


# -------------------------------------------------
# Retirement Planning
# -------------------------------------------------

@app.route(
    "/retirement-planning",
    methods=["GET", "POST"],
)
def retirement_planning():
    if "user_id" not in session:
        return redirect(url_for("login"))

    retirement_result = None

    if request.method == "POST":
        try:
            current_age = int(
                request.form.get(
                    "current_age",
                    0,
                )
            )

            retirement_age = int(
                request.form.get(
                    "retirement_age",
                    0,
                )
            )

            current_savings = float(
                request.form.get(
                    "current_savings",
                    0,
                )
            )

            monthly_investment = float(
                request.form.get(
                    "monthly_investment",
                    0,
                )
            )

            expected_return = float(
                request.form.get(
                    "expected_return",
                    0,
                )
            )

            monthly_expense = float(
                request.form.get(
                    "monthly_expense",
                    0,
                )
            )

            if current_age < 18 or current_age > 100:
                raise ValueError

            if retirement_age <= current_age:
                raise ValueError

            if current_savings < 0:
                raise ValueError

            if monthly_investment < 0:
                raise ValueError

            if expected_return < 0:
                raise ValueError

            if monthly_expense < 0:
                raise ValueError

        except (ValueError, TypeError):
            flash(
                "Please enter valid retirement planning values.",
                "error",
            )

            return redirect(
                url_for("retirement_planning")
            )

        years_to_retirement = (
            retirement_age - current_age
        )

        months_to_retirement = (
            years_to_retirement * 12
        )

        monthly_rate = (
            expected_return / 100 / 12
        )

        future_current_savings = current_savings

        for _ in range(months_to_retirement):
            future_current_savings *= (
                1 + monthly_rate
            )

        future_investments = 0

        for _ in range(months_to_retirement):
            future_investments = (
                future_investments
                * (1 + monthly_rate)
                + monthly_investment
            )

        estimated_corpus = (
            future_current_savings
            + future_investments
        )

        annual_retirement_expense = (
            monthly_expense * 12
        )

        required_corpus = (
            annual_retirement_expense * 25
        )

        corpus_gap = max(
            required_corpus - estimated_corpus,
            0,
        )

        if estimated_corpus >= required_corpus:
            status_message = (
                "Your projected retirement corpus appears sufficient "
                "based on the assumptions provided."
            )

        else:
            status_message = (
                "Your projected retirement corpus may fall short of "
                "the estimated requirement. Consider increasing your "
                "monthly investment or reviewing your retirement goal."
            )

        retirement_result = {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "years_to_retirement": years_to_retirement,
            "current_savings": current_savings,
            "monthly_investment": monthly_investment,
            "expected_return": expected_return,
            "monthly_expense": monthly_expense,
            "future_current_savings": future_current_savings,
            "future_investments": future_investments,
            "estimated_corpus": estimated_corpus,
            "annual_retirement_expense": annual_retirement_expense,
            "required_corpus": required_corpus,
            "corpus_gap": corpus_gap,
            "status_message": status_message,
        }

    return render_template(
        "retirement_planning.html",
        retirement_result=retirement_result,
    )


# -------------------------------------------------
# Financial Goals
# -------------------------------------------------

# -------------------------------------------------
# Financial Goals
# -------------------------------------------------

@app.route("/financial-goals", methods=["GET", "POST"])
def financial_goals():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    goal_result = None

    # -------------------------------------------------
    # POST - CALCULATE FINANCIAL GOAL
    # -------------------------------------------------

    if request.method == "POST":

        try:

            goal_name = request.form.get(
                "goal_name",
                ""
            ).strip()

            target_amount = float(
                request.form.get(
                    "target_amount",
                    0
                )
            )

            current_amount = float(
                request.form.get(
                    "current_amount",
                    0
                )
            )

            years = int(
                request.form.get(
                    "years",
                    0
                )
            )

            expected_return = float(
                request.form.get(
                    "expected_return",
                    0
                )
            )

        except (ValueError, TypeError):

            flash(
                "Please enter valid financial goal values.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not goal_name:

            flash(
                "Please enter a goal name.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        if target_amount <= 0:

            flash(
                "Target amount must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        if current_amount < 0:

            flash(
                "Current amount cannot be negative.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        if current_amount > target_amount:

            flash(
                "Current amount cannot be greater than target amount.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        if years <= 0:

            flash(
                "Investment period must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        if expected_return < 0:

            flash(
                "Expected return cannot be negative.",
                "error"
            )

            return redirect(
                url_for("financial_goals")
            )

        # -------------------------------------------------
        # CALCULATION
        # -------------------------------------------------

        months = years * 12

        monthly_rate = (
            expected_return / 100 / 12
        )

        # Future value of current amount

        future_current_amount = current_amount

        for _ in range(months):

            future_current_amount *= (
                1 + monthly_rate
            )

        # Amount still required

        remaining_amount = max(
            target_amount - future_current_amount,
            0
        )

        # Required monthly investment

        if monthly_rate > 0:

            monthly_required = (
                remaining_amount
                * monthly_rate
                / (
                    (1 + monthly_rate) ** months - 1
                )
            )

        else:

            monthly_required = (
                remaining_amount / months
            )

        # -------------------------------------------------
        # SAVE GOAL TO DATABASE
        # -------------------------------------------------

        conn = get_db()

        conn.execute(
            """
            INSERT INTO financial_goals (
                user_id,
                goal_name,
                target_amount,
                current_amount,
                years,
                expected_return,
                monthly_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                goal_name,
                target_amount,
                current_amount,
                years,
                expected_return,
                monthly_required
            )
        )

        conn.commit()
        conn.close()

        # -------------------------------------------------
        # RESULT
        # -------------------------------------------------

        goal_result = {

            "goal_name": goal_name,

            "target_amount": target_amount,

            "current_amount": current_amount,

            "future_current_amount": future_current_amount,

            "remaining_amount": remaining_amount,

            "years": years,

            "expected_return": expected_return,

            "monthly_required": monthly_required
        }

        flash(
            "Financial goal calculated and saved successfully.",
            "success"
        )

    # -------------------------------------------------
    # GET SAVED GOALS
    # -------------------------------------------------

    conn = get_db()

    saved_goals = conn.execute(
        """
        SELECT *
        FROM financial_goals
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    # -------------------------------------------------
    # RENDER PAGE
    # -------------------------------------------------

    return render_template(
        "financial_goals.html",
        goal_result=goal_result,
        saved_goals=saved_goals
    )

# -------------------------------------------------
# Logout
# -------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()

    flash(
        "You have been logged out.",
        "success",
    )

    return redirect(
        url_for("home")
    )


# -------------------------------------------------
# 404 Error Handler
# -------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):
    return "Page not found.", 404


# -------------------------------------------------
# Start Application
# -------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)