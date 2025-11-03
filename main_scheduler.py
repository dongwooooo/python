
# -*- coding: utf-8 -*-
"""
Timetable Auto-Assignment (Final Project) - A안 (학점=주당시수)

- 입력: courses_data.csv (교수님 별첨 파일 그대로 사용)
        rooms.csv (없으면 1215/1216/1217/1418 기본 생성)
- 규칙: 1시간 블록(09:00-21:00), 월-금
       실습 과목은 lab 전용(1217/1418), 강의 과목은 lecture 전용(1215/1216)
       수용인원(capacity)은 무시 (옵션 --respect-capacity로 활성화 가능)
       강의실 부족하면 외부대여-타강의실1 1개만 자동 추가
- 산출물: assigned_schedule.csv, vacant_slots.csv, calendar_google_import.csv, utilization.png

사용 예시:
  python main_scheduler.py --courses courses_data.csv --rooms rooms.csv \
    --department-filter "소프트웨어융합" --anchor-date 2025-11-03

선택 옵션:
  --department-filter     : 개설학과에 이 문자열을 포함하는 행만 사용 (예: 소프트웨어융합)
  --anchor-date YYYY-MM-DD: 구글 캘린더 변환 기준 주 월요일 (기본 2025-11-03)
  --start-hour            : 하루 시작 시각 (기본 9)
  --end-hour              : 하루 종료 시각(종료 시간 자체는 포함 안 됨, 기본 21)
  --respect-capacity      : rooms.csv의 capacity를 수강인원과 비교하여 초과 시 배정 금지
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from collections import namedtuple

import pandas as pd
import matplotlib.pyplot as plt

def read_csv_auto(path):
    last_err = None
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"CSV 읽기 실패: {path} (encodings tried: utf-8, cp949, euc-kr)\n{last_err}")

def ensure_rooms_csv(path):
    if not os.path.exists(path):
        df = pd.DataFrame([
            {"room_id":"1215","room_type":"lecture","capacity":9999},
            {"room_id":"1216","room_type":"lecture","capacity":9999},
            {"room_id":"1217","room_type":"lab","capacity":9999},
            {"room_id":"1418","room_type":"lab","capacity":9999},
        ])
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[INFO] rooms.csv 생성: {path}")
    return read_csv_auto(path)

def requires_lab_flag(kind: str) -> str:
    kind = str(kind).strip()
    return "Y" if "실습" in kind else "N"

def build_courses_frame(df_courses_raw, department_filter=None):
    # 필수 컬럼 확인
    need = ["교과목코드","교과목명","강좌담당교수","수강인원","교과목학점","강의유형구분","개설학과"]
    for col in need:
        if col not in df_courses_raw.columns:
            raise RuntimeError(f"필수 열 누락: {col}")

    df = df_courses_raw.copy()

    if department_filter:
        mask = df["개설학과"].astype(str).str.contains(department_filter, na=False)
        df = df[mask].copy()
        if df.empty:
            raise RuntimeError(f"'{department_filter}' 필터 결과가 없습니다. --department-filter 값을 확인하세요.")

    rows = []
    for _, r in df.iterrows():
        try:
            hours = int(pd.to_numeric(r["교과목학점"], errors="raise"))
        except Exception:
            # 학점이 비정상일 경우 0으로
            hours = 0
        rows.append({
            "course_id": str(r["교과목코드"]).strip(),
            "name": str(r["교과목명"]).strip(),
            "hours_per_week": hours,        # A안: 학점=주당시수
            "instructor": str(r["강좌담당교수"]).strip(),
            "requires_lab": requires_lab_flag(r["강의유형구분"]),
            "enrollment": int(pd.to_numeric(r["수강인원"], errors="coerce")) if pd.notna(r["수강인원"]) else 0,
            "priority": 1,
        })
    return pd.DataFrame(rows)

def try_schedule(rooms, courses, start_hour, end_hour, respect_capacity):
    DAYS = ["Mon","Tue","Wed","Thu","Fri"]
    HOURS = [(h, f"{h:02d}:00", f"{(h+1):02d}:00") for h in range(start_hour, end_hour)]
    Slot = namedtuple("Slot", ["day","start","end"])
    GRID = [Slot(d, s, e) for d in DAYS for (_, s, e) in HOURS]

    # build availability
    avail = {(r["room_id"], sl.day, sl.start): True for r in rooms for sl in GRID}
    assigns = []

    # sort courses: priority asc, hours desc, lab first
    courses_sorted = sorted(
        courses,
        key=lambda c: (c["priority"], -c["hours_per_week"], -(1 if c["requires_lab"]=="Y" else 0))
    )

    def room_ok(room, course):
        # 실습 요구 시 lab만
        if course["requires_lab"]=="Y" and str(room["room_type"]).lower()!="lab":
            return False
        if respect_capacity:
            try:
                if int(room.get("capacity", 9999)) < int(course.get("enrollment", 0)):
                    return False
            except Exception:
                pass
        return True

    for c in courses_sorted:
        hours_needed = int(c["hours_per_week"])
        got = 0
        # day-major iteration
        for d in ["Mon","Tue","Wed","Thu","Fri"]:
            if got >= hours_needed:
                break
            for (_, s, e) in HOURS:
                if got >= hours_needed:
                    break
                # search rooms
                for r in rooms:
                    if not room_ok(r, c):
                        continue
                    if avail[(r["room_id"], d, s)]:
                        avail[(r["room_id"], d, s)] = False
                        assigns.append({
                            "course_id": c["course_id"],
                            "name": c["name"],
                            "instructor": c["instructor"],
                            "enrollment": c["enrollment"],
                            "requires_lab": c["requires_lab"],
                            "room_id": r["room_id"],
                            "room_type": r["room_type"],
                            "day": d,
                            "start": s,
                            "end": e,
                            "hours": 1
                        })
                        got += 1
                        break
        if got < hours_needed:
            return None, GRID  # fail

    return assigns, GRID

def export_outputs(assignments, GRID, rooms, anchor_date, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df_sched = pd.DataFrame(assignments).sort_values(["day","start","room_id","name"])
    assigned_path = os.path.join(out_dir, "assigned_schedule.csv")
    df_sched.to_csv(assigned_path, index=False, encoding="utf-8-sig")

    # Vacancies
    room_ids = [r["room_id"] for r in rooms]
    occupied = {(r["room_id"], r["day"], r["start"]) for _, r in df_sched.iterrows()}
    vac_rows = []
    for rid in room_ids:
        for sl in GRID:
            if (rid, sl.day, sl.start) not in occupied:
                vac_rows.append({"room_id": rid, "day": sl.day, "start": sl.start, "end": sl.end})
    vacant_path = os.path.join(out_dir, "vacant_slots.csv")
    pd.DataFrame(vac_rows).to_csv(vacant_path, index=False, encoding="utf-8-sig")

    # Calendar CSV
    dmap = {"Mon":0,"Tue":1,"Wed":2,"Thu":3,"Fri":4}
    cal = []
    for _, r in df_sched.iterrows():
        delta = timedelta(days=dmap[r["day"]])
        sdt = datetime.strptime(r["start"], "%H:%M")
        edt = datetime.strptime(r["end"], "%H:%M")
        start_dt = anchor_date.replace(hour=sdt.hour, minute=sdt.minute) + delta
        end_dt = anchor_date.replace(hour=edt.hour, minute=edt.minute) + delta
        cal.append({
            "Subject": f'{r["name"]} ({r["course_id"]})',
            "Start Date": start_dt.strftime("%Y-%m-%d"),
            "Start Time": start_dt.strftime("%H:%M"),
            "End Date": end_dt.strftime("%Y-%m-%d"),
            "End Time": end_dt.strftime("%H:%M"),
            "All Day Event": "False",
            "Description": f'Instructor: {r["instructor"]}; Enrollment: {r["enrollment"]}; Lab: {r["requires_lab"]}',
            "Location": f'{r["room_id"]} ({r["room_type"]})'
        })
    cal_path = os.path.join(out_dir, "calendar_google_import.csv")
    pd.DataFrame(cal).to_csv(cal_path, index=False, encoding="utf-8-sig")

    # Utilization chart
    total_blocks = len(GRID)
    usage = df_sched.groupby("room_id").size().reindex(room_ids, fill_value=0)
    util_df = pd.DataFrame({"room_id": room_ids, "used_blocks": usage.values})
    util_df["total_blocks"] = total_blocks
    util_df["utilization_rate"] = util_df["used_blocks"] / util_df["total_blocks"]

    plt.figure(figsize=(8,5))
    plt.bar(util_df["room_id"], util_df["utilization_rate"])
    plt.title("Room Utilization Rate (1-hour blocks, Mon-Fri)")
    plt.xlabel("Room")
    plt.ylabel("Utilization")
    plt.ylim(0,1)
    for i, v in enumerate(util_df["utilization_rate"]):
        plt.text(i, v + 0.02, f"{v:.0%}", ha="center")
    plt.tight_layout()
    util_path = os.path.join(out_dir, "utilization.png")
    plt.savefig(util_path)
    plt.close()

    return assigned_path, vacant_path, cal_path, util_path

def main():
    parser = argparse.ArgumentParser(description="Timetable Auto-Assignment (A안: 학점=주당시수)")
    parser.add_argument("--courses", default="courses_data.csv", help="별첨 교과목 CSV (기본: courses_data.csv)")
    parser.add_argument("--rooms", default="rooms.csv", help="강의실 CSV (기본: rooms.csv)")
    parser.add_argument("--department-filter", default=None, help="개설학과에 이 문자열 포함된 행만 사용 (예: 소프트웨어융합)")
    parser.add_argument("--anchor-date", default="2025-11-03", help="구글 캘린더 변환 기준 주 월요일 (YYYY-MM-DD)")
    parser.add_argument("--start-hour", type=int, default=9, help="하루 시작 시간 (기본 9)")
    parser.add_argument("--end-hour", type=int, default=21, help="하루 종료 시간 (기본 21; 자신은 포함 안 됨)")
    parser.add_argument("--respect-capacity", action="store_true", help="rooms.csv capacity를 수강인원과 비교하여 초과 시 배정 금지")
    parser.add_argument("--out-dir", default=".", help="산출물 저장 폴더 (기본: 현재 폴더)")
    args = parser.parse_args()

    # Load data
    df_courses_raw = read_csv_auto(args.courses)
    df_rooms = ensure_rooms_csv(args.rooms)
    if not args.respect_capacity:
        # 무시 모드: 큰 수로 통일
        df_rooms = df_rooms.copy()
        df_rooms["capacity"] = 999999

    # Transform courses
    df_courses = build_courses_frame(df_courses_raw, department_filter=args.department_filter)

    # Dicts
    rooms = df_rooms.to_dict(orient="records")
    courses = df_courses.to_dict(orient="records")

    # First attempt
    assigns, GRID = try_schedule(rooms, courses, args.start_hour, args.end_hour, respect_capacity=args.respect_capacity)

    # Borrowed room once if needed
    used_borrowed = False
    if assigns is None:
        borrowed = {"room_id":"외부대여-타강의실1","room_type":"lecture","capacity":999999}
        rooms2 = rooms + [borrowed]
        assigns, GRID = try_schedule(rooms2, courses, args.start_hour, args.end_hour, respect_capacity=args.respect_capacity)
        used_borrowed = assigns is not None

    if assigns is None:
        print("[ERROR] 배정 실패: 시간 블록/요일을 늘리거나(예: --end-hour 22), 토요일 도입(코드 확장) 또는 과목 범위 축소 필요")
        sys.exit(1)

    # Export
    try:
        anchor = datetime.strptime(args.anchor_date, "%Y-%m-%d")
    except Exception:
        print("[WARN] anchor-date 파싱 실패. 2025-11-03으로 대체")
        anchor = datetime(2025, 11, 3)

    assigned_path, vacant_path, cal_path, util_path = export_outputs(assigns, GRID, rooms + ([{"room_id":"외부대여-타강의실1","room_type":"lecture","capacity":999999}] if used_borrowed else []), anchor, args.out_dir)

    # Console summary
    print("[DONE] 산출물 생성 완료 ↓↓↓")
    print(" - assigned_schedule.csv:", assigned_path)
    print(" - vacant_slots.csv     :", vacant_path)
    print(" - calendar_google_import.csv:", cal_path)
    print(" - utilization.png      :", util_path)
    print(" - borrowed extra room? :", "YES" if used_borrowed else "NO")

if __name__ == "__main__":
    main()
