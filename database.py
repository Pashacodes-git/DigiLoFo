import datetime
import hashlib
import hmac
import os
import random
import secrets
import sqlite3

# Resolve database path relative to this script directory so running from any CWD works safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, "digilofo.db")


def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    # Enable SQLite foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            date_lost_found TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_data BLOB
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            claimant_name TEXT NOT NULL,
            claimant_contact TEXT NOT NULL,
            claim_reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            pickup_pin TEXT,
            claimant_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Safe column migrations for claims table
    cursor.execute("PRAGMA table_info(claims)")
    cols = [col[1] for col in cursor.fetchall()]
    if "pickup_pin" not in cols:
        cursor.execute("ALTER TABLE claims ADD COLUMN pickup_pin TEXT")
    if "claimant_email" not in cols:
        cursor.execute("ALTER TABLE claims ADD COLUMN claimant_email TEXT")

    # Safe column migration for items table
    cursor.execute("PRAGMA table_info(items)")
    item_cols = [col[1] for col in cursor.fetchall()]
    if "image_data" not in item_cols:
        cursor.execute("ALTER TABLE items ADD COLUMN image_data BLOB")

    connection.commit()
    connection.close()


def create_student_session(user_id):
    """
    Creates a random session token for a student, valid for 7 days.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM student_sessions WHERE user_id = ?", (user_id,))
    cursor.execute(
        "INSERT INTO student_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat())
    )

    connection.commit()
    connection.close()
    return token


def verify_student_session(token):
    """
    Verifies a session token. Returns student user dict if valid and unexpired.
    Admin accounts are never authenticated via session tokens.
    """
    if not token or not isinstance(token, str):
        return None

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT users.id, users.name, users.email, users.role, student_sessions.expires_at
        FROM student_sessions
        JOIN users ON student_sessions.user_id = users.id
        WHERE student_sessions.token = ?
    """, (token,))

    row = cursor.fetchone()
    if not row:
        connection.close()
        return None

    user_id, name, email, role, expires_at_str = row

    if role != "student":
        cursor.execute("DELETE FROM student_sessions WHERE token = ?", (token,))
        connection.commit()
        connection.close()
        return None

    try:
        expires_at = datetime.datetime.fromisoformat(expires_at_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > expires_at:
            cursor.execute("DELETE FROM student_sessions WHERE token = ?", (token,))
            connection.commit()
            connection.close()
            return None
    except Exception:
        connection.close()
        return None

    connection.close()
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": "student"
    }


def delete_student_session(token):
    """
    Invalidates a student session token upon logout.
    """
    if not token:
        return
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM student_sessions WHERE token = ?", (token,))
    connection.commit()
    connection.close()


def add_item(
    report_type,
    title,
    category,
    description,
    location,
    date_lost_found,
    image_data=None
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO items (
            report_type,
            title,
            category,
            description,
            location,
            date_lost_found,
            image_data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        report_type,
        title,
        category,
        description,
        location,
        date_lost_found,
        image_data
    ))

    new_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return new_id


def get_items():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            report_type,
            title,
            category,
            description,
            location,
            date_lost_found,
            status,
            created_at,
            image_data
        FROM items
        ORDER BY created_at DESC
    """)

    items = cursor.fetchall()
    connection.close()
    return items


def get_open_found_items():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            report_type,
            title,
            category,
            description,
            location,
            date_lost_found,
            status,
            created_at,
            image_data
        FROM items
        WHERE report_type = 'FOUND' AND status = 'Open'
        ORDER BY created_at DESC
    """)

    items = cursor.fetchall()
    connection.close()
    return items


def get_dashboard_stats():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM items")
    total_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items WHERE status = 'Open'")
    open_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items WHERE report_type = 'LOST' AND status = 'Open'")
    lost_items = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items WHERE report_type = 'FOUND' AND status = 'Open'")
    found_items = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items WHERE status = 'Recovered'")
    recovered_items = cursor.fetchone()[0]

    connection.close()

    recovery_rate = int((recovered_items / total_reports * 100)) if total_reports > 0 else 0

    return {
        "total": total_reports,
        "open": open_reports,
        "lost": lost_items,
        "found": found_items,
        "recovered": recovered_items,
        "recovery_rate": recovery_rate
    }


