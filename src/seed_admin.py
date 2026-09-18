from auth import create_user, user_exists

# ---- CHANGE THESE BEFORE RUNNING ----
ADMIN_NAME = "Muhammad Jasim"
ADMIN_EMAIL = "admin@schoolpulse.test"
ADMIN_PASSWORD = "admin123"   # change after first login
# -------------------------------------

if __name__ == "__main__":
    if user_exists(ADMIN_EMAIL):
        print(f"User {ADMIN_EMAIL} already exists. Skipping.")
    else:
        create_user(ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, role="admin")
        print(f"Created admin user: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
        print("Change this password after first login.")