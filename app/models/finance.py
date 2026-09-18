from datetime import datetime, timezone

from app import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    # "income" or "expense" — keeps aggregation queries simple later
    type = db.Column(db.String(10), nullable=False, default="expense")

    transactions = db.relationship("Transaction", backref="category", lazy=True)

    def __init__(self, name: str, type: str = "expense", **kwargs):
        super().__init__(name=name, type=type, **kwargs)

    def __repr__(self):
        return f"<Category {self.name}>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    amount = db.Column(db.Numeric(10, 2, asdecimal=True), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "income" or "expense"
    note = db.Column(db.String(255))
    date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, user_id: int, amount, type: str, category_id: int | None = None, note: str | None = None, date = None, **kwargs):
        super().__init__(user_id=user_id, amount=amount, type=type, category_id=category_id, note=note, date=date, **kwargs)

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount}>"
