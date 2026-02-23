"""Minimize number of transfers so everyone is settled (who owes whom)."""
from collections import defaultdict
from app.schemas import SettlementItem


def compute_settlements(balances: dict[int, float]) -> list[SettlementItem]:
    """
    balances: user_id -> net balance (positive = is owed money, negative = owes money).
    Returns minimal list of transfers to settle up.
    """
    debtors = []  # (user_id, amount_owed)
    creditors = []
    for uid, bal in balances.items():
        if bal < -1e-9:
            debtors.append((uid, -bal))
        elif bal > 1e-9:
            creditors.append((uid, bal))
    debtors.sort(key=lambda x: -x[1])
    creditors.sort(key=lambda x: -x[1])

    out: list[SettlementItem] = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        du, d_amount = debtors[i]
        cu, c_amount = creditors[j]
        transfer = min(d_amount, c_amount)
        if transfer < 1e-9:
            break
        out.append(SettlementItem(from_user_id=du, to_user_id=cu, amount=round(transfer, 2)))
        debtors[i] = (du, d_amount - transfer)
        creditors[j] = (cu, c_amount - transfer)
        if debtors[i][1] < 1e-9:
            i += 1
        if creditors[j][1] < 1e-9:
            j += 1
    return out
