import {HttpClient,HttpParams} from '@angular/common/http';
import {Injectable,inject} from '@angular/core';
import {forkJoin,Observable} from 'rxjs';
import {environment} from '../../environments/environment';
import {DashboardBacklog,DashboardBreakdowns,DashboardFilters,DashboardSummary,DashboardTrends} from '../models/dashboard.models';
@Injectable({providedIn:'root'}) export class DashboardApiService {
 private readonly http=inject(HttpClient);private readonly base=environment.apiBaseUrl.replace(/\\/$/,'');
 loadDashboard(filters:DashboardFilters):Observable<{summary:DashboardSummary;trends:DashboardTrends;breakdowns:DashboardBreakdowns;backlog:DashboardBacklog}>{const params=this.toParams(filters);return forkJoin({summary:this.http.get<DashboardSummary>(`${this.base}/analytics/summary/`,{params}),trends:this.http.get<DashboardTrends>(`${this.base}/analytics/trends/`,{params}),breakdowns:this.http.get<DashboardBreakdowns>(`${this.base}/analytics/breakdowns/`,{params}),backlog:this.http.get<DashboardBacklog>(`${this.base}/analytics/backlog/`,{params:params.set('limit','100')})});}
 private toParams(filters:DashboardFilters):HttpParams{let params=new HttpParams();Object.entries(filters).forEach(([key,value])=>{if(value?.trim())params=params.set(key,value.trim());});return params;}
}
