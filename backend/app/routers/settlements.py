"""Settlements: get who owes whom for a group, record payments."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Group, Expense, Payment
from app.schemas import (
    SettlementSummary, MemberInfo, PaymentCreate, PaymentResponse, DashboardStats,
)
from app.auth import get_current_user
from app.services.settlement_calculator import compute_settlements

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _compute_balances(group, expenses, payments):
    balances: dict[int, float] = {m.id: 0.0 for m in group.members}
    for e in expenses:
        if not e.participants:
            continue
        balances[e.payer_id] += e.amount
        if e.split_type == "custom" and e.shares:
            for s in e.shares:
                balances[s.user_id] -= s.share_amount
        else:
            share = e.amount / len(e.participants)
            for p in e.participants:
                balances[p.id] -= share

    for p in payments:
        balances[p.from_user_id] += p.amount
        balances[p.to_user_id] -= p.amount

    return {uid: round(bal, 2) for uid, bal in balances.items()}


@router.get("/group/{group_id}", response_model=SettlementSummary)
def get_settlements(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    payments = db.query(Payment).filter(Payment.group_id == group_id).all()

    balances = _compute_balances(group, expenses, payments)
    settlements = compute_settlements(balances)
    return SettlementSummary(
        group_id=group_id,
        members=[MemberInfo(id=m.id, name=m.name, email=m.email) for m in group.members],
        balances=[{"user_id": uid, "balance": bal} for uid, bal in balances.items()],
        settlements=settlements,
    )


@router.post("/pay", response_model=PaymentResponse)
def record_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == data.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    to_user = next((m for m in group.members if m.id == data.to_user_id), None)
    if not to_user:
        raise HTTPException(status_code=400, detail="Recipient must be a group member")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    payment = Payment(
        group_id=data.group_id,
        from_user_id=current_user.id,
        to_user_id=data.to_user_id,
        amount=data.amount,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentResponse.model_validate(payment)


@router.get("/payments/{group_id}", response_model=list[PaymentResponse])
def list_payments(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")

    payments = (
        db.query(Payment)
        .filter(Payment.group_id == group_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return [PaymentResponse.model_validate(p) for p in payments]


@router.get("/dashboard/{group_id}", response_model=DashboardStats)
def get_dashboard(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    payments = db.query(Payment).filter(Payment.group_id == group_id).all()

    total = sum(e.amount for e in expenses)
    cat_totals: dict[str, float] = {}
    member_paid: dict[int, float] = {m.id: 0.0 for m in group.members}

    for e in expenses:
        cat = e.category or "other"
        cat_totals[cat] = round(cat_totals.get(cat, 0) + e.amount, 2)
        member_paid[e.payer_id] += e.amount

    balances = _compute_balances(group, expenses, payments)
    member_map = {m.id: m.name or m.email for m in group.members}
    member_spending = [
        {"user_id": uid, "name": member_map.get(uid, str(uid)), "paid": round(paid, 2)}
        for uid, paid in member_paid.items()
    ]

    return DashboardStats(
        total_expenses=round(total, 2),
        expense_count=len(expenses),
        category_totals=cat_totals,
        member_spending=member_spending,
        your_balance=balances.get(current_user.id, 0),
    )
