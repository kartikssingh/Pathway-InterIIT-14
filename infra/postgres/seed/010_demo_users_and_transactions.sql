-- =============================================================================
-- FRESH DUMMY DATA POPULATION SCRIPT
-- =============================================================================
-- This script populates fresh dummy data for the updated schema
-- Preserves existing admin and superadmin accounts
-- =============================================================================

-- =============================================================================
-- USERS TABLE - Sample users with varied risk profiles
-- =============================================================================

INSERT INTO users
    (entity_id, applicant_name, email, phone, kyc_status, i_360_score, i_not_score, suspicious_score, risk_level, is_blacklisted, account_status, address, city, state, country, postal_code, date_of_birth, kyc_verified_at)
VALUES
    ('APP-2024-00001', 'Rajesh Kumar', 'rajesh.kumar@email.com', '+91-9876543210', 'approved', 25.5, 15.0, 20.0, 'low', FALSE, 'active', '123 MG Road', 'Mumbai', 'Maharashtra', 'India', '400001', '1985-03-15', NOW() - INTERVAL '30 days'),
    ('APP-2024-00002', 'Priya Sharma', 'priya.sharma@email.com', '+91-9876543211', 'approved', 45.2, 38.0, 42.0, 'medium', FALSE, 'active', '456 Park Street', 'Kolkata', 'West Bengal', 'India', '700016', '1990-07-22', NOW() - INTERVAL '45 days'),
    ('APP-2024-00003', 'Amit Patel', 'amit.patel@email.com', '+91-9876543212', 'pending', 75.8, 72.0, 78.5, 'high', FALSE, 'under_investigation', '789 Civil Lines', 'Ahmedabad', 'Gujarat', 'India', '380001', '1988-11-30', NULL),
    ('APP-2024-00004', 'Sneha Reddy', 'sneha.reddy@email.com', '+91-9876543213', 'approved', 18.0, 12.5, 15.0, 'low', FALSE, 'active', '321 Banjara Hills', 'Hyderabad', 'Telangana', 'India', '500034', '1992-05-18', NOW() - INTERVAL '60 days'),
    ('APP-2024-00005', 'Vikram Singh', 'vikram.singh@email.com', '+91-9876543214', 'rejected', 92.3, 88.5, 95.0, 'critical', TRUE, 'suspended', '654 Connaught Place', 'New Delhi', 'Delhi', 'India', '110001', '1983-09-25', NULL),
    ('APP-2024-00006', 'Ananya Iyer', 'ananya.iyer@email.com', '+91-9876543215', 'approved', 32.1, 28.0, 30.0, 'low', FALSE, 'active', '987 Brigade Road', 'Bangalore', 'Karnataka', 'India', '560001', '1995-02-14', NOW() - INTERVAL '20 days'),
    ('APP-2024-00007', 'Rahul Mehta', 'rahul.mehta@email.com', '+91-9876543216', 'under_review', 58.9, 55.0, 60.0, 'medium', FALSE, 'active', '147 FC Road', 'Pune', 'Maharashtra', 'India', '411004', '1987-12-08', NULL),
    ('APP-2024-00008', 'Divya Nair', 'divya.nair@email.com', '+91-9876543217', 'approved', 22.3, 18.5, 20.0, 'low', FALSE, 'active', '258 Marine Drive', 'Kochi', 'Kerala', 'India', '682011', '1993-06-30', NOW() - INTERVAL '90 days'),
    ('APP-2024-00009', 'Karan Chopra', 'karan.chopra@email.com', '+91-9876543218', 'approved', 65.7, 62.0, 68.0, 'high', FALSE, 'active', '369 Mall Road', 'Chandigarh', 'Chandigarh', 'India', '160001', '1989-04-12', NOW() - INTERVAL '15 days'),
    ('APP-2024-00010', 'Meera Joshi', 'meera.joshi@email.com', '+91-9876543219', 'approved', 28.5, 25.0, 27.0, 'low', FALSE, 'active', '741 Residency Road', 'Jaipur', 'Rajasthan', 'India', '302001', '1991-08-20', NOW() - INTERVAL '50 days'),
    ('APP-2024-00011', 'Sanjay Gupta', 'sanjay.gupta@email.com', '+91-9876543220', 'approved', 35.0, 30.0, 33.0, 'medium', FALSE, 'active', '852 MG Road', 'Bangalore', 'Karnataka', 'India', '560002', '1986-01-10', NOW() - INTERVAL '35 days'),
    ('APP-2024-00012', 'Pooja Verma', 'pooja.verma@email.com', '+91-9876543221', 'approved', 19.5, 16.0, 18.0, 'low', FALSE, 'active', '963 Anna Salai', 'Chennai', 'Tamil Nadu', 'India', '600001', '1994-09-05', NOW() - INTERVAL '40 days');

