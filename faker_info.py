# faker_info.py
# pip install faker
from faker import Faker
import random
import shutil
import textwrap

def one_line(s: str) -> str:
    # 줄바꿈/여러 공백을 한 칸으로 정리
    return " ".join(str(s).split())

def generate_people(n=10, locale="ko_KR"):
    fake = Faker(locale)
    people = []
    for _ in range(n):
        people.append({
            "이름": one_line(fake.name()),
            "나이": random.randint(20, 60),
            "직업": one_line(fake.job()),
            "이메일": one_line(fake.email()),
            "전화번호": one_line(fake.phone_number()),
            "주소": one_line(fake.address()),
        })
    # 이름 → 나이(오름차순)
    people.sort(key=lambda r: (r["이름"], r["나이"]))
    return people

def clip(s: str, width: int) -> str:
    """너무 길면 width에 맞춰 … 으로 말줄임"""
    if width <= 1:
        return "…" if width == 1 else ""
    return textwrap.shorten(s, width=width, placeholder="…")

def print_one_line(rows):
    # 터미널 가로폭 확인 (없으면 기본 120)
    term_cols = shutil.get_terminal_size(fallback=(120, 24)).columns

    # 고정 폭(필요시 조절 가능)
    NAME_W  = 14   # 이름
    JOB_W   = 16   # 직업
    MAIL_W  = 26   # 이메일
    PHONE_W = 19   # 전화번호
    MIN_ADDR_W = 8 # 주소 최소 폭

    for i, r in enumerate(rows, 1):
        name  = clip(r["이름"], NAME_W)
        job   = clip(r["직업"], JOB_W)
        mail  = clip(r["이메일"], MAIL_W)
        phone = clip(r["전화번호"], PHONE_W)

        left = f"[{i:02}] {name}({r['나이']}) | {job} | {mail} | {phone} | "
        # 남은 공간을 주소에 할당
        addr_w = max(MIN_ADDR_W, term_cols - len(left))
        addr  = clip(r["주소"], addr_w)

        line = left + addr
        # 혹시라도 이모지/한글 폭 차이로 넘치면 한 번 더 자르기
        if len(line) > term_cols:
            line = line[:max(0, term_cols - 1)] + "…"
        print(line)

    print(f"\n총 {len(rows)}명 출력됨.")

if __name__ == "__main__":
    data = generate_people(n=10, locale="ko_KR")
    print_one_line(data)
