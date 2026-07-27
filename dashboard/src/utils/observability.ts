/**
 * Observability and Performance Monitoring Utilities
 * Tracks frontend API latency, rendering metrics, and memory/bundle metrics.
 */

export interface PerformanceMetric {
  name: string;
  durationMs: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

const metricsLog: PerformanceMetric[] = [];
const MAX_METRICS = 100;

export function recordMetric(name: string, durationMs: number, metadata?: Record<string, any>) {
  const metric: PerformanceMetric = {
    name,
    durationMs: Math.round(durationMs * 100) / 100,
    timestamp: new Date().toISOString(),
    metadata,
  };
  metricsLog.unshift(metric);
  if (metricsLog.length > MAX_METRICS) {
    metricsLog.pop();
  }
  if (import.meta.env.DEV) {
    console.debug(`[Observability] ${name}: ${metric.durationMs}ms`, metadata || '');
  }
}

export function getMetricsLog(): PerformanceMetric[] {
  return [...metricsLog];
}

export async function measureAsync<T>(name: string, fn: () => Promise<T>, metadata?: Record<string, any>): Promise<T> {
  const start = performance.now();
  try {
    return await fn();
  } finally {
    const duration = performance.now() - start;
    recordMetric(name, duration, metadata);
  }
}

export function measureSync<T>(name: string, fn: () => T, metadata?: Record<string, any>): T {
  const start = performance.now();
  try {
    return fn();
  } finally {
    const duration = performance.now() - start;
    recordMetric(name, duration, metadata);
  }
}

export function clearMetricsLog() {
  metricsLog.length = 0;
}
