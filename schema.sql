-- ============================================================
-- Programming Contest Registration & Score Tracker
-- BUP CSE 3102 DBMS Lab Project
-- MySQL Schema — compatible with XAMPP / phpMyAdmin
-- ============================================================

CREATE DATABASE IF NOT EXISTS contest_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE contest_tracker;

-- ─────────────────────────────────────────────
-- USERS (unified table for all roles)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id      INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(150) NOT NULL UNIQUE,
    password     VARCHAR(255) NOT NULL,          -- bcrypt hash
    department   VARCHAR(100),
    role         ENUM('admin','participant','advisor') NOT NULL DEFAULT 'participant',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- EVENTS (contests)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id        INT AUTO_INCREMENT PRIMARY KEY,
    event_name      VARCHAR(200) NOT NULL,
    description     TEXT,
    start_time      DATETIME NOT NULL,
    end_time        DATETIME NOT NULL,
    max_team_size   INT DEFAULT 3,
    min_team_size   INT DEFAULT 1,
    status          ENUM('upcoming','ongoing','ended') DEFAULT 'upcoming',
    created_by      INT,                         -- admin user_id
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- PROBLEMS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS problems (
    problem_id      INT AUTO_INCREMENT PRIMARY KEY,
    event_id        INT NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    input_format    TEXT,
    output_format   TEXT,
    sample_input    TEXT,
    sample_output   TEXT,
    correct_output  TEXT NOT NULL,               -- system checks against this
    base_score      INT NOT NULL DEFAULT 100,    -- starts at base_score
    decay_interval  INT DEFAULT 10,             -- minutes before score drops
    decay_amount    INT DEFAULT 5,              -- points lost per interval
    min_score       INT DEFAULT 10,             -- floor score
    difficulty      ENUM('easy','medium','hard') DEFAULT 'medium',
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- TEAMS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    team_id         INT AUTO_INCREMENT PRIMARY KEY,
    team_name       VARCHAR(150) NOT NULL,
    event_id        INT NOT NULL,
    leader_id       INT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_team_event (team_name, event_id),
    FOREIGN KEY (event_id)   REFERENCES events(event_id)  ON DELETE CASCADE,
    FOREIGN KEY (leader_id)  REFERENCES users(user_id)    ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- TEAM MEMBERS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_members (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    team_id     INT NOT NULL,
    user_id     INT NOT NULL,
    joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY one_team_per_event (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)  ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)  ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- EVENT REGISTRATIONS (team → event)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_registrations (
    reg_id      INT AUTO_INCREMENT PRIMARY KEY,
    event_id    INT NOT NULL,
    team_id     INT NOT NULL,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_reg (event_id, team_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id)  REFERENCES teams(team_id)   ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- SUBMISSIONS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS submissions (
    sub_id          INT AUTO_INCREMENT PRIMARY KEY,
    problem_id      INT NOT NULL,
    user_id         INT NOT NULL,               -- who submitted
    team_id         INT NOT NULL,
    event_id        INT NOT NULL,
    submitted_output TEXT NOT NULL,
    is_correct      TINYINT(1) DEFAULT 0,
    score_awarded   INT DEFAULT 0,
    submitted_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(user_id)       ON DELETE CASCADE,
    FOREIGN KEY (team_id)    REFERENCES teams(team_id)        ON DELETE CASCADE,
    FOREIGN KEY (event_id)   REFERENCES events(event_id)      ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- HINTS (advisor → team)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hints (
    hint_id         INT AUTO_INCREMENT PRIMARY KEY,
    problem_id      INT NOT NULL,
    team_id         INT NOT NULL,
    advisor_id      INT NOT NULL,
    hint_text       TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id)  REFERENCES problems(problem_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id)     REFERENCES teams(team_id)        ON DELETE CASCADE,
    FOREIGN KEY (advisor_id)  REFERENCES users(user_id)        ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- LEADERBOARD VIEW (computed at query time)
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW leaderboard AS
SELECT
    e.event_id,
    e.event_name,
    t.team_id,
    t.team_name,
    u.name        AS leader_name,
    COUNT(DISTINCT CASE WHEN s.is_correct = 1 THEN s.problem_id END) AS solved,
    COALESCE(SUM(CASE WHEN s.is_correct = 1 THEN s.score_awarded ELSE 0 END), 0) AS total_score,
    MIN(CASE WHEN s.is_correct = 1 THEN s.submitted_at END) AS first_solve_time
FROM events e
JOIN teams t          ON t.event_id  = e.event_id
JOIN users u          ON u.user_id   = t.leader_id
LEFT JOIN submissions s ON s.team_id = t.team_id AND s.event_id = e.event_id
GROUP BY e.event_id, e.event_name, t.team_id, t.team_name, u.name
ORDER BY total_score DESC, solved DESC, first_solve_time ASC;

-- ─────────────────────────────────────────────
-- SEED: default admin account
-- password = "admin123"  (bcrypt hash)
-- ─────────────────────────────────────────────
INSERT IGNORE INTO users (name, email, password, role)
VALUES ('Admin', 'admin@contest.local',
        '$2b$12$KIXXZplX0uMoYY.Y7vL9nO5Z3q7GkXa.LyO6.jGhV1K.z9lW0gW5q',
        'admin');
