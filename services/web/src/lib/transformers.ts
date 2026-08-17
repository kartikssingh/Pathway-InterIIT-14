// Data transformation utilities to convert API responses to component formats
import { User as ApiUser, Transaction as ApiTransaction, getRiskCategory } from './api';

// ==================== TYPE DEFINITIONS ====================

export interface UserEvent {
  id: number;
  type: string;
  by?: string;
  description?: string;
  timestamp: string;
  color: "blue" | "red" | "green" | "gray" | "yellow";
  iconType: "edit" | "alert" | "transaction" | "document";
  isAlert?: boolean;
  ruleId?: string;
  at?: string;
  document?: string;
}

export interface ComponentUser {
  user_id: number; // Changed from id
  name: string;
  email: string;
  createdAt: string;
  status: "Verified" | "Unverified" | "Blacklisted";
  statusColor: string;
  accountStatus: "Active" | "Suspended";
  image?: string; // Deprecated - use profilePic instead
  profilePic?: string; // URL/path to user's profile picture
  riskScore: number;
  riskLevel: string;
  kycStatus: "Verified" | "Pending" | "Rejected";
  lastLogin: string;
  accountAge: string;
  events: UserEvent[];
  // New API fields
  uin?: string;
  username?: string;
  phone?: string;
  occupation?: string;
  dateOfBirth?: string;
  address?: string;
  annualIncome?: number;
  creditScore?: number;
  blacklisted: boolean;
  currentRpsNot?: number;
  currentRps360?: number;
  lastRpsCalculation?: string;
  riskCategory?: string;
}

export interface ComponentTransaction {
  user_id: number; // Changed from id
  full_name?: string;
  // Aggregated metrics for display
  total_amount_1h?: number;
  txn_count_1h?: number;
  unique_cp_1h?: number;
  total_amount_24h?: number;
  txn_count_24h?: number;
  unique_cp_24h?: number;
  total_amount_7d?: number;
  txn_count_7d?: number;
  unique_cp_7d?: number;
  total_amount_30d?: number;
  txn_count_30d?: number;
  unique_cp_30d?: number;
  avg_amount_7d?: number;
  max_amount_7d?: number;
  min_amount_7d?: number;
  incoming_outgoing_ratio_7d?: number;
  calculated_at?: string;
  // For legacy display compatibility
  displayAmount?: string;
  displayTxnCount?: string;
  riskLevel?: string;
}

// ==================== USER TRANSFORMERS ====================

/**
 * Convert API user to component user format
 */
