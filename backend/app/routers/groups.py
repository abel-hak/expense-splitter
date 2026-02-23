"""Groups: create, list, get, update, delete, add/remove members."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Group
from app.schemas import GroupCreate, GroupUpdate, GroupResponse, GroupAddMember, MemberInfo
from app.auth import get_current_user

router = APIRouter(prefix="/groups", tags=["groups"])


def _member_info(user: User) -> MemberInfo:
    return MemberInfo(id=user.id, name=user.name, email=user.email)


def _group_response(group: Group) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        member_ids=[u.id for u in group.members],
        members=[_member_info(u) for u in group.members],
    )


@router.get("", response_model=list[GroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    groups = db.query(Group).filter(Group.members.any(User.id == current_user.id)).all()
    return [_group_response(g) for g in groups]


@router.post("", response_model=GroupResponse)
def create_group(
    data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    members = [current_user]
    if data.member_ids:
        others = db.query(User).filter(User.id.in_(data.member_ids)).all()
        for u in others:
            if u not in members:
                members.append(u)
    group = Group(name=data.name, description=data.description)
    group.members = members
    db.add(group)
    db.commit()
    db.refresh(group)
    return _group_response(group)


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    return _group_response(group)


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    data: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    db.commit()
    db.refresh(group)
    return _group_response(group)


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/members", response_model=GroupResponse)
def add_group_member(
    group_id: int,
    data: GroupAddMember,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found with that email")
    if user in group.members:
        raise HTTPException(status_code=400, detail="User already in group")
    group.members.append(user)
    db.commit()
    db.refresh(group)
    return _group_response(group)


@router.delete("/{group_id}/members/{user_id}", response_model=GroupResponse)
def remove_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member")
    user = next((m for m in group.members if m.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not in this group")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    group.members.remove(user)
    db.commit()
    db.refresh(group)
    return _group_response(group)
