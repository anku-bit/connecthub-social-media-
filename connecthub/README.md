# 📱 ConnectHub — Social Media Platform

Full-stack social media app built with **Python Flask + SQLite + Vanilla JS**.

---

## ⚡ Run in 3 Steps

```bash
# 1. Install dependencies
cd connecthub/backend
pip install -r requirements.txt

# 2. Start server
python app.py

# 3. Open browser
# → http://localhost:5002
```

The backend serves the frontend automatically. No separate setup needed.

---

## 🔐 Demo Accounts  (password for all: `Demo@123`)

| Name | Email | Username |
|------|-------|----------|
| Rahul Mehta | user@demo.com | @rahulmehta |
| Priya Sharma | priya@demo.com | @priyasharma |
| Amit Verma | amit@demo.com | @amitverma |
| Sneha Patel | sneha@demo.com | @sneha_patel |
| Vikram Singh | vikram@demo.com | @vikramsingh |
| Admin | admin@connecthub.com | @admin (password: Admin@123) |

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 👤 User Profiles | Bio, location, website, follower/following counts |
| 📝 Posts | Text + image URL, hashtag support |
| ❤️ Likes | Toggle like/unlike with real-time count update |
| 💬 Comments | Add, delete, threaded display |
| 👥 Follow System | Follow/unfollow, followers/following lists |
| 🔥 Explore Feed | Trending posts sorted by popularity |
| 🏠 Personal Feed | Posts from followed users |
| #️⃣ Hashtags | Trending hashtags sidebar, clickable search |
| 🔖 Save Posts | Bookmark posts to read later |
| 🔔 Notifications | Like, comment, follow notifications with unread badge |
| 🔍 Search | Search users and posts |
| 🛡️ Admin | Stats dashboard at /api/admin/stats |

---

## 📡 API Endpoints (30+)

### Auth
```
POST /api/auth/register     Register new user
POST /api/auth/login        Login (email or username)
GET  /api/auth/me           Current user info
PUT  /api/auth/update       Update profile
PUT  /api/auth/change-password
```

### Feed & Posts
```
GET  /api/feed              Personal feed (following users)
GET  /api/explore           Trending explore feed
POST /api/posts             Create post
GET  /api/posts/:id         Post detail + comments
DEL  /api/posts/:id         Delete own post
```

### Interactions
```
POST /api/posts/:id/like    Toggle like/unlike
POST /api/posts/:id/comments  Add comment
DEL  /api/comments/:id      Delete comment
POST /api/posts/:id/save    Toggle save
GET  /api/saved             Saved posts
```

### Users & Follows
```
GET  /api/users/:username   User profile + posts
POST /api/users/:id/follow  Toggle follow/unfollow
GET  /api/users/:id/followers
GET  /api/users/:id/following
```

### Discovery
```
GET  /api/search?q=...      Search users and posts
GET  /api/trending          Trending hashtags + suggested users
```

### Notifications
```
GET  /api/notifications     Get all notifications
PUT  /api/notifications/read-all
```

---

## 🗄️ Database Tables (8)

| Table | Description |
|-------|-------------|
| users | Profiles, bio, follower counts |
| posts | Content, image URL, like/comment counts |
| comments | Post comments with parent_id for replies |
| likes | User-post like pairs (unique constraint) |
| follows | Follower-following pairs (unique constraint) |
| notifications | Like/comment/follow alerts |
| saved_posts | Bookmarked posts per user |
| hashtags | Tag names with post counts |

---

## 🔒 Security

- Passwords hashed with **bcrypt** (salt rounds: automatic)
- Authentication via **JWT tokens** (30-day expiry)
- SQL injection prevented via **parameterized queries**
- CORS enabled for all origins (restrict in production)

---

## 🚀 Production Tips

```bash
# Use gunicorn instead of Flask dev server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 app:app

# Set a strong secret key
export SECRET_KEY=your-very-long-random-secret

# For HTTPS: use nginx + certbot
# For scale: switch to PostgreSQL
```
