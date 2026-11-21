def score_contract(amount_minor, supplier_score, months_active):
    risk = 0
    if amount_minor > 500000000:
        risk = risk + 35
    elif amount_minor > 100000000:
        risk = risk + 20
    if supplier_score < 30:
        risk = risk + 35
    elif supplier_score < 60:
        risk = risk + 20
    if months_active < 6:
        risk = risk + 25
    elif months_active < 24:
        risk = risk + 10
    if amount_minor > 200000000 and supplier_score < 45 and risk < 90:
        risk = 90
    if risk > 100:
        risk = 100
    return risk