-- =============================================================================
-- TRANSACTIONS TABLE - Sample transactions with varied risk levels
-- =============================================================================

INSERT INTO transactions
    (user_id, transaction_id, transaction_type, amount, currency, sender_account, receiver_account, sender_name, receiver_name, suspicious_score, risk_level, is_flagged, status, payment_method, ip_address, device_id, location, transaction_date)
VALUES
    -- User 1 (Rajesh Kumar) - Low risk transactions
    (1, 'TXN-2024-10001', 'deposit', 50000.00, 'INR', 'ACC-100001', 'ACC-100002', 'Rajesh Kumar', 'Merchant Account', 15.0, 'low', FALSE, 'completed', 'UPI', '192.168.1.1', 'DEV-001', 'Mumbai, Maharashtra', NOW() - INTERVAL '5 days'),
    (1, 'TXN-2024-10002', 'withdrawal', 25000.00, 'INR', 'ACC-100002', 'ACC-100001', 'Rajesh Kumar', 'Bank Account', 20.0, 'low', FALSE, 'completed', 'Bank Transfer', '192.168.1.1', 'DEV-001', 'Mumbai, Maharashtra', NOW() - INTERVAL '3 days'),
    
    -- User 2 (Priya Sharma) - Medium risk transactions
    (2, 'TXN-2024-10003', 'transfer', 150000.00, 'INR', 'ACC-100003', 'ACC-200001', 'Priya Sharma', 'Business Partner', 48.5, 'medium', TRUE, 'completed', 'NEFT', '192.168.2.10', 'DEV-002', 'Kolkata, West Bengal', NOW() - INTERVAL '7 days'),
    (2, 'TXN-2024-10004', 'payment', 75000.00, 'INR', 'ACC-100003', 'MERCHANT-001', 'Priya Sharma', 'Online Merchant', 42.0, 'medium', FALSE, 'completed', 'Credit Card', '192.168.2.10', 'DEV-002', 'Kolkata, West Bengal', NOW() - INTERVAL '2 days'),
    
    -- User 3 (Amit Patel) - High risk transactions
    (3, 'TXN-2024-10005', 'deposit', 500000.00, 'INR', 'ACC-UNKNOWN', 'ACC-100004', 'Unknown Source', 'Amit Patel', 85.0, 'high', TRUE, 'under_review', 'Cash Deposit', '10.0.0.5', 'DEV-003', 'Ahmedabad, Gujarat', NOW() - INTERVAL '1 day'),
    (3, 'TXN-2024-10006', 'withdrawal', 450000.00, 'INR', 'ACC-100004', 'ACC-OFFSHORE', 'Amit Patel', 'Offshore Account', 92.0, 'critical', TRUE, 'pending', 'Wire Transfer', '10.0.0.5', 'DEV-003', 'Ahmedabad, Gujarat', NOW() - INTERVAL '6 hours'),
    
    -- User 4 (Sneha Reddy) - Low risk transactions
    (4, 'TXN-2024-10007', 'payment', 35000.00, 'INR', 'ACC-100005', 'MERCHANT-002', 'Sneha Reddy', 'E-commerce Store', 18.0, 'low', FALSE, 'completed', 'Debit Card', '192.168.3.15', 'DEV-004', 'Hyderabad, Telangana', NOW() - INTERVAL '8 days'),
    (4, 'TXN-2024-10008', 'transfer', 20000.00, 'INR', 'ACC-100005', 'ACC-100006', 'Sneha Reddy', 'Family Member', 12.0, 'low', FALSE, 'completed', 'UPI', '192.168.3.15', 'DEV-004', 'Hyderabad, Telangana', NOW() - INTERVAL '4 days'),
    
    -- User 5 (Vikram Singh) - Critical risk transactions
    (5, 'TXN-2024-10009', 'transfer', 800000.00, 'INR', 'ACC-100007', 'ACC-SUSPICIOUS', 'Vikram Singh', 'Unverified Entity', 95.0, 'critical', TRUE, 'cancelled', 'Wire Transfer', '10.0.0.10', 'DEV-005', 'New Delhi, Delhi', NOW() - INTERVAL '10 days'),
    (5, 'TXN-2024-10010', 'deposit', 1000000.00, 'INR', 'ACC-UNKNOWN2', 'ACC-100007', 'Shell Company', 'Vikram Singh', 98.5, 'critical', TRUE, 'under_review', 'Cash Deposit', '10.0.0.10', 'DEV-005', 'New Delhi, Delhi', NOW() - INTERVAL '5 days'),
    
    -- User 6 (Ananya Iyer) - Low risk transactions
    (6, 'TXN-2024-10011', 'payment', 45000.00, 'INR', 'ACC-100008', 'MERCHANT-003', 'Ananya Iyer', 'Shopping Portal', 25.0, 'low', FALSE, 'completed', 'Credit Card', '192.168.4.20', 'DEV-006', 'Bangalore, Karnataka', NOW() - INTERVAL '6 days'),
    (6, 'TXN-2024-10012', 'withdrawal', 30000.00, 'INR', 'ACC-100008', 'ACC-100009', 'Ananya Iyer', 'Savings Account', 22.0, 'low', FALSE, 'completed', 'Bank Transfer', '192.168.4.20', 'DEV-006', 'Bangalore, Karnataka', NOW() - INTERVAL '1 day'),
    
    -- User 7 (Rahul Mehta) - Medium risk transactions
    (7, 'TXN-2024-10013', 'transfer', 200000.00, 'INR', 'ACC-100010', 'ACC-100011', 'Rahul Mehta', 'Business Associate', 55.0, 'medium', TRUE, 'completed', 'RTGS', '192.168.5.25', 'DEV-007', 'Pune, Maharashtra', NOW() - INTERVAL '9 days'),
    (7, 'TXN-2024-10014', 'payment', 85000.00, 'INR', 'ACC-100010', 'MERCHANT-004', 'Rahul Mehta', 'Service Provider', 60.0, 'medium', FALSE, 'completed', 'NEFT', '192.168.5.25', 'DEV-007', 'Pune, Maharashtra', NOW() - INTERVAL '3 days'),
    
    -- User 8 (Divya Nair) - Low risk transactions
    (8, 'TXN-2024-10015', 'deposit', 40000.00, 'INR', 'ACC-100012', 'ACC-100013', 'Divya Nair', 'Salary Account', 18.5, 'low', FALSE, 'completed', 'Direct Deposit', '192.168.6.30', 'DEV-008', 'Kochi, Kerala', NOW() - INTERVAL '12 days'),
    (8, 'TXN-2024-10016', 'payment', 15000.00, 'INR', 'ACC-100013', 'MERCHANT-005', 'Divya Nair', 'Utility Provider', 20.0, 'low', FALSE, 'completed', 'UPI', '192.168.6.30', 'DEV-008', 'Kochi, Kerala', NOW() - INTERVAL '2 days'),
    
    -- User 9 (Karan Chopra) - High risk transactions
    (9, 'TXN-2024-10017', 'transfer', 350000.00, 'INR', 'ACC-100014', 'ACC-FOREIGN', 'Karan Chopra', 'Foreign Account', 70.0, 'high', TRUE, 'completed', 'Wire Transfer', '192.168.7.35', 'DEV-009', 'Chandigarh, Chandigarh', NOW() - INTERVAL '11 days'),
    (9, 'TXN-2024-10018', 'withdrawal', 280000.00, 'INR', 'ACC-100014', 'ACC-100015', 'Karan Chopra', 'Investment Account', 65.0, 'high', FALSE, 'completed', 'Bank Transfer', '192.168.7.35', 'DEV-009', 'Chandigarh, Chandigarh', NOW() - INTERVAL '4 days'),
    
    -- User 10 (Meera Joshi) - Low risk transactions
    (10, 'TXN-2024-10019', 'payment', 28000.00, 'INR', 'ACC-100016', 'MERCHANT-006', 'Meera Joshi', 'Travel Agency', 25.0, 'low', FALSE, 'completed', 'Credit Card', '192.168.8.40', 'DEV-010', 'Jaipur, Rajasthan', NOW() - INTERVAL '7 days'),
    (10, 'TXN-2024-10020', 'deposit', 55000.00, 'INR', 'ACC-100017', 'ACC-100016', 'Employer', 'Meera Joshi', 27.0, 'low', FALSE, 'completed', 'Direct Deposit', '192.168.8.40', 'DEV-010', 'Jaipur, Rajasthan', NOW() - INTERVAL '1 day');

