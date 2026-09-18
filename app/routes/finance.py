from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models.finance import Transaction, Category

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")


@finance_bp.route("/")
@login_required
def list_transactions():
    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.date.desc())
        .all()
    )
    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "finance/list.html", transactions=transactions, categories=categories
    )


@finance_bp.route("/add", methods=["POST"])
@login_required
def add_transaction():
    amount_str = request.form.get("amount")
    ttype = request.form.get("type")
    category_id = request.form.get("category_id") or None
    note = request.form.get("note", "").strip()
    date_str = request.form.get("date")

    if not amount_str or not ttype:
        flash("Amount and type are required.", "danger")
        return redirect(url_for("finance.list_transactions"))

    try:
        amount_val = Decimal(amount_str)
        if amount_val <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("finance.list_transactions"))
    except (ValueError, InvalidOperation):
        flash("Invalid amount format.", "danger")
        return redirect(url_for("finance.list_transactions"))

    try:
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now(timezone.utc).date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("finance.list_transactions"))

    txn = Transaction(
        user_id=current_user.id,
        amount=amount_val,
        type=ttype,
        category_id=int(category_id) if category_id else None,
        note=note,
        date=date_val,
    )
    db.session.add(txn)
    db.session.commit()

    flash("Transaction added.", "success")
    return redirect(url_for("finance.list_transactions"))


@finance_bp.route("/delete/<int:txn_id>", methods=["POST"])
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first_or_404()
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("finance.list_transactions"))
