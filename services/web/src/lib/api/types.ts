/**
 * Shared response and request types, mirroring the API's Pydantic schemas.
 *
 * Split out of the former 1,700-line `lib/api.ts`. Types live apart from the
 * request functions so a component can import a type without pulling in the
 * whole client.
 */

// ==================== TYPE DEFINITIONS ====================

export interface User {
  user_id: number; // Primary key (changed from id)
  uin?: string; // User Identification Number (max 20 chars)
  uin_hash?: string; // Hashed UIN (max 64 chars)
  username?: string; // Username (max 100 chars)
  profile_pic?: string; // URL/path to user's profile picture (nullable)
  email?: string;
  phone?: string; // Max 15 chars (changed from 20)
  date_of_birth?: string;
  address?: string; // TEXT type (unlimited length)
  occupation?: string; // Max 200 chars
  annual_income?: number; // Changed from string to number (Float)
  kyc_status?: string; // Max 100 chars (changed from 20)
  kyc_verified_at?: string;
  signature_hash?: string; // Max 64 chars
  credit_score?: number; // Integer, range: 300-900
  blacklisted: boolean; // Replaces is_blacklisted
  blacklisted_at?: string | null;
  current_rps_not?: number; // Current RPS (Not) score in 0-1 format (display as-is)
  current_rps_360?: number; // Current RPS 360 score in 0-1 format (display as-is)
  last_rps_calculation?: string; // Last RPS calculation timestamp
  risk_category?: string; // Max 100 chars
  version?: number; // Version control field
  time?: number; // Pathway timestamp (BigInteger)
  diff?: number; // Pathway diff field
  created_at?: string;
  updated_at?: string;
}

// Individual transaction record - matches backend schema
export interface Transaction {
  transaction_id: number;       // BIGINT primary key
  user_id: number;              // BIGINT, references users.user_id
  timestamp: string;            // TIMESTAMP - when transaction occurred
  amount: number;               // DOUBLE PRECISION - transaction amount
  currency: string;             // VARCHAR(10) - currency code (e.g., 'INR')
  txn_type: string;            // VARCHAR(50) - transaction type (e.g., 'TRANSFER', 'DEPOSIT')
  counterparty_id: number | null; // BIGINT - other party in transaction
  is_fraud: number;            // INT (0 or 1) - fraud flag (use is_fraud === 1 to check)
}

// Transaction aggregation data (legacy interface, may be deprecated)
export interface TransactionAggregation {
  user_id: number; // Primary key (changed from id)
  full_name?: string; // User's full name (max 255 chars)
  
  // 1-Hour Window Aggregations
  total_amount_1h?: number;
  txn_count_1h?: number;
  unique_cp_1h?: number; // Unique counterparties
  avg_amount_1h?: number;
  max_amount_1h?: number;
  min_amount_1h?: number;
  
  // 24-Hour Window Aggregations
  total_amount_24h?: number;
  txn_count_24h?: number;
  unique_cp_24h?: number;
  avg_amount_24h?: number;
  max_amount_24h?: number;
  min_amount_24h?: number;
  
  // 7-Day Window Aggregations
  total_amount_7d?: number;
  txn_count_7d?: number;
  unique_cp_7d?: number;
  avg_amount_7d?: number;
  max_amount_7d?: number;
  min_amount_7d?: number;
  
  // 30-Day Window Aggregations
  total_amount_30d?: number;
  txn_count_30d?: number;
  unique_cp_30d?: number;
  avg_amount_30d?: number;
  max_amount_30d?: number;
  min_amount_30d?: number;
  
  // Ratio Features
  incoming_outgoing_ratio_7d?: number; // Ratio of incoming to outgoing transactions
  
  // Metadata
  calculated_at?: string; // When aggregations were last calculated
}

export interface DashboardSummary {
  total_users: number;
  total_transactions: number; // Sum of all transactions in last 30 days (changed from 7 days)
  fraudulent_transactions: number; // Changed from flagged_transactions - transactions where is_fraud = 1
  blacklisted_users: number;
  high_risk_users: number; // Users with risk_category = 'high'
  critical_risk_users: number; // Users with risk_category = 'critical'
  pending_kyc: number; // Users with kyc_status = 'pending'
  average_i360_score: number; // RPS 360 score in 0-1 format (display as-is)
  total_volume: number; // Total transaction volume in last 30 days
  average_i_not_score: number; // RPS NOT score in 0-1 format (display as-is)
}

export interface RiskDistribution {
  low_risk: number;
  medium_risk: number;
  high_risk: number;
  critical_risk: number;
}

// Fraudulent transaction (where is_fraud = 1)
export interface FlaggedTransaction {
  transaction_id: number;       // BIGINT
  user_id: number;              // BIGINT
  user_name: string;            // From joined user data
  timestamp: string;            // Transaction timestamp
  amount: number;
  currency: string;
  txn_type: string;            // Changed from transaction_type
  is_fraud: number;            // Will be 1 for flagged transactions
}

// ==================== ALERT TYPE DEFINITIONS ====================

export type AlertType = 
  | 'kyc_alert' 
  | 'transaction_alert' 
  | 'fraud_alert' 
  | 'aml_alert' 
  | 'sanction_alert' 
  | 'behavioral_alert' 
  | 'system_alert';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type AlertStatus = 
  | 'active' 
  | 'investigating' 
  | 'resolved' 
  | 'dismissed' 
  | 'escalated';

export type Priority = 'low' | 'medium' | 'high' | 'critical';

