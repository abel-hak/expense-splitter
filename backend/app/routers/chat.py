"""AI Chat: natural-language interface to expense management via Gemini."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import google.generativeai as genai

from app.database import get_db
from app.models import User, Group, Expense, Payment
from app.schemas import ChatRequest, ChatResponse, EXPENSE_CATEGORIES
from app.auth import get_current_user
from app.services.settlement_calculator import compute_settlements

router = APIRouter(prefix="/chat", tags=["chat"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# Gemini function declarations
# ---------------------------------------------------------------------------

_FUNCTIONS = [
    genai.protos.FunctionDeclaration(
        name="add_expense",
        description="Add a new expense to a group. The current user is the payer unless stated otherwise.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group to add the expense to."),
                "amount": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Total expense amount."),
                "description": genai.protos.Schema(type=genai.protos.Type.STRING, description="Short description of the expense (e.g. 'dinner', 'taxi')."),
                "category": genai.protos.Schema(type=genai.protos.Type.STRING, description=f"Expense category. Must be one of: {', '.join(EXPENSE_CATEGORIES)}."),
                "participant_names": genai.protos.Schema(type=genai.protos.Type.ARRAY, items=genai.protos.Schema(type=genai.protos.Type.STRING), description="Names or emails of people to split with. Use 'all' to include everyone in the group."),
            },
            required=["group_name", "amount", "description"],
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="get_balances",
        description="Get who owes whom in a group and suggested settlements.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group."),
            },
            required=["group_name"],
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="get_dashboard",
        description="Get spending statistics and summary for a group: total expenses, category breakdown, per-member spending.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group."),
            },
            required=["group_name"],
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="settle_debt",
        description="Record a payment to settle a debt with another group member.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group."),
                "to_user_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name or email of the person being paid."),
                "amount": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Amount to pay."),
            },
            required=["group_name", "to_user_name", "amount"],
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="list_expenses",
        description="List recent expenses for a group, optionally filtered by search term or category.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group."),
                "search": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional search term to filter expenses by description."),
                "category": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional category to filter by."),
            },
            required=["group_name"],
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="add_member",
        description="Add a new member to a group by their email address.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "group_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Name of the group."),
                "email": genai.protos.Schema(type=genai.protos.Type.STRING, description="Email address of the person to add."),
            },
            required=["group_name", "email"],
        ),
    ),
]

# ---------------------------------------------------------------------------
# Helpers: resolve names to DB objects
# ---------------------------------------------------------------------------

def _find_group(db: Session, user: User, name: str) -> Group:
    groups = db.query(Group).filter(Group.members.any(User.id == user.id)).all()
    name_lower = name.lower()
    for g in groups:
        if g.name.lower() == name_lower:
            return g
    for g in groups:
        if name_lower in g.name.lower():
            return g
    raise ValueError(f"No group named '{name}' found. Your groups: {', '.join(g.name for g in groups)}")


def _find_member(group: Group, name_or_email: str) -> User:
    val = name_or_email.lower().strip()
    for m in group.members:
        if m.email.lower() == val or (m.name and m.name.lower() == val):
            return m
    for m in group.members:
        if (m.name and val in m.name.lower()) or val in m.email.lower():
            return m
    member_names = [m.name or m.email for m in group.members]
    raise ValueError(f"No member '{name_or_email}' found in group. Members: {', '.join(member_names)}")


def _compute_balances(group: Group, db: Session) -> dict[int, float]:
    expenses = db.query(Expense).filter(Expense.group_id == group.id).all()
    payments = db.query(Payment).filter(Payment.group_id == group.id).all()
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


# ---------------------------------------------------------------------------
# Action executors — each returns (action_name, result_dict, summary_text)
# ---------------------------------------------------------------------------

def _exec_add_expense(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    amount = float(args["amount"])
    description = args.get("description", "expense")
    category = args.get("category")
    if category and category not in EXPENSE_CATEGORIES:
        category = "other"

    participant_names = args.get("participant_names", ["all"])
    if not participant_names or (len(participant_names) == 1 and str(participant_names[0]).lower() == "all"):
        participants = list(group.members)
    else:
        participants = []
        for pname in participant_names:
            pname_str = str(pname).lower()
            if pname_str in ("me", "myself") or (user.name and pname_str == user.name.lower()):
                if user not in participants:
                    participants.append(user)
            else:
                participants.append(_find_member(group, str(pname)))
        if user not in participants:
            participants.append(user)

    expense = Expense(
        group_id=group.id,
        payer_id=user.id,
        amount=amount,
        description=description,
        category=category,
        split_type="equal",
    )
    expense.participants = participants
    db.add(expense)
    db.commit()
    db.refresh(expense)

    names = [m.name or m.email for m in participants]
    per_person = round(amount / len(participants), 2)
    summary = f"Added ${amount:.2f} for '{description}' in {group.name}, split equally among {', '.join(names)} (${per_person:.2f} each)."
    return "add_expense", {"expense_id": expense.id, "amount": amount, "group": group.name}, summary


def _exec_get_balances(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    balances = _compute_balances(group, db)
    settlements = compute_settlements(balances)

    member_map = {m.id: m.name or m.email for m in group.members}
    balance_lines = []
    for uid, bal in balances.items():
        name = member_map[uid]
        if uid == user.id:
            name = "You"
        if bal > 0.01:
            balance_lines.append(f"  {name}: is owed ${bal:.2f}")
        elif bal < -0.01:
            balance_lines.append(f"  {name}: owes ${abs(bal):.2f}")
        else:
            balance_lines.append(f"  {name}: settled up")

    settle_lines = []
    for s in settlements:
        f_name = "You" if s.from_user_id == user.id else member_map.get(s.from_user_id, "?")
        t_name = "You" if s.to_user_id == user.id else member_map.get(s.to_user_id, "?")
        settle_lines.append(f"  {f_name} pays {t_name} ${s.amount:.2f}")

    summary = f"Balances in {group.name}:\n" + "\n".join(balance_lines)
    if settle_lines:
        summary += "\n\nSuggested settlements:\n" + "\n".join(settle_lines)
    else:
        summary += "\n\nEveryone is settled up!"

    return "get_balances", {"group": group.name}, summary


def _exec_get_dashboard(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    expenses = db.query(Expense).filter(Expense.group_id == group.id).all()

    total = sum(e.amount for e in expenses)
    cat_totals: dict[str, float] = {}
    member_paid: dict[int, float] = {m.id: 0.0 for m in group.members}
    for e in expenses:
        cat = e.category or "other"
        cat_totals[cat] = round(cat_totals.get(cat, 0) + e.amount, 2)
        member_paid[e.payer_id] += e.amount

    member_map = {m.id: m.name or m.email for m in group.members}
    cat_lines = [f"  {cat}: ${amt:.2f}" for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1])]
    member_lines = [f"  {member_map[uid]}: paid ${amt:.2f}" for uid, amt in member_paid.items() if amt > 0]

    summary = f"Dashboard for {group.name}:\n"
    summary += f"  Total expenses: ${total:.2f} ({len(expenses)} expenses)\n"
    if cat_lines:
        summary += "\nBy category:\n" + "\n".join(cat_lines)
    if member_lines:
        summary += "\n\nBy member:\n" + "\n".join(member_lines)

    return "get_dashboard", {"group": group.name, "total": total}, summary


def _exec_settle_debt(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    to_user = _find_member(group, args["to_user_name"])
    amount = float(args["amount"])
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    payment = Payment(
        group_id=group.id,
        from_user_id=user.id,
        to_user_id=to_user.id,
        amount=amount,
    )
    db.add(payment)
    db.commit()
    to_name = to_user.name or to_user.email
    summary = f"Recorded payment of ${amount:.2f} from you to {to_name} in {group.name}."
    return "settle_debt", {"group": group.name, "amount": amount, "to": to_name}, summary


def _exec_list_expenses(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    q = db.query(Expense).filter(Expense.group_id == group.id)
    search = args.get("search")
    category = args.get("category")
    if search:
        q = q.filter(Expense.description.ilike(f"%{search}%"))
    if category:
        q = q.filter(Expense.category == category)

    expenses = q.order_by(Expense.created_at.desc()).limit(10).all()
    member_map = {m.id: m.name or m.email for m in group.members}

    if not expenses:
        return "list_expenses", {"group": group.name, "count": 0}, f"No expenses found in {group.name}."

    lines = []
    for e in expenses:
        payer = member_map.get(e.payer_id, "?")
        cat = f" [{e.category}]" if e.category else ""
        lines.append(f"  ${e.amount:.2f} - {e.description or 'No description'}{cat} (paid by {payer})")

    summary = f"Recent expenses in {group.name}:\n" + "\n".join(lines)
    return "list_expenses", {"group": group.name, "count": len(expenses)}, summary


def _exec_add_member(db: Session, user: User, args: dict) -> tuple[str, dict, str]:
    group = _find_group(db, user, args["group_name"])
    email = args["email"].strip().lower()
    new_user = db.query(User).filter(User.email == email).first()
    if not new_user:
        raise ValueError(f"No registered user with email '{email}'. They need to sign up first.")
    if new_user in group.members:
        raise ValueError(f"{new_user.name or email} is already in {group.name}.")
    group.members.append(new_user)
    db.commit()
    name = new_user.name or email
    summary = f"Added {name} to {group.name}."
    return "add_member", {"group": group.name, "member": name}, summary


_EXECUTORS = {
    "add_expense": _exec_add_expense,
    "get_balances": _exec_get_balances,
    "get_dashboard": _exec_get_dashboard,
    "settle_debt": _exec_settle_debt,
    "list_expenses": _exec_list_expenses,
    "add_member": _exec_add_member,
}

# ---------------------------------------------------------------------------
# Build user context for the system prompt
# ---------------------------------------------------------------------------

def _build_context(db: Session, user: User, group_id: Optional[int]) -> str:
    groups = db.query(Group).filter(Group.members.any(User.id == user.id)).all()
    if not groups:
        return f"User: {user.name or user.email} (id={user.id}). They have no groups yet."

    lines = [f"User: {user.name or user.email} (id={user.id})"]
    lines.append(f"Groups ({len(groups)}):")
    for g in groups:
        members = ", ".join(f"{m.name or m.email}" for m in g.members)
        marker = " [SELECTED]" if group_id and g.id == group_id else ""
        lines.append(f"  - {g.name}{marker}: members = [{members}]")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are the AI assistant for Expense Splitter, an app for splitting expenses with friends.

You help users:
- Add expenses and split them with group members
- Check balances and who owes whom
- View spending dashboards and summaries
- Settle debts between members
- List and search expenses
- Add members to groups

Rules:
- Be concise and friendly. Use short responses.
- When the user mentions people by name, match them to group members.
- If the user says "I paid" or "I spent", they are the payer.
- If the user doesn't specify participants, split among all group members.
- If the user doesn't specify a category, pick the most appropriate one from the available list.
- If the user has a [SELECTED] group, default to that group when they don't specify one.
- Amounts are in dollars ($).
- After performing an action, confirm what was done concisely.
- If you're unsure which group or member the user means, ask for clarification instead of guessing.
"""

# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not GEMINI_API_KEY:
        return ChatResponse(reply="AI chat is not configured. The GEMINI_API_KEY environment variable is missing.")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools=[genai.protos.Tool(function_declarations=_FUNCTIONS)],
            system_instruction=SYSTEM_PROMPT + "\n\n" + _build_context(db, current_user, data.group_id),
            generation_config=genai.GenerationConfig(temperature=0.3),
        )

        chat_session = model.start_chat()
        response = chat_session.send_message(data.message)
    except Exception as exc:
        err_msg = str(exc)
        if "quota" in err_msg.lower() or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return ChatResponse(reply="The AI service is temporarily at capacity. Please try again in a minute.")
        return ChatResponse(reply=f"AI service error: {err_msg}")

    try:
        part = response.candidates[0].content.parts[0]
    except (IndexError, AttributeError):
        return ChatResponse(reply="I didn't get a response from the AI. Please try again.")

    if part.function_call:
        fc = part.function_call
        fn_name = fc.name
        fn_args = dict(fc.args) if fc.args else {}

        executor = _EXECUTORS.get(fn_name)
        if not executor:
            return ChatResponse(reply=f"I tried to use an unknown action '{fn_name}'. Please try rephrasing.")

        try:
            action, result_data, summary = executor(db, current_user, fn_args)
        except Exception as exc:
            return ChatResponse(reply=f"Sorry, I couldn't do that: {exc}", action=fn_name, data={"error": str(exc)})

        try:
            followup = chat_session.send_message(
                genai.protos.Content(parts=[
                    genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=fn_name,
                        response={"result": summary},
                    ))
                ])
            )
            reply = followup.text or summary
        except Exception:
            reply = summary

        return ChatResponse(reply=reply, action=action, data=result_data)

    return ChatResponse(reply=part.text or "I'm not sure how to help with that. Try asking about expenses, balances, or settlements.")
