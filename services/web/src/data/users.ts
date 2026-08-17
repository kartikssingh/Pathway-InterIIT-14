// Shared user data for the application
// Updated to match API reference schema

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

export interface User {
  user_id: number; // Primary key (matches API)
  name: string; // Display name (derived from username or email)
  email: string;
  createdAt: string; // ISO 8601 format
  status: "Verified" | "Unverified" | "Blacklisted"; // User verification status (for list page)
  statusColor: string;
  accountStatus: "Active" | "Suspended" | "Closed" | "Under Investigation"; // Account active status (for detail page)
  image?: string; // Deprecated - use profilePic
  profilePic?: string; // URL/path to user's profile picture
  riskScore: number; // current_rps_not (0-1 format)
  riskLevel: string; // Derived from risk_category or current_rps_360
  kycStatus: "Verified" | "Pending" | "Rejected" | "Under Review";
  lastLogin: string;
  accountAge: string;
  events: UserEvent[];
  // API fields matching backend schema
  uin?: string; // User Identification Number
  username?: string;
  phone?: string;
  occupation?: string;
  dateOfBirth?: string;
  address?: string;
  annualIncome?: number;
  creditScore?: number; // Range: 300-900
  blacklisted: boolean;
  currentRpsNot?: number; // RPS NOT score (0-1 format)
  currentRps360?: number; // RPS 360 score (0-1 format)
  lastRpsCalculation?: string;
  riskCategory?: string; // low/medium/high/critical
}

