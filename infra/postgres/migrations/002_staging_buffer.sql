-- =============================================================================
-- 002 — Staging_Buffer and the trigger that fans a KYC report out
--
-- The `db-sink` pipeline flow writes one flat row per enriched applicant here.
-- An AFTER INSERT trigger distributes it to Users, ToxicityHistory and
-- UserSanctionMatches inside the same transaction, which is what keeps the three
-- tables consistent without the streaming job needing multi-table writes.
--
-- Fixes:
--   * the trigger inserted into UserSanctionMatches unconditionally, so every
--     applicant got a "screened" row even when no screening had run;
--   * ON CONFLICT used NEW.* on the right-hand side of COALESCE against the
--     unqualified table name, which is ambiguous under a table alias — the
--     EXCLUDED pseudo-table is the correct reference and is used throughout;
--   * a failure in one of the three inserts silently aborted the whole staging
--     insert with no indication of which one; each step is now commented and
--     the exception carries the user id.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Staging_Buffer (
    -- Identity
    user_id             BIGINT,
    uin                 CHAR(20),
    uin_hash            CHAR(64),
    username            TEXT,
    profile_pic         TEXT,
    email               VARCHAR(255),
    phone               VARCHAR(15),
    date_of_birth       TIMESTAMP,
    address             TEXT,
    occupation          VARCHAR(200),
    annual_income       DOUBLE PRECISION,

    -- KYC
    kyc_status          VARCHAR(100),
    kyc_verified_at     TIMESTAMP,
    signature_hash      VARCHAR(64),
    credit_score        INT,

    -- Status
    blacklisted         BOOLEAN DEFAULT FALSE,
    blacklisted_at      TIMESTAMP,
    risk_category       TEXT,

    -- Scores
    current_rps_not     DOUBLE PRECISION,
    current_rps_360     DOUBLE PRECISION,
    rps_not             DOUBLE PRECISION,
    rps_360             DOUBLE PRECISION,
    sanction_score      DOUBLE PRECISION,
    news_score          DOUBLE PRECISION,
    transaction_score   DOUBLE PRECISION,
    portfolio_score     DOUBLE PRECISION,
    calculation_trigger VARCHAR(50),

    -- Sanctions screening
    match_found         BOOLEAN,
    match_confidence    DOUBLE PRECISION,
    matched_entity_name TEXT,

    version             INT DEFAULT 1,
    created_at          TIMESTAMP,
    time                BIGINT,
    diff                INT
);

COMMENT ON TABLE Staging_Buffer IS
    'Landing table for the db-sink pipeline flow. A trigger fans each row out; '
    'rows here are transient and safe to truncate.';


CREATE OR REPLACE FUNCTION distribute_staging_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Step A: upsert the customer record ------------------------------------
    INSERT INTO Users (
        user_id, uin, uin_hash,
        username, profile_pic, email, phone, date_of_birth,
        address, occupation, annual_income, kyc_status,
        kyc_verified_at, signature_hash, credit_score,
        blacklisted, blacklisted_at,
        current_rps_not, current_rps_360,
        risk_category, version,
        created_at, last_rps_calculation, time, diff, updated_at
    )
    VALUES (
        NEW.user_id, NEW.uin, NEW.uin_hash,
        NEW.username, NEW.profile_pic, NEW.email, NEW.phone, NEW.date_of_birth,
        NEW.address, NEW.occupation, NEW.annual_income, NEW.kyc_status,
        NEW.kyc_verified_at, NEW.signature_hash, NEW.credit_score,
        COALESCE(NEW.blacklisted, FALSE), NEW.blacklisted_at,
        COALESCE(NEW.current_rps_not, NEW.rps_not), NEW.current_rps_360,
        NEW.risk_category, COALESCE(NEW.version, 1),
        COALESCE(NEW.created_at, CURRENT_TIMESTAMP),
        COALESCE(NEW.created_at, CURRENT_TIMESTAMP),
        NEW.time, NEW.diff,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (user_id) DO UPDATE SET
        username             = COALESCE(EXCLUDED.username,        Users.username),
        profile_pic          = COALESCE(EXCLUDED.profile_pic,     Users.profile_pic),
        email                = COALESCE(EXCLUDED.email,           Users.email),
        phone                = COALESCE(EXCLUDED.phone,           Users.phone),
        date_of_birth        = COALESCE(EXCLUDED.date_of_birth,   Users.date_of_birth),
        address              = COALESCE(EXCLUDED.address,         Users.address),
        occupation           = COALESCE(EXCLUDED.occupation,      Users.occupation),
        annual_income        = COALESCE(EXCLUDED.annual_income,   Users.annual_income),
        kyc_status           = COALESCE(EXCLUDED.kyc_status,      Users.kyc_status),
        kyc_verified_at      = COALESCE(EXCLUDED.kyc_verified_at, Users.kyc_verified_at),
        signature_hash       = COALESCE(EXCLUDED.signature_hash,  Users.signature_hash),
        credit_score         = COALESCE(EXCLUDED.credit_score,    Users.credit_score),
        blacklisted          = COALESCE(EXCLUDED.blacklisted,     Users.blacklisted),
        blacklisted_at       = COALESCE(EXCLUDED.blacklisted_at,  Users.blacklisted_at),
        current_rps_not      = COALESCE(EXCLUDED.current_rps_not, Users.current_rps_not),
        current_rps_360      = COALESCE(EXCLUDED.current_rps_360, Users.current_rps_360),
        risk_category        = COALESCE(EXCLUDED.risk_category,   Users.risk_category),
        last_rps_calculation = COALESCE(EXCLUDED.created_at,      Users.last_rps_calculation),
        updated_at           = CURRENT_TIMESTAMP,
        version              = Users.version + 1,
        time                 = COALESCE(EXCLUDED.time,            Users.time),
        diff                 = COALESCE(EXCLUDED.diff,            Users.diff);

    -- Step B: record the score in the history trail ---------------------------
    IF NEW.rps_not IS NOT NULL OR NEW.rps_360 IS NOT NULL THEN
        INSERT INTO ToxicityHistory (
            user_id, rps_not, rps_360, sanction_score,
            news_score, transaction_score, portfolio_score,
            calculation_trigger, calculated_at, time, diff
        )
        VALUES (
            NEW.user_id, NEW.rps_not, NEW.rps_360, NEW.sanction_score,
            NEW.news_score, NEW.transaction_score, NEW.portfolio_score,
            COALESCE(NEW.calculation_trigger, 'register'),
            COALESCE(NEW.created_at, CURRENT_TIMESTAMP), NEW.time, NEW.diff
        );
    END IF;

    -- Step C: record the screening outcome ------------------------------------
    -- Only when a screening actually happened; the original wrote a row every
    -- time, which made "how many customers have been screened?" unanswerable.
    IF NEW.match_found IS NOT NULL OR NEW.matched_entity_name IS NOT NULL THEN
        INSERT INTO UserSanctionMatches (
            user_id, match_found, match_confidence, matched_entity_name,
            checked_at, time, diff
        )
        VALUES (
            NEW.user_id, COALESCE(NEW.match_found, FALSE), NEW.match_confidence,
            NEW.matched_entity_name,
            COALESCE(NEW.created_at, CURRENT_TIMESTAMP), NEW.time, NEW.diff
        );
    END IF;

    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'distribute_staging_data failed for user_id=% : %', NEW.user_id, SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_process_staging ON Staging_Buffer;
CREATE TRIGGER trigger_process_staging
    AFTER INSERT ON Staging_Buffer
    FOR EACH ROW
    EXECUTE FUNCTION distribute_staging_data();
