"""Pydantic schemas for request/response."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ----- User -----
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MemberInfo(BaseModel):
    id: int
    name: Optional[str] = None
    email: EmailStr


# ----- Group -----
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    member_ids: list[int] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupAddMember(BaseModel):
    email: EmailStr


class GroupResponse(GroupBase):
    id: int
    created_at: Optional[datetime] = None
    member_ids: list[int] = []
    members: list[MemberInfo] = []

    class Config:
        from_attributes = True


# ----- Expense -----
EXPENSE_CATEGORIES = [
    "food",
    "transport",
    "housing",
    "entertainment",
    "utilities",
    "shopping",
    "health",
    "travel",
    "education",
    "other",
]


class ExpenseBase(BaseModel):
    amount: float
    description: Optional[str] = None
    participant_ids: list[int]


class ExpenseCreate(ExpenseBase):
    group_id: int
    payer_id: int
    split_type: str = "equal"
    shares: Optional[dict[int, float]] = None
    category: Optional[str] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    participant_ids: Optional[list[int]] = None
    split_type: Optional[str] = None
    shares: Optional[dict[int, float]] = None
    category: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    id: int
    group_id: int
    payer_id: int
    split_type: str = "equal"
    shares: Optional[dict[int, float]] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ----- Payment (settle up) -----
class PaymentCreate(BaseModel):
    group_id: int
    to_user_id: int
    amount: float


class PaymentResponse(BaseModel):
    id: int
    group_id: int
    from_user_id: int
    to_user_id: int
    amount: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ----- Settlement -----
class SettlementItem(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: float


class SettlementSummary(BaseModel):
    group_id: int
    members: list[MemberInfo] = []
    balances: list[dict]
    settlements: list[SettlementItem]


# ----- Dashboard -----
class DashboardStats(BaseModel):
    total_expenses: float
    expense_count: int
    category_totals: dict[str, float]
    member_spending: list[dict]
    your_balance: float
