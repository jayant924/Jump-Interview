import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';

const API_BASE = 'http://localhost:8000';

export interface Summary {
  total_dealers: number;
  total_revenue: number;
  total_cost?: number;
  total_profit?: number | null;
  avg_margin_pct?: number | null;
  total_units?: number;
  validation_issues_count?: number;
  issues_count: number;
  issues_by_severity?: Record<string, number>;
  dealers_with_issues: number;
  outliers_count?: number;
  outliers_for_human_review?: number;
  market_impact?: {
    signals_applied: number;
    revenue_delta_pct: number;
    revenue_impact: number;
    impact_notes: { signal: string; effect_revenue_pct: number; description: string }[];
  };
}

export interface Issue {
  dealer_id: string;
  code: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
}

export interface Dealer {
  dealer_id: string;
  dealer_name: string;
  region?: string;
  state?: string;
  revenue: number;
  cost?: number;
  margin_pct?: number;
  units_sold?: number;
  stock_turnover_days?: number;
  order_count?: number;
  last_order_date?: string;
  report_date?: string;
  status?: string;
  issue_count: number;
  revenue_vs_state?: number | null;
}

export interface Outlier {
  dealer_id: string;
  metric: string;
  value: number;
  bound_low: number;
  bound_high: number;
  z_score: number;
  confidence_score: number;
  reason: string;
  state_deviation_flag?: boolean;
}

export interface Results {
  generated_at: string;
  summary: Summary;
  issues: Issue[];
  dealers: Dealer[];
  outliers_for_human_review?: Outlier[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  getResults(): Observable<Results | { error: string }> {
    return this.http.get<Results | { error: string }>(`${API_BASE}/api/results`).pipe(
      catchError(() => of({ error: 'Cannot reach API. Start the backend with: uvicorn api.main:app --reload' }))
    );
  }

  getSummary(): Observable<Summary | { error: string }> {
    return this.http.get<Summary | { error: string }>(`${API_BASE}/api/summary`).pipe(
      catchError(() => of({ error: 'API unavailable' }))
    );
  }

  getIssues(): Observable<Issue[]> {
    return this.http.get<Issue[]>(`${API_BASE}/api/issues`).pipe(
      catchError(() => of([]))
    );
  }

  getDealers(): Observable<Dealer[]> {
    return this.http.get<Dealer[]>(`${API_BASE}/api/dealers`).pipe(
      catchError(() => of([]))
    );
  }

  refresh(): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${API_BASE}/api/refresh`, {});
  }

  getOutliers(): Observable<Outlier[]> {
    return this.http.get<Outlier[]>(`${API_BASE}/api/outliers`).pipe(
      catchError(() => of([]))
    );
  }
}
