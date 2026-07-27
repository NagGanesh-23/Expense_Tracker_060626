import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSummary, fetchTransactions, triggerDataSync } from './apiClient';
import type { ValidatedSummaryResponse, ValidatedTransactionsResponse } from './apiClient';

export function useSummaryQuery(filters: Record<string, any> = {}, options = {}) {
  return useQuery<ValidatedSummaryResponse, Error>({
    queryKey: ['summary', filters],
    queryFn: () => fetchSummary(filters),
    staleTime: 60 * 1000, // 60 seconds matching server TTL
    ...options,
  });
}

export function useTransactionsQuery(filters: Record<string, any> = {}, options = {}) {
  return useQuery<ValidatedTransactionsResponse, Error>({
    queryKey: ['transactions', filters],
    queryFn: () => fetchTransactions(filters),
    staleTime: 60 * 1000,
    ...options,
  });
}

export function useSyncMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerDataSync,
    onSuccess: () => {
      // Invalidate all queries to trigger a fresh fetch from SQLite / server
      queryClient.invalidateQueries({ queryKey: ['summary'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}
