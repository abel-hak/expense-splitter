"""Expenses: create, list, update, delete, export."""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Group, Expense, ExpenseShare
from app.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse, EXPENSE_CATEGORIES
from app.auth import get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _expense_response(exp: Expense) -> ExpenseResponse:
    shares = None
    if exp.split_type == "custom" and exp.shares:
        shares = {s.user_id: s.share_amount for s in exp.shares}
    return ExpenseResponse(
        id=exp.id,
        group_id=exp.group_id,
        payer_id=exp.payer_id,
        amount=exp.amount,
        description=exp.description,
        category=exp.category,
        split_type=exp.split_type or "equal",
        shares=shares,
        created_at=exp.created_at,
        participant_ids=[p.id for p in exp.participants],
    )


def _check_group_member(db: Session, group_id: int, user: User) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return group


@router.post("", response_model=ExpenseResponse)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _check_group_member(db, data.group_id, current_user)
    payer = next((m for m in group.members if m.id == data.payer_id), None)
    if not payer:
        raise HTTPException(status_code=400, detail="Payer must be a group member")
    if not data.participant_ids:
        raise HTTPException(status_code=400, detail="At least one participant required")
    participants = [m for m in group.members if m.id in data.participant_ids]
    if len(participants) != len(data.participant_ids):
        raise HTTPException(status_code=400, detail="All participants must be group members")

    if data.category and data.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(EXPENSE_CATEGORIES)}")

    split_type = data.split_type or "equal"
    if split_type == "custom":
        if not data.shares:
            raise HTTPException(status_code=400, detail="Custom split requires shares")
        if set(data.shares.keys()) != set(data.participant_ids):
            raise HTTPException(status_code=400, detail="Shares must match participant list")
        total_shares = round(sum(data.shares.values()), 2)
        if abs(total_shares - data.amount) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Shares total ({total_shares}) must equal expense amount ({data.amount})",
            )

    expense = Expense(
        group_id=data.group_id,
        payer_id=data.payer_id,
        amount=data.amount,
        description=data.description,
        category=data.category,
        split_type=split_type,
    )
    expense.participants = participants
    db.add(expense)
    db.flush()

    if split_type == "custom" and data.shares:
        for uid, amt in data.shares.items():
            db.add(ExpenseShare(expense_id=expense.id, user_id=uid, share_amount=amt))

    db.commit()
    db.refresh(expense)
    return _expense_response(expense)


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(
    group_id: int,
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_group_member(db, group_id, current_user)
    q = db.query(Expense).filter(Expense.group_id == group_id)

    if search:
        q = q.filter(Expense.description.ilike(f"%{search}%"))
    if category:
        q = q.filter(Expense.category == category)

    expenses = q.order_by(Expense.created_at.desc()).offset(offset).limit(limit).all()
    return [_expense_response(e) for e in expenses]


@router.get("/export")
def export_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _check_group_member(db, group_id, current_user)
    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc())
        .all()
    )
    member_map = {m.id: m.name or m.email for m in group.members}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Amount", "Paid By", "Split Type", "Participants"])
    for e in expenses:
        payer_name = member_map.get(e.payer_id, str(e.payer_id))
        participants = ", ".join(member_map.get(p.id, str(p.id)) for p in e.participants)
        date_str = e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else ""
        writer.writerow([
            date_str,
            e.description or "",
            e.category or "",
            f"{e.amount:.2f}",
            payer_name,
            e.split_type or "equal",
            participants,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expenses-group-{group_id}.csv"},
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    _check_group_member(db, expense.group_id, current_user)
    return _expense_response(expense)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    group = _check_group_member(db, expense.group_id, current_user)

    if data.amount is not None:
        expense.amount = data.amount
    if data.description is not None:
        expense.description = data.description
    if data.category is not None:
        if data.category and data.category not in EXPENSE_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category")
        expense.category = data.category if data.category else None

    if data.participant_ids is not None:
        participants = [m for m in group.members if m.id in data.participant_ids]
        if len(participants) != len(data.participant_ids):
            raise HTTPException(status_code=400, detail="All participants must be group members")
        expense.participants = participants

    if data.split_type is not None:
        expense.split_type = data.split_type
        for old_share in expense.shares:
            db.delete(old_share)
        db.flush()
        if data.split_type == "custom" and data.shares:
            final_amount = data.amount if data.amount is not None else expense.amount
            total_shares = round(sum(data.shares.values()), 2)
            if abs(total_shares - final_amount) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Shares total ({total_shares}) must equal expense amount ({final_amount})",
                )
            for uid, amt in data.shares.items():
                db.add(ExpenseShare(expense_id=expense.id, user_id=uid, share_amount=amt))

    db.commit()
    db.refresh(expense)
    return _expense_response(expense)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    _check_group_member(db, expense.group_id, current_user)
    db.delete(expense)
    db.commit()
