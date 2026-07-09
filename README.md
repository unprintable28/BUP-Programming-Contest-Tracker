# Programming Contest Registration & Score Tracker
**BUP CSE 3102 DBMS Lab Project**

---

## Stack
| Layer     | Tech                        |
|-----------|-----------------------------|
| Frontend  | HTML + CSS + JavaScript     |
| Backend   | Python 3 / Flask            |
| Database  | MySQL (via XAMPP)           |
| Tools     | XAMPP, VS Code, phpMyAdmin  |

---

## Setup Instructions

### 1. Install XAMPP
Download from https://www.apachefriends.org and start **Apache** and **MySQL** from the XAMPP Control Panel.

### 2. Create the Database
Open http://localhost/phpmyadmin in your browser, then:
- Click **SQL** tab
- Paste the contents of `schema.sql`
- Click **Go**

Or via XAMPP terminal:
```bash
mysql -u root < schema.sql
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

Open http://localhost:5000 in your browser.

---

## Default Login
| Email                 | Password  | Role  |
|-----------------------|-----------|-------|
| admin@contest.local   | admin123  | Admin |

Use the Admin portal to:
- Create more users and assign roles (participant / advisor)
- Create events and set their status
- Add problems with scoring and decay rules

---

## Portal Overview

| Portal         | URL            | Who uses it          |
|----------------|----------------|----------------------|
| Login/Register | /login         | Everyone             |
| Participant    | /participant   | Students/Contestants |
| Advisor        | /advisor       | Instructors/Judges   |
| Admin          | /admin         | Contest Organizers   |
| Leaderboard    | /leaderboard/N | Everyone             |

---

## Key Features

### Score Decay
Problems lose points over time:
- Each problem has a **base score** (e.g. 100)
- Every N minutes (**decay interval**), the score drops by M points (**decay amount**)
- Score never goes below **min score** floor
- Live score is shown on the problem card and refreshes every 30 seconds

### Team System
- Participants create teams per event
- Team leader can invite members by email
- Each team can only submit once per problem
- Individual member submission is tracked for internal team stats

### Judge / Solution Check
- Admin enters the **correct output** when creating a problem
- Participant submits their program's output as text
- System does an exact-match check (whitespace-trimmed)
- If correct → score awarded; if wrong → 0 points, try again

### Hints
- Advisors can send targeted hints to a specific team for a specific problem
- Participants see hints in the right sidebar of the event page

### Leaderboard
- Sorted by: total score ↓, problems solved ↓, first solve time ↑
- Available to all logged-in users
- Advisor sees live leaderboard while monitoring

---

## File Structure
```
contest_tracker/
├── app.py                  ← Flask backend (all routes)
├── schema.sql              ← MySQL database schema
├── requirements.txt        ← Python packages
├── static/
│   ├── css/style.css       ← Stylesheet
│   └── js/main.js          ← Frontend JS
└── templates/
    ├── base.html           ← Shared navbar/layout
    ├── login.html
    ├── register.html
    ├── leaderboard.html
    ├── participant/
    │   ├── dashboard.html
    │   ├── events.html
    │   ├── event_detail.html
    │   ├── create_team.html
    │   └── my_scores.html
    ├── advisor/
    │   ├── dashboard.html
    │   └── event.html
    └── admin/
        ├── dashboard.html
        ├── events.html
        ├── problems.html
        └── users.html
```