export interface CriticalAlert {
  id: number | string; // Backend returns number, but some code expects string
  alert_id: number;
  alert_type: AlertType;
  severity: Severity;
  title?: string;
  description: string | null;
  user_id: number;
  user_name: string | null;
  entity_id?: string | null;
  entity_type?: string | null;
  transaction_id: number | null;
  amount: number | null;
  rps360?: number; // RPS 360 score in 0-1 format (display as-is)
  status?: AlertStatus;
  priority?: Priority;
  triggered_at: string;
  time_ago_seconds?: number; // May not be in backend response
  is_acknowledged?: boolean;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  assigned_to?: string | null;
  dismissal_reason?: string | null;
  source?: string | null;
  triggered_by?: string | null;
  alert_metadata?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface LiveAlert {
  id: string;
  severity: Severity;
  triggered_at: string;
  time_display: string;
}

export interface AlertTrendDataPoint {
  timestamp: string;
  count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface AlertTrendResponse {
  period: string;
  interval: string;
  data_points: AlertTrendDataPoint[];
  total_alerts: number;
  avg_per_interval: number;
}

// Full compliance alert response (matches ComplianceAlertRead from backend)
export interface ComplianceAlert {
  id: number;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string | null;
  user_id: number | null;
  user_name: string | null;
  transaction_id: number | null;
  entity_id: string | null;
  entity_type: string | null;
  rps360: number | null;           // Risk score 0-1
  priority: string | null;
  source: string | null;
  triggered_by: string | null;
  alert_metadata: string | null;   // JSON string
  triggered_at: string;            // ISO datetime
  status: 'active' | 'investigating' | 'resolved' | 'dismissed' | 'escalated';
  is_acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  dismissal_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComplianceAlertListResponse {
  total: number;
  items: ComplianceAlert[];
  limit: number;
  offset: number;
}

// Top alerts response
export interface TopAlertsResponse {
  total_returned: number;
  k: number;
  status_filter: string;
  alerts: ComplianceAlertSummaryItem[];
}

export interface ComplianceAlertSummaryItem {
  id: number;
  alert_type: string;
  severity: string;
  title: string;
  description: string | null;
  user_id: number | null;
  user_name: string | null;
  transaction_id: number | null;
  entity_id: string | null;
  rps360: number | null;
  status: string;
  priority: string | null;
  triggered_at: string | null;
  created_at: string | null;
  is_acknowledged: boolean;
}

// Alerts summary statistics
export interface AlertsSummaryResponse {
  total: number;
  pending_review: number;
  active: number;
  investigating: number;
  resolved: number;
  dismissed: number;
  escalated: number;
  by_severity: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
}

export interface AlertDismissRequest {
  reason?: string;
  notes?: string;
}

export interface AlertDismissResponse {
  success: boolean;
  alert_id: string;
  dismissed_at: string;
  dismissed_by: string;
}

export interface ComplianceAlertUpdate {
  status?: 'active' | 'investigating' | 'resolved' | 'dismissed' | 'escalated';
  priority?: 'low' | 'medium' | 'high';
  is_acknowledged?: boolean;
  acknowledged_by?: string;
  dismissal_reason?: string;
}

export interface UnclassifiedAlertsResponse {
  total: number;
  alerts: CriticalAlert[];
  limit: number;
  offset: number;
}

// ❌ REMOVED: Alert classification is no longer supported in backend
// export interface MarkAlertRequest {
//   is_true_positive: boolean;
//   notes?: string;
// }
// export interface MarkAlertResponse {
//   success: boolean;
//   message: string;
//   alert_id: number;
//   is_true_positive: boolean;
//   reviewed_at: string;
//   reviewed_by: string;
// }

// ==================== TOXICITY HISTORY TYPE DEFINITIONS ====================

export interface ToxicityHistory {
  history_id: number;
  user_id: number;
  rps_not?: number; // RPS (Not) risk score in 0-1 format (display as-is)
  rps_360?: number; // RPS 360 risk score in 0-1 format (display as-is)
  sanction_score?: number; // Sanction list match score
  news_score?: number; // Negative news sentiment score
  transaction_score?: number; // Transaction pattern risk score
  portfolio_score?: number; // Portfolio composition risk score
  calculated_at: string; // Timestamp when scores were calculated
  calculation_trigger?: string; // What triggered the calculation
  time?: number; // Pathway timestamp
  diff?: number; // Pathway diff field
}

export interface CreateToxicityHistoryRequest {
  user_id: number;
  rps_not?: number; // RPS (Not) score in 0-1 format (backend expects 0-1, not percentage)
  rps_360?: number; // RPS 360 score in 0-1 format (backend expects 0-1, not percentage)
  sanction_score?: number;
  news_score?: number;
  transaction_score?: number;
  portfolio_score?: number;
  calculation_trigger?: string;
  time?: number;
  diff?: number;
}

// ==================== USER SANCTION MATCHES TYPE DEFINITIONS ====================

export interface UserSanctionMatch {
  match_id: number;
  user_id: number;
  match_found: boolean; // Boolean indicating if a match was found
  match_confidence?: number; // Confidence score of the match (0.0 to 1.0)
  matched_entity_name?: string | null; // Name of the matched entity from sanction list
  checked_at: string; // Timestamp when check was performed
  time?: number; // Pathway timestamp
  diff?: number; // Pathway diff field
}

export interface CreateUserSanctionMatchRequest {
  user_id: number;
  match_found: boolean;
  match_confidence?: number;
  matched_entity_name?: string | null;
  time?: number;
  diff?: number;
}
