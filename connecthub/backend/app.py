"""
ConnectHub - Social Media Platform
Complete REST API: Auth, Feed, Posts, Likes, Comments, Follows,
                   Profiles, Search, Notifications, Trending
Run: python app.py  →  http://localhost:5002
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import re
import datetime
import functools
import bcrypt
import jwt

from database import get_db, init_db

app = Flask(__name__, static_folder="../frontend/public", static_url_path="")
CORS(app, origins="*")

SECRET = os.environ.get("SECRET_KEY", "connecthub_dev_secret_2024")

# ─── helpers ─────────────────────────────────────────────────────────────────

def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def check_pw(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())

def make_token(uid):
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    return jwt.encode({"uid": uid, "exp": exp}, SECRET, algorithm="HS256")

def decode_token(tok):
    try:
        return jwt.decode(tok, SECRET, algorithms=["HS256"])
    except Exception:
        return None

def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    data = decode_token(auth[7:])
    if not data:
        return None
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (data["uid"],)).fetchone()
    conn.close()
    return dict(u) if u else None

def auth_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return jsonify({"error": "Authentication required. Please login."}), 401
        request.user = u
        return fn(*args, **kwargs)
    return wrapper

def safe(text, maxlen=2000):
    return str(text or "").strip()[:maxlen]

def notify(to_uid, actor_id, ntype, message, post_id=None):
    if to_uid == actor_id:
        return
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO notifications(user_id,actor_id,type,post_id,message) VALUES(?,?,?,?,?)",
            (to_uid, actor_id, ntype, post_id, message)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def pub(u):
    """Return user dict without password."""
    return {k: v for k, v in dict(u).items() if k != "password"}

def extract_tags(text):
    return list(set(re.findall(r"#(\w+)", text)))


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    d = request.json or {}
    name     = safe(d.get("name", ""))
    username = safe(d.get("username", "")).lower().strip()
    email    = safe(d.get("email", "")).lower().strip()
    pw       = d.get("password", "")

    if not all([name, username, email, pw]):
        return jsonify({"error": "Name, username, email and password are required"}), 400
    if not re.match(r"^[a-z0-9_.]{3,20}$", username):
        return jsonify({"error": "Username: 3-20 chars, letters/numbers/underscore/dot only"}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email address"}), 400
    if len(pw) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    try:
        row = conn.execute(
            "INSERT INTO users(name,username,email,password) VALUES(?,?,?,?) RETURNING id",
            (name, username, email, hash_pw(pw))
        ).fetchone()
        uid = row["id"]
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        conn.close()
        notify(uid, uid, "welcome", f"Welcome to ConnectHub, {name}! 👋")
        return jsonify({"token": make_token(uid), "user": pub(user)}), 201
    except Exception as e:
        conn.close()
        msg = str(e)
        if "username" in msg:
            return jsonify({"error": "Username is already taken"}), 409
        if "email" in msg:
            return jsonify({"error": "Email is already registered"}), 409
        return jsonify({"error": "Registration failed. Please try again."}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    d  = request.json or {}
    em = safe(d.get("email", "")).lower().strip()
    pw = d.get("password", "")
    if not em or not pw:
        return jsonify({"error": "Email/username and password required"}), 400
    conn = get_db()
    u = conn.execute(
        "SELECT * FROM users WHERE email=? OR username=?", (em, em)
    ).fetchone()
    conn.close()
    if not u or not check_pw(pw, u["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": make_token(u["id"]), "user": pub(u)})


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def me():
    u = request.user
    conn = get_db()
    user   = conn.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
    unread = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (u["id"],)
    ).fetchone()[0]
    unread_notifs = unread
    conn.close()
    r = pub(user)
    r["unread_notifications"] = unread_notifs
    return jsonify(r)


@app.route("/api/auth/update", methods=["PUT"])
@auth_required
def update_profile():
    u    = request.user
    d    = request.json or {}
    conn = get_db()
    cur  = conn.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
    fields = {
        "name":     safe(d.get("name",     cur["name"])),
        "bio":      safe(d.get("bio",      cur["bio"]      or ""), 500),
        "website":  safe(d.get("website",  cur["website"]  or "")),
        "location": safe(d.get("location", cur["location"] or "")),
    }
    conn.execute(
        "UPDATE users SET name=?,bio=?,website=?,location=? WHERE id=?",
        (*fields.values(), u["id"])
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
    conn.close()
    return jsonify(pub(updated))


@app.route("/api/auth/change-password", methods=["PUT"])
@auth_required
def change_password():
    u   = request.user
    d   = request.json or {}
    old = d.get("old_password", "")
    new = d.get("new_password", "")
    if not old or not new or len(new) < 6:
        return jsonify({"error": "Both passwords required (new min 6 chars)"}), 400
    conn = get_db()
    row  = conn.execute("SELECT password FROM users WHERE id=?", (u["id"],)).fetchone()
    if not check_pw(old, row["password"]):
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 400
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new), u["id"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Password changed successfully"})


# ─── FEED & EXPLORE ──────────────────────────────────────────────────────────

@app.route("/api/feed", methods=["GET"])
@auth_required
def feed():
    u    = request.user
    page = max(1, int(request.args.get("page", 1)))
    per  = 15
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*,
               u.name, u.username, u.avatar, u.is_verified,
               (SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked,
               (SELECT 1 FROM saved_posts WHERE user_id=? AND post_id=p.id) AS is_saved
        FROM   posts p
        JOIN   users u ON p.user_id = u.id
        WHERE  p.user_id = ?
          OR   p.user_id IN (
               SELECT following_id FROM follows WHERE follower_id = ?
               )
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, (u["id"], u["id"], u["id"], u["id"], per, (page - 1) * per)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/explore", methods=["GET"])
def explore():
    page = max(1, int(request.args.get("page", 1)))
    per  = 15
    viewer = 0
    tok  = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*,
               u.name, u.username, u.avatar, u.is_verified,
               (SELECT 1 FROM likes      WHERE user_id=? AND post_id=p.id) AS is_liked,
               (SELECT 1 FROM saved_posts WHERE user_id=? AND post_id=p.id) AS is_saved
        FROM   posts p
        JOIN   users u ON p.user_id = u.id
        ORDER BY p.like_count DESC, p.created_at DESC
        LIMIT ? OFFSET ?
    """, (viewer, viewer, per, (page - 1) * per)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─── POSTS ────────────────────────────────────────────────────────────────────