-- =============================================================================
-- COMPLIANCE ALERTS TABLE - Sample alerts for monitoring
-- =============================================================================

INSERT INTO compliance_alerts
    (user_id, transaction_id, alert_type, severity, title, description, entity_id, entity_type, rps360, status, priority, source, triggered_by, triggered_at)
VALUES
    -- Low severity alerts
    (1, 1, 'transaction_alert', 'low', 'Large Deposit Detected', 'User made a deposit exceeding 50,000 INR', 'APP-2024-00001', 'user', 15.0, 'active', 'low', 'transaction_monitoring', 'automated_system', NOW() - INTERVAL '5 days'),
    (4, 7, 'kyc_alert', 'low', 'Document Update Required', 'KYC document expiring in 30 days', 'APP-2024-00004', 'user', 12.5, 'active', 'low', 'kyc_monitoring', 'automated_system', NOW() - INTERVAL '8 days'),
    (6, 11, 'transaction_alert', 'low', 'Multiple Transactions', 'User has made multiple transactions in short period', 'APP-2024-00006', 'user', 28.0, 'resolved', 'low', 'transaction_monitoring', 'automated_system', NOW() - INTERVAL '6 days'),
    
    -- Medium severity alerts
    (2, 3, 'transaction_alert', 'medium', 'High Value Transfer', 'Transfer of 150,000 INR to business partner', 'APP-2024-00002', 'user', 38.0, 'investigating', 'medium', 'transaction_monitoring', 'automated_system', NOW() - INTERVAL '7 days'),
    (7, 13, 'fraud_alert', 'medium', 'Unusual Transaction Pattern', 'Transaction pattern differs from historical behavior', 'APP-2024-00007', 'user', 55.0, 'active', 'medium', 'behavioral_analysis', 'ml_model', NOW() - INTERVAL '9 days'),
    
    -- High severity alerts
    (3, 5, 'aml_alert', 'high', 'Large Cash Deposit - Unknown Source', 'Cash deposit of 500,000 INR from unverified source', 'APP-2024-00003', 'user', 72.0, 'investigating', 'high', 'aml_monitoring', 'automated_system', NOW() - INTERVAL '1 day'),
    (3, 6, 'fraud_alert', 'high', 'Offshore Account Transfer', 'Attempted transfer to offshore account', 'APP-2024-00003', 'user', 72.0, 'escalated', 'critical', 'transaction_monitoring', 'automated_system', NOW() - INTERVAL '6 hours'),
    (9, 17, 'transaction_alert', 'high', 'Foreign Transfer', 'Large transfer to foreign account', 'APP-2024-00009', 'user', 62.0, 'active', 'high', 'transaction_monitoring', 'automated_system', NOW() - INTERVAL '11 days'),
    
    -- Critical severity alerts
    (5, 9, 'fraud_alert', 'critical', 'Suspicious Transfer to Unverified Entity', 'Transfer of 800,000 INR to suspicious account', 'APP-2024-00005', 'user', 88.5, 'escalated', 'critical', 'fraud_detection', 'ml_model', NOW() - INTERVAL '10 days'),
    (5, 10, 'aml_alert', 'critical', 'High Value Cash Deposit from Shell Company', 'Deposit of 1,000,000 INR from suspected shell company', 'APP-2024-00005', 'user', 88.5, 'escalated', 'critical', 'aml_monitoring', 'automated_system', NOW() - INTERVAL '5 days'),
    
    -- System alerts
    (NULL, NULL, 'system_alert', 'medium', 'Daily KYC Review Required', 'Daily review of pending KYC applications', NULL, 'system', 0.0, 'active', 'medium', 'system', 'scheduled_task', NOW() - INTERVAL '1 day'),
    (NULL, NULL, 'behavioral_alert', 'low', 'Weekly Risk Assessment Complete', 'Weekly user risk scores have been updated', NULL, 'system', 0.0, 'resolved', 'low', 'system', 'scheduled_task', NOW() - INTERVAL '2 days');

