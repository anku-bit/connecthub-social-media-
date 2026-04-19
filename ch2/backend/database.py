"""ConnectHub - Social Media Platform - Database Layer"""
import sqlite3, os, bcrypt, re

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connecthub.db")

def get_db():
    conn = sqlite3.connect(DB)
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
            name             TEXT    NOT NULL,
            username         TEXT    UNIQUE NOT NULL,
            email            TEXT    UNIQUE NOT NULL,
            password         TEXT    NOT NULL,
            bio              TEXT    DEFAULT '',
            location         TEXT    DEFAULT '',
            website          TEXT    DEFAULT '',
            is_verified      INTEGER DEFAULT 0,
            follower_count   INTEGER DEFAULT 0,
            following_count  INTEGER DEFAULT 0,
            post_count       INTEGER DEFAULT 0,
            created_at       TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS posts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id),
            content       TEXT    NOT NULL,
            image_url     TEXT    DEFAULT '',
            like_count    INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            hashtags      TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id    INTEGER NOT NULL REFERENCES posts(id),
            user_id    INTEGER NOT NULL REFERENCES users(id),
            content    TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS likes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            post_id    INTEGER NOT NULL REFERENCES posts(id),
            UNIQUE(user_id, post_id)
        );

        CREATE TABLE IF NOT EXISTS follows (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id  INTEGER NOT NULL REFERENCES users(id),
            following_id INTEGER NOT NULL REFERENCES users(id),
            created_at   TEXT    DEFAULT (datetime('now')),
            UNIQUE(follower_id, following_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            actor_id   INTEGER NOT NULL REFERENCES users(id),
            type       TEXT    NOT NULL,
            post_id    INTEGER DEFAULT NULL,
            message    TEXT    NOT NULL,
            is_read    INTEGER DEFAULT 0,
            created_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS saved_posts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            post_id INTEGER NOT NULL REFERENCES posts(id),
            UNIQUE(user_id, post_id)
        );

        CREATE TABLE IF NOT EXISTS hashtags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tag        TEXT UNIQUE NOT NULL,
            post_count INTEGER DEFAULT 0
        );
    """)

    def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    seed_users = [
        ("Rahul Mehta",   "rahulmehta",  "user@demo.com",   hp("Demo@123"), "Software developer 💻 | Open source enthusiast | Building cool stuff", "Bangalore", 1),
        ("Priya Sharma",  "priyasharma", "priya@demo.com",  hp("Demo@123"), "UI/UX Designer 🎨 | Travel lover ✈️ | Photographer 📸", "Mumbai", 0),
        ("Amit Verma",    "amitverma",   "amit@demo.com",   hp("Demo@123"), "Entrepreneur | EdTech Startup Founder", "Delhi", 0),
        ("Sneha Patel",   "sneha_patel", "sneha@demo.com",  hp("Demo@123"), "Food blogger 🍕 | Home chef | Mumbai foodie", "Mumbai", 0),
        ("Vikram Singh",  "vikramsingh", "vikram@demo.com", hp("Demo@123"), "Fitness coach 💪 | Marathon runner 🏃 | Cricket fan 🏏", "Pune", 0),
        ("Admin User",    "admin",       "admin@connecthub.com", hp("Admin@123"), "Platform administrator", "", 1),
    ]
    for name, username, email, pwd, bio, loc, verified in seed_users:
        c.execute("INSERT OR IGNORE INTO users(name,username,email,password,bio,location,is_verified) VALUES(?,?,?,?,?,?,?)",
                  (name, username, email, pwd, bio, loc, verified))
    conn.commit()

    def uid(uname):
        r = c.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
        return r["id"] if r else None

    u1=uid("rahulmehta"); u2=uid("priyasharma"); u3=uid("amitverma")
    u4=uid("sneha_patel"); u5=uid("vikramsingh")
    if not u1: conn.close(); print("✅ ConnectHub DB ready"); return

    posts_data = [
        (u1, "Just shipped my first open-source Python library! 🚀 It auto-generates REST API docs from Flask routes. 200+ GitHub stars in 24 hours!\n\n#OpenSource #Python #Flask #Developer",
              "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=700&q=80"),
        (u2, "Weekend escape to Manali ❄️ Woke up at 5am for this golden-hour shot — every bit of the early rise was worth it!\n\n#Travel #Manali #Mountains #Photography",
              "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=700&q=80"),
        (u3, "Thrilled to announce our EdTech startup just closed a ₹2 Crore seed round! 🎉 Building adaptive AI-based learning for Tier-2 India.\n\n#Startup #EdTech #Funding #India",
              ""),
        (u4, "Tried restaurant-style butter chicken at home 🍗 The secret? Slow-cook the onion-tomato base for 45 minutes. Total game changer!\n\n#Cooking #Recipe #Foodie #Homemade",
              "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=700&q=80"),
        (u5, "5km run + 100 pushups + 50 pull-ups before 7am ✅ You don't need motivation, you need discipline. Show up every single day!\n\n#Fitness #Discipline #MorningRoutine",
              "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=700&q=80"),
        (u1, "Unpopular opinion: mastering one language deeply beats knowing 10 poorly. Spent 3 years going deep on Python — it unlocked everything else.\n\n#Programming #Python #DevTips",
              ""),
        (u2, "New portfolio piece: redesigned a fintech app onboarding flow. Cut drop-off rate by 38% by reducing steps from 7 to 3.\n\n#UXDesign #Fintech #ProductDesign #CaseStudy",
              "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=700&q=80"),
        (u3, "3 books that rewired how I think about business:\n📖 Zero to One\n📖 The Lean Startup\n📖 Good to Great\n\nDrop your must-reads below! 👇\n\n#Books #Startup #Entrepreneurship",
              ""),
        (u4, "Mumbai street food tour 🌮 Vada Pav → Pani Puri → Bhel Puri. All under ₹150 and absolutely unbeatable!\n\n#MumbaiFoodScene #StreetFood #Foodie",
              "https://images.unsplash.com/photo-1567521464027-f127ff144326?w=700&q=80"),
        (u5, "Finished my first full marathon! 🏅 42.2km in 4:08:33. Six months of 5am training runs. Every painful morning was worth it!\n\n#Marathon #Running #Achievement",
              "https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?w=700&q=80"),
        (u1, "Just deployed with Docker + GitHub Actions CI/CD. Zero-downtime blue-green deployment on AWS. 2 days to set up but pushes are anxiety-free now 😌\n\n#DevOps #Docker #AWS #CICD",
              ""),
        (u2, "Golden hour photography is absolutely magical ✨ This shot took 2 hours of waiting for the perfect light. Patience always pays!\n\n#Photography #GoldenHour #Nature",
              "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=700&q=80"),
    ]
    for uid_v, content, img in posts_data:
        c.execute("INSERT OR IGNORE INTO posts(user_id,content,image_url) VALUES(?,?,?)", (uid_v, content, img))
    conn.commit()

    # Seed hashtags from posts
    all_posts = c.execute("SELECT content FROM posts").fetchall()
    for p in all_posts:
        for tag in set(re.findall(r"#(\w+)", p["content"])):
            c.execute("INSERT OR IGNORE INTO hashtags(tag,post_count) VALUES(?,0)", (tag,))
            c.execute("UPDATE hashtags SET post_count=post_count+1 WHERE tag=?", (tag,))
    conn.commit()

    post_ids = [r["id"] for r in c.execute("SELECT id FROM posts ORDER BY id").fetchall()]

    # Seed likes
    like_pairs = [
        (u2,post_ids[0]),(u3,post_ids[0]),(u4,post_ids[0]),(u5,post_ids[0]),
        (u1,post_ids[1]),(u3,post_ids[1]),(u5,post_ids[1]),
        (u1,post_ids[2]),(u2,post_ids[2]),(u4,post_ids[2]),
        (u1,post_ids[3]),(u2,post_ids[3]),(u3,post_ids[3]),
        (u1,post_ids[4]),(u2,post_ids[4]),(u3,post_ids[4]),(u4,post_ids[4]),
        (u2,post_ids[5]),(u3,post_ids[5]),(u5,post_ids[5]),
        (u1,post_ids[6]),(u3,post_ids[6]),(u4,post_ids[6]),
        (u1,post_ids[7]),(u2,post_ids[7]),(u4,post_ids[7]),(u5,post_ids[7]),
        (u1,post_ids[8]),(u2,post_ids[8]),(u5,post_ids[8]),
        (u1,post_ids[9]),(u2,post_ids[9]),(u3,post_ids[9]),(u4,post_ids[9]),
    ]
    for luid, lpid in like_pairs:
        c.execute("INSERT OR IGNORE INTO likes(user_id,post_id) VALUES(?,?)", (luid, lpid))
    conn.commit()

    # Seed follows
    for fp in [(u1,u2),(u1,u3),(u1,u4),(u1,u5),
               (u2,u1),(u2,u3),(u2,u5),
               (u3,u1),(u3,u2),(u3,u4),
               (u4,u1),(u4,u2),(u4,u5),
               (u5,u1),(u5,u2),(u5,u3)]:
        c.execute("INSERT OR IGNORE INTO follows(follower_id,following_id) VALUES(?,?)", fp)
    conn.commit()

    # Seed comments
    for cm in [
        (post_ids[0], u2, "This is exactly what I needed! What's the GitHub link? 🙌"),
        (post_ids[0], u3, "200 stars in 24 hours is incredible. Open source is the best path!"),
        (post_ids[1], u1, "Absolutely stunning 😍 Manali is on my bucket list now!"),
        (post_ids[1], u4, "The mountains look magical. Did you try the local momos?"),
        (post_ids[2], u1, "Massive congratulations Amit! 🎊 The EdTech space needs more mission-driven founders."),
        (post_ids[4], u1, "Goals!! 💪 What's your training plan?"),
        (post_ids[4], u2, "The discipline mindset over motivation is everything!"),
        (post_ids[5], u2, "100% agree. I went deep on JavaScript for 2 years — no regrets."),
        (post_ids[7], u1, "Adding Zero to One to my list right now. Great picks!"),
        (post_ids[9], u1, "CONGRATULATIONS 🎉 Sub-4 hours next!"),
        (post_ids[9], u2, "This made me emotional. So proud of you!"),
    ]:
        c.execute("INSERT OR IGNORE INTO comments(post_id,user_id,content) VALUES(?,?,?)", cm)
    conn.commit()

    # Seed saved posts
    for sv in [(u1,post_ids[1]),(u1,post_ids[3]),(u2,post_ids[0]),(u2,post_ids[4])]:
        c.execute("INSERT OR IGNORE INTO saved_posts(user_id,post_id) VALUES(?,?)", sv)
    conn.commit()

    # Seed notifications
    for n in [
        (u1,u2,"like",   post_ids[0],"Priya Sharma liked your post"),
        (u1,u3,"like",   post_ids[0],"Amit Verma liked your post"),
        (u1,u2,"comment",post_ids[0],"Priya Sharma commented on your post"),
        (u1,u2,"follow", None,       "Priya Sharma started following you"),
        (u2,u1,"like",   post_ids[1],"Rahul Mehta liked your photo"),
        (u2,u1,"follow", None,       "Rahul Mehta started following you"),
    ]:
        c.execute("INSERT OR IGNORE INTO notifications(user_id,actor_id,type,post_id,message) VALUES(?,?,?,?,?)", n)
    conn.commit()

    # Update all aggregate counts
    c.executescript("""
        UPDATE posts SET like_count    = (SELECT COUNT(*) FROM likes    WHERE post_id=posts.id);
        UPDATE posts SET comment_count = (SELECT COUNT(*) FROM comments WHERE post_id=posts.id);
        UPDATE users SET post_count      = (SELECT COUNT(*) FROM posts   WHERE user_id=users.id);
        UPDATE users SET follower_count  = (SELECT COUNT(*) FROM follows WHERE following_id=users.id);
        UPDATE users SET following_count = (SELECT COUNT(*) FROM follows WHERE follower_id=users.id);
    """)
    conn.commit()
    conn.close()
    print("✅ ConnectHub DB ready")

if __name__ == "__main__":
    init_db()
    print("DB:", DB)
