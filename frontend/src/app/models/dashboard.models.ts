export interface DashboardFilters {month?:string;date_from?:string;date_to?:string;plant?:string;category?:string;subcategory?:string;assignee?:string;status?:string;channel?:string;}
export interface DashboardSummary {reporting_start_date:string;as_of_date:string;total_tickets:number;resolved_tickets:number;resolution_rate:number;open_backlog:number;oldest_open_age_days:number;average_resolution_days:number;median_resolution_days:number;resolved_within_one_day_rate:number;average_tickets_per_week:number;weeks_in_reporting_data:number;}
export interface TrendPoint {month?:string;week_start?:string;tickets:number;resolved?:number;resolution_rate?:number;}
export interface DashboardTrends {monthly:TrendPoint[];weekly:TrendPoint[];}
export interface BreakdownPoint {name:string;tickets?:number;resolved?:number;average_resolution_days?:number;}
export interface DashboardBreakdowns {by_subcategory:BreakdownPoint[];by_plant:BreakdownPoint[];by_channel:BreakdownPoint[];by_assignee:BreakdownPoint[];average_resolution_by_subcategory:BreakdownPoint[];}
export interface BacklogTicket {incident_number:string;title:string;status:string;status_label:string;category:string;subcategory:string;plant:string;assignee:string;created_date:string|null;due_date:string|null;age_days:number|null;overdue:boolean;legacy:boolean;}
export interface DashboardBacklog {as_of_date:string;total_open:number;older_than_30_days:number;older_than_90_days:number;overdue_count:number;results:BacklogTicket[];limit:number;}