@app.route("/api/posts", methods=["POST"])
@auth_required
def create_post():
    u = request.user
    d = request.json or {}
    content   = safe(d.get("content", ""), 2000)
    image_url = safe(d.get("image_url", ""))
    if not content.strip():
        return jsonify({"error": "Post content cannot be empty"}), 400

    tags = extract_tags(content)
    conn = get_db()
    row  = conn.execute(
        "INSERT INTO posts(user_id,content,image_url,hashtags) VALUES(?,?,?,?) RETURNING id",
        (u["id"], content, image_url, ",".join(tags))
    ).fetchone()
    pid = row["id"]
    conn.execute("UPDATE users SET post_count=post_count+1 WHERE id=?", (u["id"],))
    for tag in tags:
        conn.execute("INSERT OR IGNORE INTO hashtags(tag,post_count) VALUES(?,0)", (tag,))
        conn.execute("UPDATE hashtags SET post_count=post_count+1 WHERE tag=?", (tag,))
    conn.commit()
    post = conn.execute("""
        SELECT p.*, u.name, u.username, u.avatar, u.is_verified
        FROM   posts p JOIN users u ON p.user_id=u.id
        WHERE  p.id=?
    """, (pid,)).fetchone()
    conn.close()
    return jsonify(dict(post)), 201


