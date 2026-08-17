"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownLeft, DollarSign, AlertCircle, CheckCircle } from "lucide-react";
import { useState, useMemo, useEffect } from "react";
import { useTransactions } from "@/hooks/useApi";

export default function TransactionsPage() {
  const [fraudFilter, setFraudFilter] = useState<"all" | "fraud" | "normal">("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  
  // Fetch transactions
  const apiFilters = useMemo(() => ({
    limit: 200
  }), []);
  
  const { transactions, loading, error, refetch } = useTransactions(apiFilters);

  // Console log for debugging - clearly shows what we're getting
  useEffect(() => {
    console.log('========================================');
    console.log('🔄 TRANSACTIONS TAB DATA:');
    console.log('========================================');
    console.log('Loading:', loading);
    console.log('Error:', error);
    console.log('Raw transactions received:', transactions);
    console.log('Number of transactions:', transactions?.length || 0);
    
    if (transactions && transactions.length > 0) {
      console.log('First transaction sample:', transactions[0]);
      console.log('Transaction keys:', Object.keys(transactions[0]));
      
      // Log unique transaction types
      const types = [...new Set(transactions.map(tx => tx.txn_type))];
      console.log('Unique transaction types:', types);
      
      // Log fraud statistics
      const fraudCount = transactions.filter(tx => tx.is_fraud === 1).length;
      console.log('Fraud transactions count:', fraudCount);
      console.log('Normal transactions count:', transactions.length - fraudCount);
    }
    console.log('========================================');
  }, [transactions, loading, error]);

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    if (!transactions) return [];
    
    let filtered = [...transactions];
    
    // Filter by fraud status
    if (fraudFilter === "fraud") {
      filtered = filtered.filter(tx => tx.is_fraud === 1);
    } else if (fraudFilter === "normal") {
      filtered = filtered.filter(tx => tx.is_fraud === 0);
    }
    
    // Filter by transaction type
    if (typeFilter !== "all") {
      filtered = filtered.filter(tx => tx.txn_type?.toLowerCase() === typeFilter.toLowerCase());
    }
    
    return filtered;
  }, [transactions, fraudFilter, typeFilter]);
  
  // Get unique transaction types for filter
  const transactionTypes = useMemo(() => {
    if (!transactions) return [];
    const types = new Set(transactions.map(tx => tx.txn_type).filter(Boolean));
    return Array.from(types);
  }, [transactions]);
  
  // Calculate statistics
  const stats = useMemo(() => {
    if (!filteredTransactions) return { 
      total: 0, 
      totalVolume: 0, 
      fraudCount: 0, 
      fraudVolume: 0,
      avgAmount: 0 
    };
    
    const fraudTxs = filteredTransactions.filter(tx => tx.is_fraud === 1);
    const totalVolume = filteredTransactions.reduce((sum, tx) => sum + (tx.amount || 0), 0);
    const fraudVolume = fraudTxs.reduce((sum, tx) => sum + (tx.amount || 0), 0);
    
    return {
      total: filteredTransactions.length,
      totalVolume,
      fraudCount: fraudTxs.length,
      fraudVolume,
      avgAmount: filteredTransactions.length > 0 ? totalVolume / filteredTransactions.length : 0,
    };
  }, [filteredTransactions]);
  
  if (error) {
    return (
      <div className="p-8">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error loading transactions</h3>
          <p className="text-gray-600 mb-4">{error.message}</p>
          <button 
            onClick={refetch}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Page Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Transactions</h2>
        <p className="text-sm text-gray-500 mb-4">Individual transaction records</p>
        <div className="border-t border-gray-200" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Transactions</p>
              <p className="text-2xl font-semibold">{stats.total}</p>
              <p className="text-xs text-gray-400 mt-1">Showing {filteredTransactions.length} filtered</p>
            </div>
            <DollarSign className="h-8 w-8 text-blue-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Volume</p>
              <p className="text-2xl font-semibold">
                ₹{stats.totalVolume.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Avg: ₹{stats.avgAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
            </div>
            <ArrowUpRight className="h-8 w-8 text-green-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Fraudulent</p>
              <p className="text-2xl font-semibold text-red-600">{stats.fraudCount}</p>
              <p className="text-xs text-gray-400 mt-1">
                {stats.total > 0 ? ((stats.fraudCount / stats.total) * 100).toFixed(1) : 0}% of total
              </p>
            </div>
            <AlertCircle className="h-8 w-8 text-red-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Fraud Volume</p>
              <p className="text-2xl font-semibold text-red-600">
                ₹{stats.fraudVolume.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {stats.totalVolume > 0 ? ((stats.fraudVolume / stats.totalVolume) * 100).toFixed(1) : 0}% of volume
              </p>
            </div>
            <ArrowDownLeft className="h-8 w-8 text-orange-500" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <Select value={fraudFilter} onValueChange={(value) => setFraudFilter(value as "all" | "fraud" | "normal")}>
          <SelectTrigger className="w-auto min-w-[150px] bg-[#FFFFFF] hover:bg-gray-50 border-black rounded-full h-9 px-4">
            <SelectValue placeholder="Fraud Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Transactions</SelectItem>
            <SelectItem value="fraud">Fraudulent Only</SelectItem>
            <SelectItem value="normal">Normal Only</SelectItem>
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-auto min-w-[150px] bg-[#FFFFFF] hover:bg-gray-50 border-black rounded-full h-9 px-4">
            <SelectValue placeholder="Transaction Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {transactionTypes.map(type => (
              <SelectItem key={type} value={type}>{type}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        <div className="ml-auto text-sm text-gray-500 flex items-center">
          Showing {filteredTransactions.length} of {transactions?.length || 0} transactions
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg overflow-hidden border border-gray-200">
        <Table>
          <TableHeader className="[&_tr]:border-0">
            <TableRow className="bg-gray-50 border-0">
              <TableHead className="font-semibold text-gray-900">Transaction ID</TableHead>
              <TableHead className="font-semibold text-gray-900">User ID</TableHead>
              <TableHead className="font-semibold text-gray-900">Amount</TableHead>
              <TableHead className="font-semibold text-gray-900">Currency</TableHead>
              <TableHead className="font-semibold text-gray-900">Type</TableHead>
              <TableHead className="font-semibold text-gray-900">Counterparty</TableHead>
              <TableHead className="font-semibold text-gray-900">Status</TableHead>
              <TableHead className="font-semibold text-gray-900">Timestamp</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
                    <span className="ml-2">Loading transactions...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredTransactions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                  No transactions found
                </TableCell>
              </TableRow>
            ) : (
              filteredTransactions.map((tx) => (
                <TableRow key={tx.transaction_id} className="hover:bg-gray-50 border-b border-gray-200 last:border-b-0">
                  <TableCell>
                    <div className="font-mono text-sm text-gray-700">
                      #{tx.transaction_id}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <span className="font-medium">User {tx.user_id}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="font-semibold text-gray-900">
                      {tx.amount.toLocaleString('en-IN', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                      })}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {tx.currency || 'INR'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="secondary"
                      className="bg-blue-100 text-blue-700 border-0 font-normal"
                    >
                      {tx.txn_type || 'Unknown'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm text-gray-600">
                      {tx.counterparty_id ? `User ${tx.counterparty_id}` : '-'}
                    </div>
                  </TableCell>
                  <TableCell>
                    {tx.is_fraud === 1 ? (
                      <div className="flex items-center gap-1.5">
                        <AlertCircle className="h-4 w-4 text-red-600" />
                        <Badge 
                          variant="secondary"
                          className="bg-red-100 text-red-700 border-0 font-medium"
                        >
                          FRAUD
                        </Badge>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <Badge 
                          variant="secondary"
                          className="bg-green-100 text-green-700 border-0 font-normal"
                        >
                          Normal
                        </Badge>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-gray-700 text-sm">
                    {tx.timestamp ? new Date(tx.timestamp).toLocaleString('en-IN', { 
                      month: 'short', 
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    }) : 'N/A'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