export function transformApiUserToComponent(apiUser: ApiUser, userEvents: UserEvent[] = []): ComponentUser {
  // Map blacklisted status to component status
  const getStatus = (): "Verified" | "Unverified" | "Blacklisted" => {
    if (apiUser.blacklisted) return "Blacklisted";
    // Check KYC status from new kyc_status field
    if (apiUser.kyc_status?.toLowerCase() === 'verified') return "Verified";
    return "Unverified";
  };

  const status = getStatus();
  
  // Map status colors
  const getStatusColor = (status: string): string => {
    switch (status) {
      case "Verified":
        return "bg-green-100 text-green-700";
      case "Blacklisted":
        return "bg-red-100 text-red-700";
      default:
        return "bg-yellow-100 text-yellow-700";
    }
  };

  // Map risk level based on current_rps_360 or risk_category
  const getRiskLevel = (): string => {
    if (apiUser.risk_category) {
      const category = apiUser.risk_category.toLowerCase();
      return category.charAt(0).toUpperCase() + category.slice(1);
    }
    if (apiUser.current_rps_360 !== undefined) {
      const category = getRiskCategory(apiUser.current_rps_360);
      return category.charAt(0) + category.slice(1).toLowerCase();
    }
    return "Unknown";
  };

  // Calculate account age
  const calculateAccountAge = (createdAt?: string): string => {
    if (!createdAt) return "Unknown";
    const created = new Date(createdAt);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - created.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 30) {
      return `${diffDays} Days`;
    } else if (diffDays < 365) {
      const months = Math.floor(diffDays / 30);
      return `${months} Month${months > 1 ? 's' : ''}`;
    } else {
      const years = Math.floor(diffDays / 365);
      return `${years} Year${years > 1 ? 's' : ''}`;
    }
  };

  // Use updated_at or last_rps_calculation as last activity
  const lastLogin = formatRelativeTime(apiUser.updated_at || apiUser.last_rps_calculation || apiUser.created_at || new Date().toISOString());

  return {
    user_id: apiUser.user_id,
    name: apiUser.username || apiUser.email?.split('@')[0] || `User ${apiUser.user_id}`,
    email: apiUser.email || 'No email provided',
    createdAt: apiUser.created_at || new Date().toISOString(),
    status,
    statusColor: getStatusColor(status),
    accountStatus: apiUser.blacklisted ? "Suspended" : "Active",
    image: undefined, // Deprecated - use profilePic instead
    profilePic: apiUser.profile_pic, // Profile picture URL/path
    riskScore: apiUser.current_rps_not || 0,
    riskLevel: getRiskLevel(),
    kycStatus: status === "Verified" ? "Verified" : (status === "Blacklisted" ? "Rejected" : "Pending"),
    lastLogin,
    accountAge: calculateAccountAge(apiUser.created_at),
    events: userEvents,
    uin: apiUser.uin,
    username: apiUser.username,
    phone: apiUser.phone,
    occupation: apiUser.occupation,
    dateOfBirth: apiUser.date_of_birth,
    address: apiUser.address,
    annualIncome: apiUser.annual_income,
    creditScore: apiUser.credit_score,
    blacklisted: apiUser.blacklisted,
    currentRpsNot: apiUser.current_rps_not,
    currentRps360: apiUser.current_rps_360,
    lastRpsCalculation: apiUser.last_rps_calculation,
    riskCategory: apiUser.risk_category,
  };
}

/**
 * Generate user events from individual transactions (for timeline view)
 * ⚠️ NOTE: Backend now returns individual transactions, not aggregations
 */
export function generateUserEventsFromTransactions(
  transactions: ApiTransaction | ApiTransaction[],
  userId: number
): UserEvent[] {
  // Convert to array if single transaction
  const txArray = Array.isArray(transactions) ? transactions : [transactions];
  
  if (!txArray || txArray.length === 0) return [];

  const events: UserEvent[] = [];
  
  // Create event for each transaction (limit to recent 10)
  const recentTransactions = txArray.slice(0, 10);
  
  recentTransactions.forEach((tx, index) => {
    const isFraud = tx.is_fraud === 1;
    events.push({
      id: index + 1,
      type: isFraud ? 'Fraudulent Transaction' : 'Transaction',
      description: `${tx.txn_type}: ${tx.amount} ${tx.currency}${tx.counterparty_id ? ` to/from ${tx.counterparty_id}` : ''}`,
      timestamp: tx.timestamp || new Date().toISOString(),
      color: isFraud ? 'red' : 'blue',
      iconType: 'transaction' as const,
      isAlert: isFraud,
    });
  });

  return events;
}

// ==================== TRANSACTION TRANSFORMERS ====================

/**
 * @deprecated Transaction aggregations no longer exist in backend
 * This function is kept for backward compatibility but returns minimal data
 * Individual transactions should be used directly from API
 */
