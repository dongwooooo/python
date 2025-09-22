from flask import Flask, request, jsonify

app = Flask(__name__)

# 세율(10%)
VAT_RATE = 0.10

@app.post("/estimate")
def estimate_price():
    """
    요청(JSON):
      - price: 단가 (숫자, 필수)
      - quantity: 수량 (정수, 기본 1)

    응답(JSON):
      - unit_price: 단가(원)
      - quantity: 수량
      - subtotal: 세전 합계(원)
      - vat_rate: 세율
      - vat: 세액(원)
      - total: 세후 합계(원)
    """
    data = request.get_json(silent=True) or {}

    # price 검증
    if "price" not in data:
        return jsonify({"error": "price(단가) 필수입니다."}), 400
    try:
        price = float(data["price"])
    except (TypeError, ValueError):
        return jsonify({"error": "price는 숫자여야 합니다."}), 400

    # quantity 검증
    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity는 정수여야 합니다."}), 400
    if quantity <= 0:
        return jsonify({"error": "quantity는 1 이상이어야 합니다."}), 400

    # 계산
    subtotal = price * quantity
    vat = round(subtotal * VAT_RATE)       # 원 단위 반올림
    total = int(round(subtotal + vat))

    return jsonify({
        "unit_price": int(round(price)),
        "quantity": quantity,
        "subtotal": int(round(subtotal)),
        "vat_rate": VAT_RATE,
        "vat": int(vat),
        "total": total
    })

if __name__ == "__main__":
    # 개발 실행용
    app.run(host="0.0.0.0", port=5000, debug=True)
