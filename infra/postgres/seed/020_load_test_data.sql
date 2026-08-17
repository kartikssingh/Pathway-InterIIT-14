-- =============================================================================
-- LOAD TEST DATA POPULATION SCRIPT
-- This script adds sufficient data for comprehensive load testing
-- Handles existing data gracefully with ON CONFLICT
-- =============================================================================

-- =============================================================================
-- USERS TABLE - 100 test users for load testing
-- =============================================================================

DO $$
DECLARE
    i INTEGER;
    risk_levels TEXT[] := ARRAY['low', 'medium', 'high', 'critical'];
    kyc_statuses TEXT[] := ARRAY['approved', 'pending', 'approved', 'approved', 'under_review'];
    account_statuses TEXT[] := ARRAY['active', 'active', 'active', 'under_investigation', 'suspended'];
    cities TEXT[] := ARRAY['Mumbai', 'Delhi', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Kochi'];
    states TEXT[] := ARRAY['Maharashtra', 'Delhi', 'Karnataka', 'West Bengal', 'Tamil Nadu', 'Telangana', 'Maharashtra', 'Gujarat', 'Rajasthan', 'Kerala'];
BEGIN
    FOR i IN 1..100 LOOP
        INSERT INTO users (
            entity_id, 
            applicant_name, 
            email, 
            phone, 
            kyc_status, 
            i_360_score, 
            i_not_score, 
            suspicious_score, 
            risk_level, 
            is_blacklisted, 
            account_status, 
            address, 
            city, 
            state, 
            country, 
            postal_code, 
            date_of_birth, 
            kyc_verified_at
        ) VALUES (
            'APP-2024-' || LPAD(i::TEXT, 5, '0'),
            'Test User ' || i,
            'testuser' || i || '@example.com',
            '+91-98765' || LPAD(i::TEXT, 5, '0'),
            kyc_statuses[(i % 5) + 1],
            (RANDOM() * 100)::NUMERIC(5,2),
            (RANDOM() * 100)::NUMERIC(5,2),
            (RANDOM() * 100)::NUMERIC(5,2),
            risk_levels[(i % 4) + 1],
            (i % 20 = 0), -- Every 20th user is blacklisted
            account_statuses[(i % 5) + 1],
            i || ' Test Street',
            cities[(i % 10) + 1],
            states[(i % 10) + 1],
            'India',
            '40000' || (i % 10),
            NOW() - INTERVAL '20 years' + (i * INTERVAL '30 days'),
            CASE WHEN kyc_statuses[(i % 5) + 1] = 'approved' THEN NOW() - INTERVAL '30 days' ELSE NULL END
        )
        ON CONFLICT (entity_id) DO NOTHING;  -- Skip if already exists
    END LOOP;
END $$;

-- =============================================================================
-- TRANSACTIONS TABLE - 500 transactions for load testing
-- =============================================================================

DO $$
DECLARE
    i INTEGER;
    user_id_val INTEGER;
    transaction_types TEXT[] := ARRAY['deposit', 'withdrawal', 'transfer', 'payment'];
    risk_levels TEXT[] := ARRAY['low', 'medium', 'high', 'critical'];
    statuses TEXT[] := ARRAY['completed', 'pending', 'under_review', 'cancelled'];
    payment_methods TEXT[] := ARRAY['UPI', 'Bank Transfer', 'Credit Card', 'Debit Card', 'NEFT', 'RTGS', 'IMPS'];
    max_user_id INTEGER;
BEGIN
    -- Get actual max user ID to avoid foreign key violations
    SELECT COALESCE(MAX(id), 1) INTO max_user_id FROM users;
    
    FOR i IN 1..500 LOOP
        user_id_val := ((i - 1) % max_user_id) + 1;
        
        INSERT INTO transactions (
            user_id,
            transaction_id,
            transaction_type,
            amount,
            currency,
            sender_account,
            receiver_account,
            sender_name,
            receiver_name,
            suspicious_score,
            risk_level,
            is_flagged,
            status,
            payment_method,
            ip_address,
            device_id,
            location,
            transaction_date
        ) VALUES (
            user_id_val,
            'TXN-2024-' || LPAD(i::TEXT, 6, '0'),
            transaction_types[(i % 4) + 1],
            (RANDOM() * 1000000 + 1000)::NUMERIC(12,2),
            'INR',
            'ACC-' || LPAD(user_id_val::TEXT, 6, '0'),
            'ACC-' || LPAD((((i + 1) - 1) % max_user_id + 1)::TEXT, 6, '0'),
            'Test User ' || user_id_val,
            'Recipient ' || (((i + 1) - 1) % max_user_id + 1),
            (RANDOM() * 100)::NUMERIC(5,2),
            risk_levels[(i % 4) + 1],
            (i % 5 = 0), -- Every 5th transaction is flagged
            statuses[(i % 4) + 1],
            payment_methods[(i % 7) + 1],
            '192.168.' || (i % 255) || '.' || ((i * 3) % 255),
            'DEV-' || LPAD((user_id_val % 10)::TEXT, 3, '0'),
            'City-' || (i % 10) || ', State-' || (i % 10),
            NOW() - INTERVAL '30 days' + (i * INTERVAL '1 hour')
        )
        ON CONFLICT (transaction_id) DO NOTHING;  -- Skip if already exists
    END LOOP;
END $$;

-- =============================================================================
-- COMPLIANCE ALERTS TABLE - 100 alerts (mix of classified and unclassified)
-- =============================================================================

DO $$
DECLARE
    i INTEGER;
    user_id_val INTEGER;
    transaction_id_val INTEGER;
    alert_types TEXT[] := ARRAY['transaction_alert', 'fraud_alert', 'aml_alert', 'kyc_alert', 'behavioral_alert', 'sanction_alert'];
    severities TEXT[] := ARRAY['low', 'medium', 'high', 'critical'];
    statuses TEXT[] := ARRAY['active', 'investigating', 'resolved', 'dismissed', 'escalated'];
    sources TEXT[] := ARRAY['Transaction Monitoring', 'Fraud Detection', 'AML Screening', 'KYC System', 'Pattern Recognition'];
    max_user_id INTEGER;
    max_trans_id INTEGER;
BEGIN
    -- Get actual max IDs to avoid foreign key violations
    SELECT COALESCE(MAX(id), 0) INTO max_user_id FROM users;
    SELECT COALESCE(MAX(id), 0) INTO max_trans_id FROM transactions;
    
    FOR i IN 1..100 LOOP
        user_id_val := ((i - 1) % max_user_id) + 1;
        transaction_id_val := CASE WHEN max_trans_id > 0 THEN ((i - 1) % max_trans_id) + 1 ELSE NULL END;
        
        INSERT INTO compliance_alerts (
            user_id,
            transaction_id,
            alert_type,
            severity,
            title,
            description,
            entity_id,
            entity_type,
            rps360,
            status,
            priority,
            source,
            triggered_by,
            alert_metadata,
            triggered_at,
            is_true_positive,
            reviewed_at,
            reviewed_by
        ) VALUES (
            user_id_val,
            CASE WHEN i % 3 = 0 AND transaction_id_val IS NOT NULL THEN transaction_id_val ELSE NULL END,
            alert_types[(i % 6) + 1],
            severities[(i % 4) + 1],
            'Alert ' || i || ': ' || alert_types[(i % 6) + 1],
            'Test alert description for load testing - Alert ID: ' || i,
            'APP-2024-' || LPAD(user_id_val::TEXT, 5, '0'),
            'user',
            (RANDOM() * 100)::NUMERIC(5,2),
            statuses[(i % 5) + 1],
            severities[(i % 4) + 1],
            sources[(i % 5) + 1],
            'Auto-Detection',
            ('{"alert_id": ' || i || ', "test": true}')::JSONB,
            NOW() - INTERVAL '30 days' + (i * INTERVAL '7 hours'),
            -- Only classify 60% of alerts (40% remain unclassified for testing)
            CASE 
                WHEN i % 5 < 3 THEN (i % 2 = 0)::BOOLEAN  -- 60% classified (true/false)
                ELSE NULL  -- 40% unclassified
            END,
            CASE 
                WHEN i % 5 < 3 THEN NOW() - INTERVAL '10 days' + (i * INTERVAL '3 hours')
                ELSE NULL 
            END,
            CASE 
                WHEN i % 5 < 3 THEN 'reviewer' || (i % 5) || '@example.com'
                ELSE NULL 
            END
        );
    END LOOP;
END $$;

-- =============================================================================
-- INVESTIGATION CASES TABLE - 20 cases for testing
-- =============================================================================

DO $$
DECLARE
    i INTEGER;
    user_id_val INTEGER;
    case_types TEXT[] := ARRAY['fraud', 'aml', 'kyc', 'behavioral', 'sanctions'];
    severities TEXT[] := ARRAY['low', 'medium', 'high', 'critical'];
    statuses TEXT[] := ARRAY['open', 'investigating', 'pending_review', 'closed', 'escalated'];
    max_user_id INTEGER;
BEGIN
    -- Get actual max user ID to avoid foreign key violations
    SELECT COALESCE(MAX(id), 1) INTO max_user_id FROM users;
    
    FOR i IN 1..20 LOOP
        user_id_val := ((i - 1) % max_user_id) + 1;
        
        INSERT INTO investigation_cases (
            id,
            user_id,
            case_title,
            case_description,
            case_type,
            severity,
            status,
            priority,
            assigned_to,
            created_by,
            transaction_ids,
            alert_ids,
            investigation_notes,
            created_at,
            due_date
        ) VALUES (
            'CASE-2024-' || LPAD(i::TEXT, 5, '0'),
            user_id_val,
            'Investigation Case ' || i,
            'Test investigation case for load testing',
            case_types[(i % 5) + 1],
            severities[(i % 4) + 1],
            statuses[(i % 5) + 1],
            severities[(i % 4) + 1],
            'investigator' || (i % 5) || '@example.com',
            'system@example.com',
            '["TXN-2024-' || LPAD(((i * 5) % 500 + 1)::TEXT, 6, '0') || '"]',
            '["' || (i % 100 + 1) || '"]',
            'Investigation in progress for case ' || i,
            NOW() - INTERVAL '30 days' + (i * INTERVAL '1 day'),
            NOW() + INTERVAL '30 days' - (i * INTERVAL '1 day')
        )
        ON CONFLICT (id) DO NOTHING;  -- Skip if already exists
    END LOOP;
END $$;

-- =============================================================================
-- NOTIFICATION SETTINGS - All users get notification settings
-- =============================================================================

INSERT INTO notification_settings (
    user_id,
    enable_email,
    email_frequency,
    enable_sms,
    enable_push,
    notify_kyc_alerts,
    notify_transaction_alerts,
    notify_fraud_alerts,
    notify_aml_alerts,
    notify_case_updates,
    notify_hold_updates,
    min_severity_level
)
SELECT 
    id as user_id,
    TRUE,
    CASE (id % 4)
        WHEN 0 THEN 'immediate'
        WHEN 1 THEN 'hourly'
        WHEN 2 THEN 'daily'
        ELSE 'weekly'
    END,
    (id % 3 = 0),
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    CASE (id % 3)
        WHEN 0 THEN 'low'
        WHEN 1 THEN 'medium'
        ELSE 'high'
    END
FROM users
WHERE id NOT IN (SELECT user_id FROM notification_settings);

-- =============================================================================
-- VERIFICATION - Display counts
-- =============================================================================

SELECT 
    'Users' as table_name, 
    COUNT(*) as record_count,
    'Total users in system' as description
FROM users

UNION ALL

SELECT 
    'Transactions', 
    COUNT(*),
    'Total transactions'
FROM transactions

UNION ALL

SELECT 
    'Compliance Alerts (Total)', 
    COUNT(*),
    'All alerts'
FROM compliance_alerts

UNION ALL

SELECT 
    'Compliance Alerts (Unclassified)', 
    COUNT(*),
    'Alerts with is_true_positive = NULL'
FROM compliance_alerts
WHERE is_true_positive IS NULL

UNION ALL

SELECT 
    'Compliance Alerts (Classified)', 
    COUNT(*),
    'Alerts already classified'
FROM compliance_alerts
WHERE is_true_positive IS NOT NULL

UNION ALL

SELECT 
    'Investigation Cases', 
    COUNT(*),
    'Active and closed cases'
FROM investigation_cases

UNION ALL

SELECT 
    'Notification Settings', 
    COUNT(*),
    'User notification preferences'
FROM notification_settings

ORDER BY table_name;

-- Show sample severity distribution for alerts
SELECT 
    severity,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE is_true_positive IS NULL) as unclassified_count,
    COUNT(*) FILTER (WHERE is_true_positive IS NOT NULL) as classified_count
FROM compliance_alerts
GROUP BY severity
ORDER BY 
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END;

COMMIT;