export function transformApiTransactionToComponent(
  apiTransaction: ApiTransaction,
  users?: Map<number, ApiUser>
): ComponentTransaction {
  console.warn('transformApiTransactionToComponent is deprecated. Backend now returns individual transactions, not aggregations.');
  
  // Return minimal structure to avoid breaking existing code
  return {
    user_id: apiTransaction.user_id,
    // All aggregation fields will be undefined since they don't exist
    displayAmount: apiTransaction.amount 
      ? `₹${apiTransaction.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` 
      : 'N/A',
    displayTxnCount: '1',
    riskLevel: apiTransaction.is_fraud === 1 ? 'High' : 'Low',
  };
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Format timestamp to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format date to human-readable string
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Filter users by search query
 */
export function filterUsersByQuery(users: ComponentUser[], query: string): ComponentUser[] {
  if (!query) return users;
  
  const lowerQuery = query.toLowerCase();
  return users.filter(user => 
    user.name.toLowerCase().includes(lowerQuery) ||
    user.email.toLowerCase().includes(lowerQuery) ||
    user.uin?.toLowerCase().includes(lowerQuery) ||
    user.username?.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Filter users by risk level
 */
export function filterUsersByRiskLevel(users: ComponentUser[], riskLevel: string): ComponentUser[] {
  if (!riskLevel || riskLevel === 'All') return users;
  return users.filter(user => user.riskLevel === riskLevel);
}

/**
 * Filter users by status
 */
export function filterUsersByStatus(users: ComponentUser[], status: string): ComponentUser[] {
  if (!status || status === 'All') return users;
  return users.filter(user => user.kycStatus === status);
}

/**
 * Sort users by field
 */
export function sortUsers(
  users: ComponentUser[], 
  field: 'name' | 'riskScore' | 'createdAt' | 'creditScore',
  direction: 'asc' | 'desc' = 'asc'
): ComponentUser[] {
  const sorted = [...users].sort((a, b) => {
    let comparison = 0;
    
    switch (field) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'riskScore':
        comparison = a.riskScore - b.riskScore;
        break;
      case 'creditScore':
        comparison = (a.creditScore || 0) - (b.creditScore || 0);
        break;
      case 'createdAt':
        comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        break;
    }
    
    return direction === 'asc' ? comparison : -comparison;
  });
  
  return sorted;
}

/**
 * Calculate statistics from users array
 */
export function calculateUserStatistics(users: ComponentUser[]) {
  const total = users.length;
  const verified = users.filter(u => u.kycStatus === 'Verified').length;
  const blacklisted = users.filter(u => u.status === 'Blacklisted').length;
  const highRisk = users.filter(u => u.riskLevel === 'High' || u.riskLevel === 'Critical').length;
  const avgRpsNot = users.reduce((sum, u) => sum + (u.currentRpsNot || 0), 0) / total;
  const avgRps360 = users.reduce((sum, u) => sum + (u.currentRps360 || 0), 0) / total;
  const avgCreditScore = users.filter(u => u.creditScore).reduce((sum, u) => sum + (u.creditScore || 0), 0) / users.filter(u => u.creditScore).length;

  return {
    total,
    verified,
    blacklisted,
    highRisk,
    // RPS scores are in 0-1 format
    avgRpsNot: Math.round(avgRpsNot * 100) / 100, // Keep in 0-1 format with 2 decimal places
    avgRps360: Math.round(avgRps360 * 100) / 100, // Keep in 0-1 format with 2 decimal places
    avgCreditScore: Math.round(avgCreditScore) || 0,
  };
}

/**
 * Calculate transaction statistics from aggregated data
 */
export function calculateTransactionStatistics(transactions: ComponentTransaction[]) {
  const total = transactions.length;
  const highRisk = transactions.filter(t => t.riskLevel === 'High').length;
  const totalAmount = transactions.reduce((sum, t) => sum + (t.total_amount_7d || 0), 0);
  const totalTxnCount = transactions.reduce((sum, t) => sum + (t.txn_count_7d || 0), 0);
  const avgTxnPerUser = totalTxnCount / total;

  return {
    total,
    highRisk,
    totalAmount: Math.round(totalAmount * 100) / 100,
    totalTxnCount,
    avgTxnPerUser: Math.round(avgTxnPerUser * 10) / 10,
    highRiskPercentage: Math.round((highRisk / total) * 100),
  };
}