@app.route("/api/posts/<int:pid>", methods=["GET"])
def get_post(pid):
    viewer = 0
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn = get_db()
    p = conn.execute("""
        SELECT p.*, u.name, u.username, u.avatar, u.is_verified,
               (SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked,
               (SELECT 1 FROM saved_posts WHERE user_id=? AND post_id=p.id) AS is_saved
        FROM   posts p JOIN users u ON p.user_id=u.id
        WHERE  p.id=?
    """, (viewer, viewer, pid)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Post not found"}), 404
    comments = conn.execute("""
        SELECT c.*, u.name, u.username, u.avatar
        FROM   comments c JOIN users u ON c.user_id=u.id
        WHERE  c.post_id=? AND c.parent_id IS NULL
        ORDER BY c.created_at ASC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify({"post": dict(p), "comments": [dict(c) for c in comments]})


@app.route("/api/posts/<int:pid>", methods=["DELETE"])
@auth_required
def delete_post(pid):
    u    = request.user
    conn = get_db()
    p    = conn.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Post not found"}), 404
    if p["user_id"] != u["id"]:
        conn.close()
        return jsonify({"error": "You can only delete your own posts"}), 403
    conn.execute("DELETE FROM posts WHERE id=?", (pid,))
    conn.execute("UPDATE users SET post_count=MAX(0,post_count-1) WHERE id=?", (u["id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Post deleted"})


# ─── LIKES ────────────────────────────────────────────────────────────────────

@app.route("/api/posts/<int:pid>/like", methods=["POST"])
@auth_required
def toggle_like(pid):
    u    = request.user
    conn = get_db()
    ex   = conn.execute(
        "SELECT id FROM likes WHERE user_id=? AND post_id=?", (u["id"], pid)
    ).fetchone()
    p    = conn.execute("SELECT user_id FROM posts WHERE id=?", (pid,)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    if ex:
        conn.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (u["id"], pid))
        conn.execute("UPDATE posts SET like_count=MAX(0,like_count-1) WHERE id=?", (pid,))
        liked = False
    else:
        conn.execute("INSERT INTO likes(user_id,post_id) VALUES(?,?)", (u["id"], pid))
        conn.execute("UPDATE posts SET like_count=like_count+1 WHERE id=?", (pid,))
        liked = True
        notify(p["user_id"], u["id"], "like",
               f"{u['name']} liked your post", post_id=pid)

    lc = conn.execute("SELECT like_count FROM posts WHERE id=?", (pid,)).fetchone()["like_count"]
    conn.commit()
    conn.close()
    return jsonify({"liked": liked, "like_count": lc})


# ─── COMMENTS ─────────────────────────────────────────────────────────────────

@app.route("/api/posts/<int:pid>/comments", methods=["POST"])
@auth_required
def add_comment(pid):
    u       = request.user
    d       = request.json or {}
    content = safe(d.get("content", ""), 500)
    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400
    conn = get_db()
    p    = conn.execute("SELECT user_id FROM posts WHERE id=?", (pid,)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    row = conn.execute(
        "INSERT INTO comments(post_id,user_id,content,parent_id) VALUES(?,?,?,?) RETURNING id",
        (pid, u["id"], content, d.get("parent_id"))
    ).fetchone()
    conn.execute("UPDATE posts SET comment_count=comment_count+1 WHERE id=?", (pid,))
    conn.commit()
    notify(p["user_id"], u["id"], "comment",
           f"{u['name']} commented on your post", post_id=pid)
    cm = conn.execute("""
        SELECT c.*, u.name, u.username, u.avatar
        FROM   comments c JOIN users u ON c.user_id=u.id
        WHERE  c.id=?
    """, (row["id"],)).fetchone()
    conn.close()
    return jsonify(dict(cm)), 201


@app.route("/api/comments/<int:cid>", methods=["DELETE"])
@auth_required
def delete_comment(cid):
    u    = request.user
    conn = get_db()
    cm   = conn.execute("SELECT * FROM comments WHERE id=?", (cid,)).fetchone()
    if not cm:
        conn.close()
        return jsonify({"error": "Comment not found"}), 404
    if cm["user_id"] != u["id"]:
        conn.close()
        return jsonify({"error": "You can only delete your own comments"}), 403
    conn.execute("DELETE FROM comments WHERE id=?", (cid,))
    conn.execute(
        "UPDATE posts SET comment_count=MAX(0,comment_count-1) WHERE id=?",
        (cm["post_id"],)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Comment deleted"})


# ─── FOLLOWS ──────────────────────────────────────────────────────────────────

@app.route("/api/users/<int:target_id>/follow", methods=["POST"])
@auth_required
def toggle_follow(target_id):
    u = request.user
    if u["id"] == target_id:
        return jsonify({"error": "You cannot follow yourself"}), 400
    conn = get_db()
    ex   = conn.execute(
        "SELECT id FROM follows WHERE follower_id=? AND following_id=?",
        (u["id"], target_id)
    ).fetchone()
    if ex:
        conn.execute(
            "DELETE FROM follows WHERE follower_id=? AND following_id=?",
            (u["id"], target_id)
        )
        conn.execute(
            "UPDATE users SET follower_count=MAX(0,follower_count-1) WHERE id=?",
            (target_id,)
        )
        conn.execute(
            "UPDATE users SET following_count=MAX(0,following_count-1) WHERE id=?",
            (u["id"],)
        )
        following = False
    else:
        conn.execute(
            "INSERT INTO follows(follower_id,following_id) VALUES(?,?)",
            (u["id"], target_id)
        )
        conn.execute(
            "UPDATE users SET follower_count=follower_count+1 WHERE id=?",
            (target_id,)
        )
        conn.execute(
            "UPDATE users SET following_count=following_count+1 WHERE id=?",
            (u["id"],)
        )
        following = True
        notify(target_id, u["id"], "follow",
               f"{u['name']} started following you")

    fc = conn.execute(
        "SELECT follower_count FROM users WHERE id=?", (target_id,)
    ).fetchone()["follower_count"]
    conn.commit()
    conn.close()
    return jsonify({"following": following, "follower_count": fc})


@app.route("/api/users/<int:uid>/followers", methods=["GET"])
def get_followers(uid):
    viewer = 0
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT u.*,
               (SELECT 1 FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM   follows f JOIN users u ON f.follower_id=u.id
        WHERE  f.following_id=?
        ORDER BY f.created_at DESC
    """, (viewer, uid)).fetchall()
    conn.close()
    return jsonify([pub(r) for r in rows])


@app.route("/api/users/<int:uid>/following", methods=["GET"])
def get_following(uid):
    viewer = 0
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT u.*,
               (SELECT 1 FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM   follows f JOIN users u ON f.following_id=u.id
        WHERE  f.follower_id=?
        ORDER BY f.created_at DESC
    """, (viewer, uid)).fetchall()
    conn.close()
    return jsonify([pub(r) for r in rows])


# ─── USER PROFILES ────────────────────────────────────────────────────────────

@app.route("/api/users/<string:username>", methods=["GET"])
def get_profile(username):
    viewer = 0
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn  = get_db()
    user  = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    is_following = bool(conn.execute(
        "SELECT 1 FROM follows WHERE follower_id=? AND following_id=?",
        (viewer, user["id"])
    ).fetchone())
    posts = conn.execute("""
        SELECT p.*,
               (SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked,
               (SELECT 1 FROM saved_posts WHERE user_id=? AND post_id=p.id) AS is_saved
        FROM posts p WHERE p.user_id=?
        ORDER BY p.created_at DESC
    """, (viewer, viewer, user["id"])).fetchall()
    conn.close()
    u_data = pub(user)
    u_data["is_following"] = is_following
    u_data["is_me"]        = (viewer == user["id"])
    return jsonify({"user": u_data, "posts": [dict(p) for p in posts]})


# ─── SAVED POSTS ──────────────────────────────────────────────────────────────

@app.route("/api/posts/<int:pid>/save", methods=["POST"])
@auth_required
def toggle_save(pid):
    u    = request.user
    conn = get_db()
    ex   = conn.execute(
        "SELECT id FROM saved_posts WHERE user_id=? AND post_id=?",
        (u["id"], pid)
    ).fetchone()
    if ex:
        conn.execute(
            "DELETE FROM saved_posts WHERE user_id=? AND post_id=?",
            (u["id"], pid)
        )
        saved = False
    else:
        conn.execute(
            "INSERT INTO saved_posts(user_id,post_id) VALUES(?,?)",
            (u["id"], pid)
        )
        saved = True
    conn.commit()
    conn.close()
    return jsonify({"saved": saved})


@app.route("/api/saved", methods=["GET"])
@auth_required
def saved_posts():
    u    = request.user
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, u.name, u.username, u.avatar, u.is_verified,
               1 AS is_saved,
               (SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked
        FROM   saved_posts sp
        JOIN   posts p  ON sp.post_id  = p.id
        JOIN   users u  ON p.user_id   = u.id
        WHERE  sp.user_id = ?
        ORDER BY sp.id DESC
    """, (u["id"], u["id"])).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─── SEARCH ───────────────────────────────────────────────────────────────────

@app.route("/api/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"users": [], "posts": []})
    viewer = 0
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        dd = decode_token(tok[7:])
        if dd:
            viewer = dd.get("uid", 0)
    conn  = get_db()
    users = conn.execute("""
        SELECT id, name, username, bio, avatar, follower_count, is_verified,
               (SELECT 1 FROM follows WHERE follower_id=? AND following_id=users.id) AS is_following
        FROM users
        WHERE name LIKE ? OR username LIKE ? OR bio LIKE ?
        LIMIT 8
    """, (viewer, f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    posts = conn.execute("""
        SELECT p.*, u.name, u.username, u.avatar, u.is_verified,
               (SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked
        FROM   posts p JOIN users u ON p.user_id=u.id
        WHERE  p.content LIKE ?
        ORDER BY p.like_count DESC
        LIMIT 10
    """, (viewer, f"%{q}%")).fetchall()
    conn.close()
    return jsonify({
        "users": [dict(r) for r in users],
        "posts": [dict(r) for r in posts]
    })


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
@auth_required
def get_notifications():
    u    = request.user
    conn = get_db()
    rows = conn.execute("""
        SELECT n.*, u.name AS actor_name, u.username AS actor_username, u.avatar AS actor_avatar
        FROM   notifications n
        JOIN   users u ON n.actor_id = u.id
        WHERE  n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 30
    """, (u["id"],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/notifications/read-all", methods=["PUT"])
@auth_required
def mark_all_read():
    u    = request.user
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (u["id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "All notifications marked as read"})


# ─── TRENDING ─────────────────────────────────────────────────────────────────

@app.route("/api/trending", methods=["GET"])
def trending():
    conn  = get_db()
    tags  = conn.execute(
        "SELECT * FROM hashtags ORDER BY post_count DESC LIMIT 12"
    ).fetchall()
    users = conn.execute("""
        SELECT id, name, username, avatar, bio, follower_count, is_verified
        FROM   users
        WHERE  username != 'admin'
        ORDER BY follower_count DESC
        LIMIT 8
    """).fetchall()
    conn.close()
    return jsonify({
        "hashtags": [dict(r) for r in tags],
        "users":    [dict(r) for r in users]
    })


# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route("/api/admin/stats", methods=["GET"])
@auth_required
def admin_stats():
    u = request.user
    # Simple check — any admin user has username 'admin'
    if u.get("username") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    conn = get_db()
    stats = {
        "total_users":    conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "total_posts":    conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        "total_comments": conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
        "total_likes":    conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0],
        "total_follows":  conn.execute("SELECT COUNT(*) FROM follows").fetchone()[0],
    }
    recent_users = conn.execute(
        "SELECT id,name,username,email,created_at FROM users ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    recent_posts = conn.execute("""
        SELECT p.id, p.content, p.like_count, u.name AS author, p.created_at
        FROM   posts p JOIN users u ON p.user_id=u.id
        ORDER BY p.created_at DESC LIMIT 5
    """).fetchall()
    conn.close()
    return jsonify({
        "stats":        stats,
        "recent_users": [dict(r) for r in recent_users],
        "recent_posts": [dict(r) for r in recent_posts],
    })


# ─── SERVE FRONTEND ───────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    fp = os.path.join(app.static_folder, path)
    if path and os.path.exists(fp):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n" + "=" * 54)
    print("  📱  ConnectHub — Social Media Platform")
    print("  🌐  Open:  http://localhost:5002")
    print("  📡  API:   http://localhost:5002/api")
    print("=" * 54)
    print("\n  Demo Accounts  (password for all: Demo@123)")
    print("  👤  user@demo.com      →  @rahulmehta")
    print("  👤  priya@demo.com     →  @priyasharma")
    print("  👤  amit@demo.com      →  @amitverma")
    print("  👤  sneha@demo.com     →  @sneha_patel")
    print("  👤  vikram@demo.com    →  @vikramsingh")
    print("  🛡️   admin@connecthub.com  /  Admin@123  →  @admin")
    print("=" * 54 + "\n")
    app.run(debug=True, port=5002, host="0.0.0.0")