def get_campus_hotspots():
    """
    Returns counts of reports aggregated by campus location and category.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT location, COUNT(*) as count
        FROM items
        GROUP BY location
        ORDER BY count DESC
        LIMIT 6
    """)
    locations = cursor.fetchall()

    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM items
        GROUP BY category
        ORDER BY count DESC
    """)
    categories = cursor.fetchall()

    connection.close()
    return {
        "locations": locations,
        "categories": categories
    }


def update_item_status(item_id, new_status, current_user_role=None):
    """
    Updates the status of an item.
    Enforces authorization check: caller must have 'admin' role.
    """
    if current_user_role != "admin":
        raise PermissionError("Unauthorized: Only administrators can update item status.")

    if new_status not in ("Open", "Recovered"):
        raise ValueError(f"Invalid item status: {new_status}")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE items
        SET status = ?
        WHERE id = ?
    """, (new_status, item_id))

    connection.commit()
    connection.close()


def add_claim(item_id, claimant_name, claimant_contact, claim_reason, claimant_email=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO claims (
            item_id,
            claimant_name,
            claimant_contact,
            claim_reason,
            claimant_email
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        item_id,
        claimant_name,
        claimant_contact,
        claim_reason,
        claimant_email
    ))

    connection.commit()
    connection.close()


def get_claims(current_user_role=None):
    """
    Fetches all claims with associated item titles.
    Enforces authorization check: caller must have 'admin' role.
    """
    if current_user_role != "admin":
        raise PermissionError("Unauthorized: Only administrators can view claim details.")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            claims.id,
            claims.item_id,
            items.title,
            claims.claimant_name,
            claims.claimant_contact,
            claims.claim_reason,
            claims.status,
            claims.pickup_pin,
            claims.claimant_email,
            claims.created_at
        FROM claims
        JOIN items ON claims.item_id = items.id
        ORDER BY claims.created_at DESC
    """)

    claims = cursor.fetchall()
    connection.close()
    return claims


def get_user_claims(user_email):
    """
    Fetches claims submitted by a specific student so they can track their own status & PIN.
    """
    if not user_email:
        return []

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            claims.id,
            claims.item_id,
            items.title,
            items.location,
            claims.status,
            claims.pickup_pin,
            claims.created_at
        FROM claims
        JOIN items ON claims.item_id = items.id
        WHERE claims.claimant_email = ?
        ORDER BY claims.created_at DESC
    """, (user_email.strip().lower(),))

    user_claims = cursor.fetchall()
    connection.close()
    return user_claims


def update_claim_status(claim_id, new_status, current_user_role=None):
    """
    Updates claim status (Approved / Rejected).
    Generates a secure 4-digit pickup PIN when Approved.
    Enforces authorization check: caller must have 'admin' role.
    """
    if current_user_role != "admin":
        raise PermissionError("Unauthorized: Only administrators can update claim status.")

    if new_status not in ("Approved", "Rejected", "Pending", "Handed Over"):
        raise ValueError(f"Invalid claim status: {new_status}")

    pickup_pin = None
    if new_status == "Approved":
        # Generate 4-digit secure physical recovery PIN
        pickup_pin = f"{random.randint(1000, 9999)}"

    connection = get_connection()
    cursor = connection.cursor()

    if pickup_pin:
        cursor.execute("""
            UPDATE claims
            SET status = ?, pickup_pin = ?
            WHERE id = ?
        """, (new_status, pickup_pin, claim_id))
    else:
        cursor.execute("""
            UPDATE claims
            SET status = ?
            WHERE id = ?
        """, (new_status, claim_id))

    connection.commit()
    connection.close()
    return pickup_pin


def verify_and_handover_item(claim_id, entered_pin, current_user_role=None):
    """
    Admin verifies the student's physical pickup PIN at the campus custody hub
    and formally marks both the claim and item as 'Handed Over' / 'Recovered'.
    """
    if current_user_role != "admin":
        raise PermissionError("Unauthorized: Only administrators can execute physical handover.")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT item_id, pickup_pin, status FROM claims WHERE id = ?", (claim_id,))
    row = cursor.fetchone()

    if not row:
        connection.close()
        return False, "Claim record not found."

    item_id, correct_pin, status = row

    if status != "Approved":
        connection.close()
        return False, "Only Approved claims awaiting physical handover can be verified."

    if not hmac.compare_digest(str(correct_pin).strip(), str(entered_pin).strip()):
        connection.close()
        return False, "Incorrect Pickup PIN. Please verify the code on student's screen."

    # Valid PIN -> Finalize Handover
    cursor.execute("UPDATE claims SET status = 'Handed Over' WHERE id = ?", (claim_id,))
    cursor.execute("UPDATE items SET status = 'Recovered' WHERE id = ?", (item_id,))
    connection.commit()
    connection.close()
    return True, "PIN verified! Physical handover completed successfully. Item marked Recovered."


