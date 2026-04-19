"""
ConnectHub - Social Media Platform
Database: SQLite with complete schema and rich seed data
"""
import sqlite3
import os
import bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connecthub.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            username         TEXT UNIQUE NOT NULL,
            email            TEXT UNIQUE NOT NULL,
            password         TEXT NOT NULL,
            bio              TEXT    DEFAULT '',
            avatar           TEXT    DEFAULT '',
            website          TEXT    DEFAULT '',
            location         TEXT    DEFAULT '',
            is_verified      INTEGER DEFAULT 0,
            follower_count   INTEGER DEFAULT 0,
            following_count  INTEGER DEFAULT 0,
            post_count       INTEGER DEFAULT 0,
            created_at       TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS posts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            content       TEXT    NOT NULL,
            image_url     TEXT    DEFAULT '',
            like_count    INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            hashtags      TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id    INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            content    TEXT NOT NULL,
            parent_id  INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS likes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            post_id    INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );

        CREATE TABLE IF NOT EXISTS follows (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id  INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at   TEXT DEFAULT (datetime('now')),
            UNIQUE(follower_id, following_id),
            FOREIGN KEY(follower_id)  REFERENCES users(id),
            FOREIGN KEY(following_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            actor_id   INTEGER NOT NULL,
            type       TEXT NOT NULL,
            post_id    INTEGER DEFAULT NULL,
            message    TEXT NOT NULL,
            is_read    INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id)  REFERENCES users(id),
            FOREIGN KEY(actor_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS saved_posts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );

        CREATE TABLE IF NOT EXISTS hashtags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tag        TEXT UNIQUE NOT NULL,
            post_count INTEGER DEFAULT 0
        );
    """)

    def h(p):
        return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    # ── seed users ──────────────────────────────
    seed_users = [
        ("Admin User",    "admin",       "admin@connecthub.com",  h("Admin@123"), "Platform admin", 1),
        ("Rahul Mehta",   "rahulmehta",  "user@demo.com",         h("Demo@123"),  "Software developer 💻 | Open source enthusiast | Building cool stuff #Python #React", 1),
        ("Priya Sharma",  "priyasharma", "priya@demo.com",        h("Demo@123"),  "UI/UX Designer 🎨 | Travel lover ✈️ | Photographer 📸 | Mumbai", 0),
        ("Amit Verma",    "amitverma",   "amit@demo.com",         h("Demo@123"),  "Entrepreneur | EdTech Startup Founder | Delhi NCR", 0),
        ("Sneha Patel",   "sneha_patel", "sneha@demo.com",        h("Demo@123"),  "Food blogger 🍕 | Home chef | Mumbai foodie | Sharing recipes daily!", 0),
        ("Vikram Singh",  "vikramsingh", "vikram@demo.com",       h("Demo@123"),  "Fitness coach 💪 | Marathon runner 🏃 | Cricket fan 🏏 | Pune", 0),
    ]
    for row in seed_users:
        c.execute("""
            INSERT OR IGNORE INTO users
              (name, username, email, password, bio, is_verified)
            VALUES (?,?,?,?,?,?)
        """, row)
    conn.commit()

    def uid(uname):
        r = c.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
        return r["id"] if r else None

    u1 = uid("rahulmehta")
    u2 = uid("priyasharma")
    u3 = uid("amitverma")
    u4 = uid("sneha_patel")
    u5 = uid("vikramsingh")

    if not u1:
        conn.close()
        print("✅ ConnectHub DB ready")
        return

    # ── seed posts ──────────────────────────────
    posts_data = [
        (u1,
         "Just shipped my first open-source Python library! 🚀 It auto-generates REST API docs from your Flask routes. 200+ GitHub stars in 24 hours!\n\n#OpenSource #Python #Flask #Developer #GitHub",
         "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=700&q=80"),
        (u2,
         "Weekend escape to Manali ❄️ The mountains never disappoint. Woke up at 5am for this golden-hour shot — every bit of the early rise was worth it!\n\n#Travel #Manali #Mountains #GoldenHour #Photography",
         "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=700&q=80"),
        (u3,
         "Thrilled to announce: our EdTech startup just closed a ₹2 Crore seed round! 🎉 We're building adaptive AI-based learning for Tier-2 India. Big things ahead!\n\n#Startup #EdTech #Funding #India #AI",
         ""),
        (u4,
         "Tried making restaurant-style butter chicken at home tonight 🍗 The secret? Slow-cook the onion-tomato base for at least 45 minutes. Game changer!\n\n#Cooking #ButterChicken #FoodBlogger #Recipe #Homemade",
         "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=700&q=80"),
        (u5,
         "Morning done ✅ 5km run + 100 pushups + 50 pull-ups before 7am. Reminder: you don't need motivation, you need discipline. Show up every single day!\n\n#Fitness #MorningRoutine #Discipline #Motivation #HealthyLife",
         "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=700&q=80"),
        (u1,
         "Unpopular opinion: mastering one language deeply beats knowing 10 languages poorly. I spent 3 years going deep on Python and it unlocked everything else.\n\nWhat's your take? 👇\n\n#Programming #Python #SoftwareEngineering #100DaysOfCode",
         ""),
        (u2,
         "Captured this street portrait in Jaipur's old city 📸 Sometimes the best shots come from simply walking slowly and being present.\n\n#Photography #Jaipur #Portrait #StreetPhotography #India",
         "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=700&q=80"),
        (u3,
         "3 books that rewired how I think about business:\n\n📖 Zero to One – Peter Thiel\n📖 The Lean Startup – Eric Ries\n📖 Good to Great – Jim Collins\n\nDrop your must-reads below 👇\n\n#Books #Reading #Startup #Entrepreneurship",
         ""),
        (u4,
         "Mumbai street food walking tour 🌮 Vada Pav → Pani Puri → Bhel Puri → Dahi Sev Puri. All under ₹150 and absolutely unbeatable flavour.\n\n#MumbaiFoodScene #StreetFood #Foodie #MumbaiDiaries",
         "https://images.unsplash.com/photo-1567521464027-f127ff144326?w=700&q=80"),
        (u5,
         "Crossed the finish line of my first full marathon today! 🏅 42.2km in 4:08:33. Six months of 5am training runs. Every painful early morning was worth it!\n\n#Marathon #Running #Achievement #NeverGiveUp #PuneMarathon",
         "https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?w=700&q=80"),
        (u1,
         "Just deployed to production using Docker + GitHub Actions CI/CD. Zero-downtime blue-green deployment on AWS. The pipeline took 2 days to set up but now pushes are anxiety-free 😌\n\n#DevOps #Docker #AWS #CI_CD #Engineering",
         ""),
        (u2,
         "New portfolio piece: redesigned the onboarding flow for a fintech app. Cut drop-off rate by 38% by reducing steps from 7 to 3. Good UX = good business.\n\n#UXDesign #Fintech #ProductDesign #CaseStudy #UI",
         "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=700&q=80"),
    ]
    for p in posts_data:
        c.execute(
            "INSERT OR IGNORE INTO posts (user_id, content, image_url) VALUES (?,?,?)",
            p
        )
    conn.commit()

    # Update hashtags table
    import re
    post_rows = c.execute("SELECT content FROM posts").fetchall()
    for pr in post_rows:
        tags = re.findall(r"#(\w+)", pr["content"])
        for tag in set(tags):
            c.execute("INSERT OR IGNORE INTO hashtags(tag, post_count) VALUES(?,0)", (tag,))
            c.execute("UPDATE hashtags SET post_count = post_count+1 WHERE tag=?", (tag,))
    conn.commit()

    post_ids = [r["id"] for r in c.execute("SELECT id FROM posts ORDER BY id").fetchall()]

    # ── seed likes ──────────────────────────────
    likes = [
        (u2, post_ids[0]), (u3, post_ids[0]), (u4, post_ids[0]), (u5, post_ids[0]),
        (u1, post_ids[1]), (u3, post_ids[1]), (u5, post_ids[1]),
        (u1, post_ids[2]), (u2, post_ids[2]), (u4, post_ids[2]), (u5, post_ids[2]),
        (u1, post_ids[3]), (u2, post_ids[3]), (u3, post_ids[3]),
        (u1, post_ids[4]), (u2, post_ids[4]), (u3, post_ids[4]), (u4, post_ids[4]),
        (u2, post_ids[5]), (u3, post_ids[5]), (u4, post_ids[5]),
        (u1, post_ids[6]), (u3, post_ids[6]), (u4, post_ids[6]),
        (u1, post_ids[7]), (u2, post_ids[7]), (u4, post_ids[7]), (u5, post_ids[7]),
        (u1, post_ids[8]), (u2, post_ids[8]), (u5, post_ids[8]),
        (u1, post_ids[9]), (u2, post_ids[9]), (u3, post_ids[9]), (u4, post_ids[9]),
    ]
    for lk in likes:
        c.execute("INSERT OR IGNORE INTO likes(user_id, post_id) VALUES(?,?)", lk)
    conn.commit()

    # ── seed follows ────────────────────────────
    follow_pairs = [
        (u1, u2), (u1, u3), (u1, u4), (u1, u5),
        (u2, u1), (u2, u3), (u2, u5),
        (u3, u1), (u3, u2), (u3, u4),
        (u4, u1), (u4, u2), (u4, u5),
        (u5, u1), (u5, u2), (u5, u3),
    ]
    for fp in follow_pairs:
        c.execute("INSERT OR IGNORE INTO follows(follower_id, following_id) VALUES(?,?)", fp)
    conn.commit()

    # ── seed comments ───────────────────────────
    comments = [
        (post_ids[0],  u2, "This is exactly what I needed! What's the GitHub link? Would love to contribute 🙌"),
        (post_ids[0],  u3, "200 stars in 24 hours is incredible. Open source is the best path to visibility!"),
        (post_ids[1],  u1, "This photo is absolutely stunning 😍 Manali is on my bucket list now!"),
        (post_ids[1],  u4, "The mountains look magical. Did you try the local momos? Best I've ever had!"),
        (post_ids[2],  u1, "Massive congratulations Amit! 🎊 The EdTech space needs more mission-driven founders."),
        (post_ids[2],  u2, "Inspiring! Would love to learn more about your product roadmap."),
        (post_ids[3],  u1, "This looks incredible! Saving this recipe for the weekend 🍗"),
        (post_ids[4],  u1, "Goals!! 💪 What's your training plan? Do you follow a specific programme?"),
        (post_ids[4],  u2, "The discipline mindset over motivation is everything. Sharing this!"),
        (post_ids[5],  u2, "100% agree. I went deep on JavaScript for 2 years before touching TypeScript. No regrets."),
        (post_ids[5],  u3, "Solid take. Though I'd add — breadth matters once you've hit depth in one language."),
        (post_ids[7],  u1, "Adding Zero to One to my reading list right now. Great picks all around!"),
        (post_ids[9],  u1, "CONGRATULATIONS 🎉 Six months of 5am runs deserve every bit of that medal!"),
        (post_ids[9],  u2, "This made me emotional. So proud of you! Sub-4 next, let's go!"),
    ]
    for cm in comments:
        c.execute("INSERT OR IGNORE INTO comments(post_id, user_id, content) VALUES(?,?,?)", cm)
    conn.commit()

    # ── seed notifications ──────────────────────
    notifs = [
        (u1, u2, "like",    post_ids[0], "Priya Sharma liked your post"),
        (u1, u3, "like",    post_ids[0], "Amit Verma liked your post"),
        (u1, u2, "comment", post_ids[0], "Priya Sharma commented: 'This is exactly what I needed!'"),
        (u1, u2, "follow",  None,        "Priya Sharma started following you"),
        (u2, u1, "like",    post_ids[1], "Rahul Mehta liked your photo"),
        (u2, u1, "follow",  None,        "Rahul Mehta started following you"),
        (u3, u1, "like",    post_ids[2], "Rahul Mehta liked your post"),
        (u3, u1, "comment", post_ids[2], "Rahul Mehta commented: 'Massive congratulations!'"),
    ]
    for n in notifs:
        c.execute("""
            INSERT OR IGNORE INTO notifications
              (user_id, actor_id, type, post_id, message)
            VALUES (?,?,?,?,?)
        """, n)
    conn.commit()

    # ── seed saved posts ────────────────────────
    saves = [(u1, post_ids[1]), (u1, post_ids[3]), (u2, post_ids[0]), (u2, post_ids[4])]
    for sv in saves:
        c.execute("INSERT OR IGNORE INTO saved_posts(user_id, post_id) VALUES(?,?)", sv)
    conn.commit()

    # ── update all aggregate counts ─────────────
    c.executescript("""
        UPDATE posts SET like_count    = (SELECT COUNT(*) FROM likes    WHERE post_id = posts.id);
        UPDATE posts SET comment_count = (SELECT COUNT(*) FROM comments WHERE post_id = posts.id);
        UPDATE users SET post_count      = (SELECT COUNT(*) FROM posts   WHERE user_id   = users.id);
        UPDATE users SET follower_count  = (SELECT COUNT(*) FROM follows WHERE following_id = users.id);
        UPDATE users SET following_count = (SELECT COUNT(*) FROM follows WHERE follower_id  = users.id);
    """)
    conn.commit()
    conn.close()
    print("✅ ConnectHub DB ready")


if __name__ == "__main__":
    init_db()
    print("DB path:", DB_PATH)
