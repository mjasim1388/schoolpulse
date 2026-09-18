from fees import (
    current_month_str,
    month_summary,
    get_defaulters,
    record_payment,
    get_payments_for_month,
    recent_months,
    payments_by_month,
)
from students import get_all_students

if __name__ == "__main__":
    month = current_month_str()
    print(f"Current month: {month}\n")

    print("Summary BEFORE any payment:")
    s = month_summary(month)
    for k, v in s.items():
        print(f"  {k}: {v}")

    print(f"\nDefaulters for {month}: {len(get_defaulters(month))}")

    # Pay for the first 2 students
    students = get_all_students()
    if len(students) >= 2:
        for st in students[:2]:
            if not record_payment(st["id"], st["monthly_fee"], month, method="cash"):
                print(f"Failed to record for {st['full_name']}")
        print(f"\nRecorded payments for {students[0]['full_name']} and {students[1]['full_name']}")

    print("\nSummary AFTER payments:")
    s = month_summary(month)
    for k, v in s.items():
        print(f"  {k}: {v}")

    print(f"\nPayments this month: {len(get_payments_for_month(month))}")
    print(f"Defaulters now: {len(get_defaulters(month))}")

    print("\nLast 6 months collection:")
    for row in payments_by_month(recent_months(6)):
        print(f"  {row['month']}: Rs {row['collected']:,.0f}")