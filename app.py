from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------
# 샘플 데이터 (사전형)
# ---------------------------
customers = {
    1: {"id": 1, "name": "김선민", "age": 31, "address": "경기 남양주시 진접", "phone": "010-1111-2222"},
    2: {"id": 2, "name": "이서준", "age": 29, "address": "서울 강북구 미아", "phone": "010-3333-4444"},
    3: {"id": 3, "name": "박지민", "age": 27, "address": "경기 김포시 걸포", "phone": "010-5555-6666"},
}

products = {
    101: {"id": 101, "name": "무선 이어폰", "price": 129000, "desc": "ANC 지원"},
    102: {"id": 102, "name": "기계식 키보드", "price": 89000, "desc": "청축, RGB 백라이트"},
    103: {"id": 103, "name": "게이밍 마우스", "price": 59000, "desc": "고정밀 센서, 매크로 지원"},
}

# ---------------------------
# 검색 유틸 (대소문자 무시, 부분일치)
# ---------------------------
def contains(text, keyword: str) -> bool:
    if keyword is None or keyword.strip() == "":
        return True
    return keyword.lower() in str(text).lower()

def search_dict(dict_obj: dict, q: str):
    """사전형(dict[int, dict])에서 값들 중 하나라도 q를 포함하면 매칭"""
    if not q:
        return list(dict_obj.values())
    out = []
    for item in dict_obj.values():
        if any(contains(v, q) for v in item.values()):
            out.append(item)
    return out

# ---------------------------
# 라우트
# ---------------------------

@app.get("/")
def all_data():
    """모든 고객/상품 정보 한 번에 조회"""
    return jsonify({
        "customers": list(customers.values()),
        "products": list(products.values()),
    })

@app.get("/customers")
def customers_route():
    """
    고객 조회/검색
    - 전체: /customers
    - 키워드: /customers?q=키워드
    - (선택) 단건: /customers?id=1
    """
    q = request.args.get("q", "").strip()
    id_str = request.args.get("id")

    if id_str:
        try:
            cid = int(id_str)
            return jsonify([customers[cid]]) if cid in customers else jsonify([])
        except ValueError:
            return jsonify([])

    return jsonify(search_dict(customers, q))

@app.get("/products")
def products_route():
    """
    상품 조회/검색ㅋ
    - 전체: /products
    - 키워드: /products?q=키워드
    - (선택) 단건: /products?id=101
    """
    q = request.args.get("q", "").strip()
    id_str = request.args.get("id")

    if id_str:
        try:
            pid = int(id_str)
            return jsonify([products[pid]]) if pid in products else jsonify([])
        except ValueError:
            return jsonify([])

    return jsonify(search_dict(products, q))

# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