def hash_password(password):
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        600000
    ).hex()

    return f"pbkdf2_sha256$600000${salt}${password_hash}"
def find_possible_matches(item_id=None):
    """
    Compares open LOST and FOUND reports using rule-based scoring.
    Optionally filters matches related to a specific item_id.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            lost.id,
            lost.title,
            lost.category,
            lost.description,
            lost.location,
            lost.date_lost_found,
            found.id,
            found.title,
            found.category,
            found.description,
            found.location,
            found.date_lost_found,
            lost.image_data,
            found.image_data
        FROM items AS lost
        CROSS JOIN items AS found
        WHERE lost.report_type = 'LOST'
          AND found.report_type = 'FOUND'
          AND lost.status = 'Open'
          AND found.status = 'Open'
    """)

    reports = cursor.fetchall()
    connection.close()

    matches = []

    for report in reports:
        lost_id, lost_title, lost_category, lost_desc, lost_loc, lost_date = report[:6]
        found_id, found_title, found_category, found_desc, found_loc, found_date = report[6:12]
        lost_image = report[12] if len(report) > 12 else None
        found_image = report[13] if len(report) > 13 else None

        if item_id is not None and lost_id != item_id and found_id != item_id:
            continue

        score = 0

        # Factor 1: Category matching (+2 pts)
        if lost_category == found_category:
            score += 2

        # Factor 2: Common descriptive keywords (+1 pt each, max 5 pts)
        lost_words = set((lost_title + " " + lost_desc).lower().split())
        found_words = set((found_title + " " + found_desc).lower().split())

        common_words = lost_words & found_words
        stop_words = {
            "a", "an", "the", "and", "or", "of", "with", "my", "is", "in",
            "at", "to", "for", "on", "it", "this", "that", "near", "by"
        }
        common_words -= stop_words

        score += min(len(common_words), 5)

        # Factor 3: Location matching (+2 pts)
        cleaned_lost_loc = lost_loc.strip().lower()
        cleaned_found_loc = found_loc.strip().lower()
        if (
            cleaned_lost_loc
            and cleaned_found_loc
            and (cleaned_lost_loc in cleaned_found_loc or cleaned_found_loc in cleaned_lost_loc)
        ):
            score += 2

        # Minimum matching threshold: 3 points
        if score >= 3:
            matches.append({
                "lost_id": lost_id,
                "lost_title": lost_title,
                "lost_location": lost_loc,
                "lost_category": lost_category,
                "lost_image": lost_image,
                "found_id": found_id,
                "found_title": found_title,
                "found_location": found_loc,
                "found_category": found_category,
                "found_image": found_image,
                "score": score
            })

    matches.sort(key=lambda match: match["score"], reverse=True)
    return matches




def register_student(name, email, password):
    email = email.strip().lower()

    if not email.endswith("@woxsen.edu.in"):
        return False, "Only Woxsen University email addresses are allowed (@woxsen.edu.in)."

    password_hash = hash_password(password)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'student')
        """, (name, email, password_hash))

        connection.commit()
        return True, "Registration successful."

    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

    finally:
        connection.close()


def verify_login(email, password):
    email = email.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id, name, email, password, role FROM users WHERE email = ?",
            (email,)
        )
        user = cursor.fetchone()

        if user is None:
            return None

        user_id, name, stored_email, stored_password, role = user

        if stored_password.startswith("pbkdf2_sha256$"):
            try:
                algorithm, iterations, salt, expected_hash = stored_password.split("$")

                actual_hash = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt.encode("utf-8"),
                    int(iterations)
                ).hex()

                valid = hmac.compare_digest(actual_hash, expected_hash)
            except (ValueError, TypeError):
                valid = False
        else:
            if len(stored_password) == 64:
                legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                valid = hmac.compare_digest(legacy_hash, stored_password)
            else:
                valid = hmac.compare_digest(password, stored_password)

            if valid:
                cursor.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (hash_password(password), user_id)
                )
                connection.commit()

        if not valid:
            return None

        return {
            "id": user_id,
            "name": name,
            "email": stored_email,
            "role": role
        }

    finally:
        connection.close()


def create_admin(name, email, password):
    email = email.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE role = 'admin'")
        if cursor.fetchone():
            return False, "An admin account already exists."

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return False, "This email is already registered."

        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'admin')
        """, (name, email, hash_password(password)))

        connection.commit()
        return True, "Admin account created successfully."

    finally:
        connection.close()