-- =============================================================================
-- INVESTIGATION CASES - Sample cases
-- =============================================================================

INSERT INTO investigation_cases
    (id, user_id, case_title, case_description, case_type, severity, status, priority, assigned_to, created_by, transaction_ids, alert_ids, created_at)
VALUES
    ('CASE-2024-0001', 3, 'High Risk Transaction Pattern Investigation', 'Investigation into multiple high-value transactions from unknown sources', 'aml', 'high', 'investigating', 'high', 'admin', 'admin', '5,6', '6,7', NOW() - INTERVAL '1 day'),
    ('CASE-2024-0002', 5, 'Critical Fraud Case - Suspected Money Laundering', 'Critical investigation into suspected money laundering activities', 'fraud', 'critical', 'investigating', 'critical', 'superadmin', 'superadmin', '9,10', '9,10', NOW() - INTERVAL '5 days'),
    ('CASE-2024-0003', 2, 'Business Transaction Review', 'Review of high-value business transactions', 'other', 'medium', 'pending_review', 'medium', 'admin', 'admin', '3,4', '4', NOW() - INTERVAL '7 days');

-- =============================================================================
-- ACCOUNT HOLDS - Sample holds
-- =============================================================================

INSERT INTO account_holds
    (id, user_id, case_id, hold_type, hold_reason, severity, status, hold_placed_at, placed_by, approved_by)
VALUES
    ('HOLD-2024-0001', 5, 'CASE-2024-0002', 'investigation', 'Account suspended pending fraud investigation', 'critical', 'active', NOW() - INTERVAL '5 days', 'superadmin', 'superadmin'),
    ('HOLD-2024-0002', 3, 'CASE-2024-0001', 'temporary', 'Temporary hold for AML review', 'high', 'active', NOW() - INTERVAL '1 day', 'admin', 'admin');

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

SELECT 'Fresh dummy data populated successfully!' AS status;
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as transaction_count FROM transactions;
SELECT COUNT(*) as alert_count FROM compliance_alerts;
SELECT COUNT(*) as case_count FROM investigation_cases;
SELECT COUNT(*) as hold_count FROM account_holds;
