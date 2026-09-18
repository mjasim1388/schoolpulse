from students import add_student, get_all_students, count_students, get_classes

# Add a few sample students to test
SAMPLE = [
    ("Ahmed Khan",   "101", "Class 5",  "A", "Muhammad Khan", "0300-1111111", 2500),
    ("Fatima Ali",   "102", "Class 5",  "A", "Ali Akbar",     "0300-2222222", 2500),
    ("Bilal Hussain","103", "Class 5",  "A", "Hussain Ahmed", "0300-3333333", 2500),
    ("Ayesha Malik", "201", "Class 6",  "B", "Malik Rasheed", "0300-4444444", 3000),
    ("Hassan Raza",  "202", "Class 6",  "B", "Raza Ahmed",    "0300-5555555", 3000),
]

if __name__ == "__main__":
    print("Adding sample students...")
    existing = {s["full_name"] for s in get_all_students()}
    for name, roll, cls, sec, parent, phone, fee in SAMPLE:
        if name in existing:
            print(f"  Skipping {name} (already exists)")
            continue
        add_student(name, roll, cls, sec, parent, phone, fee)
        print(f"  Added {name}")

    print(f"\nTotal active students: {count_students()}")
    print(f"Classes in use: {get_classes()}")
    print("\nAll students:")
    for s in get_all_students():
        print(f"  {s['id']:>3} | {s['full_name']:<18} | {s['class_name']} {s['section']} | Rs {s['monthly_fee']}")