// Dummy data matching API reference table
// Based on API Reference: Users with user_id 1001-1010
export const usersData: User[] = [
  {
    user_id: 1001,
    username: "john_doe",
    name: "john_doe",
    email: "john.doe@example.com",
    phone: "9876543210",
    uin: "AAAA1234567890BBBB12",
    createdAt: "2024-01-15T10:30:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.15, // current_rps_not
    currentRpsNot: 0.15,
    currentRps360: 0.22,
    riskLevel: "Low",
    riskCategory: "low",
    kycStatus: "Verified",
    creditScore: 750,
    blacklisted: false,
    lastLogin: "2024-12-06T14:00:00",
    accountAge: "11 Months",
    lastRpsCalculation: "2024-12-06T14:00:00",
    events: [],
  },
  {
    user_id: 1002,
    username: "jane_smith",
    name: "jane_smith",
    email: "jane.smith@example.com",
    phone: "9876543211",
    createdAt: "2024-02-20T11:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.35, // current_rps_not
    currentRpsNot: 0.35,
    currentRps360: 0.52,
    riskLevel: "Medium",
    riskCategory: "medium",
    kycStatus: "Verified",
    creditScore: 680,
    blacklisted: false,
    lastLogin: "2024-12-06T12:00:00",
    accountAge: "10 Months",
    events: [],
  },
  {
    user_id: 1003,
    username: "robert_johnson",
    name: "robert_johnson",
    email: "robert.johnson@example.com",
    phone: "9876543212",
    createdAt: "2024-03-10T09:00:00",
    status: "Unverified",
    statusColor: "bg-yellow-100 text-yellow-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.65, // current_rps_not
    currentRpsNot: 0.65,
    currentRps360: 0.78,
    riskLevel: "High",
    riskCategory: "high",
    kycStatus: "Pending",
    creditScore: 550,
    blacklisted: false,
    lastLogin: "2024-12-05T15:45:00",
    accountAge: "9 Months",
    events: [
      {
        id: 1,
        type: "Fraud Alert",
        description: "Suspicious transaction of INR 450000.00 detected",
        timestamp: "2024-12-05T15:45:00",
        color: "red",
        iconType: "alert",
        isAlert: true,
      },
    ],
  },
  {
    user_id: 1004,
    username: "emily_brown",
    name: "emily_brown",
    email: "emily.brown@example.com",
    phone: "9876543213",
    createdAt: "2024-01-30T10:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.08, // current_rps_not
    currentRpsNot: 0.08,
    currentRps360: 0.12,
    riskLevel: "Low",
    riskCategory: "low",
    kycStatus: "Verified",
    creditScore: 820,
    blacklisted: false,
    lastLogin: "2024-12-06T10:00:00",
    accountAge: "11 Months",
    events: [],
  },
  {
    user_id: 1005,
    username: "michael_wilson",
    name: "michael_wilson",
    email: "michael.wilson@example.com",
    phone: "9876543214",
    createdAt: "2024-04-05T14:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.45, // current_rps_not
    currentRpsNot: 0.45,
    currentRps360: 0.61,
    riskLevel: "Medium",
    riskCategory: "medium",
    kycStatus: "Verified",
    creditScore: 620,
    blacklisted: false,
    lastLogin: "2024-12-06T08:00:00",
    accountAge: "8 Months",
    events: [],
  },
  {
    user_id: 1006,
    username: "sarah_davis",
    name: "sarah_davis",
    email: "sarah.davis@example.com",
    phone: "9876543215",
    createdAt: "2024-05-15T11:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.20, // current_rps_not
    currentRpsNot: 0.20,
    currentRps360: 0.30,
    riskLevel: "Low",
    riskCategory: "low",
    kycStatus: "Verified",
    creditScore: 710,
    blacklisted: false,
    lastLogin: "2024-12-06T16:00:00",
    accountAge: "7 Months",
    events: [],
  },
  {
    user_id: 1007,
    username: "david_martinez",
    name: "david_martinez",
    email: "david.martinez@example.com",
    phone: "9876543216",
    createdAt: "2024-06-01T09:00:00",
    status: "Blacklisted",
    statusColor: "bg-red-100 text-red-700",
    accountStatus: "Suspended",
    profilePic: undefined,
    riskScore: 0.85, // current_rps_not
    currentRpsNot: 0.85,
    currentRps360: 0.92,
    riskLevel: "Critical",
    riskCategory: "critical",
    kycStatus: "Rejected",
    creditScore: 400,
    blacklisted: true,
    lastLogin: "2024-11-20T10:00:00",
    accountAge: "6 Months",
    events: [
      {
        id: 1,
        type: "Account Suspended",
        by: "Compliance Team",
        description: "Account suspended due to fraudulent activity",
        timestamp: "2024-11-20T10:00:00",
        color: "red",
        iconType: "alert",
        isAlert: true,
      },
      {
        id: 2,
        type: "Fraud Alert",
        description: "Suspicious transaction of USD 980000.00 detected",
        timestamp: "2024-11-20T09:45:00",
        color: "red",
        iconType: "alert",
        isAlert: true,
      },
    ],
  },
  {
    user_id: 1008,
    username: "lisa_anderson",
    name: "lisa_anderson",
    email: "lisa.anderson@example.com",
    phone: "9876543217",
    createdAt: "2024-07-10T10:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.10, // current_rps_not
    currentRpsNot: 0.10,
    currentRps360: 0.15,
    riskLevel: "Low",
    riskCategory: "low",
    kycStatus: "Verified",
    creditScore: 780,
    blacklisted: false,
    lastLogin: "2024-12-06T14:30:00",
    accountAge: "5 Months",
    events: [],
  },
  {
    user_id: 1009,
    username: "james_taylor",
    name: "james_taylor",
    email: "james.taylor@example.com",
    phone: "9876543218",
    createdAt: "2024-08-15T11:00:00",
    status: "Unverified",
    statusColor: "bg-yellow-100 text-yellow-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.60, // current_rps_not
    currentRpsNot: 0.60,
    currentRps360: 0.75,
    riskLevel: "High",
    riskCategory: "high",
    kycStatus: "Pending",
    creditScore: 520,
    blacklisted: false,
    lastLogin: "2024-12-05T13:00:00",
    accountAge: "4 Months",
    events: [],
  },
  {
    user_id: 1010,
    username: "amanda_thomas",
    name: "amanda_thomas",
    email: "amanda.thomas@example.com",
    phone: "9876543219",
    createdAt: "2024-09-20T10:00:00",
    status: "Verified",
    statusColor: "bg-green-100 text-green-700",
    accountStatus: "Active",
    profilePic: undefined,
    riskScore: 0.18, // current_rps_not
    currentRpsNot: 0.18,
    currentRps360: 0.24,
    riskLevel: "Low",
    riskCategory: "low",
    kycStatus: "Verified",
    creditScore: 730,
    blacklisted: false,
    lastLogin: "2024-12-06T11:00:00",
    accountAge: "3 Months",
    events: [],
  },
];

export const getUserById = (userId: number): User | undefined => {
  return usersData.find((user) => user.user_id === userId);
};
