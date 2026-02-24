import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Summary, Issue, Dealer, Results, Outlier } from '../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit {
  summary: Summary | null = null;
  issues: Issue[] = [];
  dealers: Dealer[] = [];
  outliers: Outlier[] = [];
  generatedAt: string | null = null;
  error: string | null = null;
  loading = true;
  refreshing = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = null;
    this.api.getResults().subscribe((data) => {
      this.loading = false;
      if ('error' in data) {
        this.error = data.error;
        this.summary = null;
        this.issues = [];
        this.dealers = [];
        this.outliers = [];
        this.generatedAt = null;
        return;
      }
      const res = data as Results;
      this.summary = res.summary;
      this.issues = res.issues;
      this.dealers = res.dealers;
      this.outliers = res.outliers_for_human_review || [];
      this.generatedAt = res.generated_at;
    });
  }

  refresh(): void {
    this.refreshing = true;
    this.api.refresh().subscribe((r) => {
      this.refreshing = false;
      if (r.status === 'ok') this.load();
      else this.error = r.message;
    });
  }

  severityClass(severity: string): string {
    return `severity-${severity}`;
  }

  formatDate(iso: string): string {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleDateString();
    } catch {
      return iso;
    }
  }

  formatCurrency(n: number): string {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
  }

  regionOrState(d: Dealer): string {
    return d.region ?? d.state ?? '—';
  }
}
