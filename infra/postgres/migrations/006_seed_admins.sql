-- =============================================================================
-- 006 — Bootstrap administrator accounts (development only)
--
-- The previous seed inserted an `is_active` column that does not exist on
-- `admins`, and roles in uppercase ('SUPERADMIN') which the CHECK constraint
-- rejects — so the whole statement failed and there was no way to log in.
--
-- Credentials below are DEVELOPMENT DEFAULTS. Change them before exposing the
-- API anywhere. Generate a replacement hash with:
--
--   python -c "import bcrypt;print(bcrypt.hashpw(b'YOUR-PASSWORD', bcrypt.gensalt(12)).decode())"
-- =============================================================================

INSERT INTO admins (username, email, hashed_password, role)
VALUES (
    'superadmin',
    'superadmin@fraudguard.local',
    -- superadmin123
    '$2b$12$5b0Jm4D9LgqXxv4SmEGDQOFqlGiJ1Y8YsJDErG6QLgm9XSH72Q7NW',
    'superadmin'
)
ON CONFLICT (username) DO NOTHING;

INSERT INTO admins (username, email, hashed_password, role)
VALUES (
    'admin',
    'admin@fraudguard.local',
    -- admin123
    '$2b$12$spgE.7sEyp7Ei9au7fwdMuz13my.a2NT96XeGXdkuuFeyE7NXequK',
    'admin'
)
ON CONFLICT (username) DO NOTHING;
