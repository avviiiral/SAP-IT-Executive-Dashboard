import {CommonModule,DatePipe,DecimalPipe,PercentPipe} from '@angular/common';
import {HttpClient,HttpHeaders} from '@angular/common/http';
import {environment} from '../environments/environment';
import {Component,OnInit,computed,inject,signal} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {NgxEchartsDirective} from 'ngx-echarts';
import {EChartsOption} from 'echarts';
import {DashboardApiService} from './services/dashboard-api.service';
import {BacklogTicket,DashboardBacklog,DashboardBreakdowns,DashboardFilters,DashboardSummary,DashboardTrends} from './models/dashboard.models';
interface UploadBatch{id:string;original_filename:string;upload_type:string;status:string;uploaded_at:string;total_rows:number;inserted_rows:number;updated_rows:number;unchanged_rows:number;rejected_rows:number;error_summary:string;}
@Component({selector:'app-root',standalone:true,imports:[CommonModule,FormsModule,DatePipe,DecimalPipe,PercentPipe,NgxEchartsDirective],templateUrl:'./app.component.html'})
export class AppComponent implements OnInit{
private readonly api=inject(DashboardApiService);
private readonly http=inject(HttpClient);
readonly activeView=signal<'overview'|'upload'>('overview');
readonly uploadUsername=signal('');
readonly uploadPassword=signal('');
readonly uploadType=signal<'INCREMENTAL'|'FULL'>('INCREMENTAL');
readonly snapshotScope=signal('');
readonly selectedFile=signal<File|null>(null);
readonly uploading=signal(false);
readonly uploadMessage=signal('');
readonly uploadError=signal('');
readonly uploadBatches=signal<UploadBatch[]>([]);
readonly uploadBase=environment.apiBaseUrl.replace(/\/$/,'');
readonly loading=signal(false);readonly error=signal('');
readonly summary=signal<DashboardSummary|null>(null);readonly trends=signal<DashboardTrends|null>(null);readonly breakdowns=signal<DashboardBreakdowns|null>(null);readonly backlog=signal<DashboardBacklog|null>(null);readonly appliedFilters=signal<DashboardFilters>({});
readonly filterForm={month:'',date_from:'',date_to:'',plant:'',category:'',subcategory:'',assignee:'',status:'',channel:''};
readonly monthlyOption=computed<EChartsOption>(()=>{const d=this.trends()?.monthly??[];return{tooltip:{trigger:'axis'},legend:{top:0,right:4},grid:{left:8,right:14,top:44,bottom:26,containLabel:true},xAxis:{type:'category',data:d.map(p=>p.month??'')},yAxis:[{type:'value'},{type:'value',min:0,max:1,axisLabel:{formatter:(v:number)=>`${Math.round(v*100)}%`}}],series:[{name:'Tickets',type:'bar',data:d.map(p=>p.tickets),barMaxWidth:28,itemStyle:{color:'#4778c8',borderRadius:[5,5,0,0]}},{name:'Resolution rate',type:'line',yAxisIndex:1,smooth:true,data:d.map(p=>p.resolution_rate),lineStyle:{width:3,color:'#24a58a'}}]};});
readonly weeklyOption=computed<EChartsOption>(()=>{const d=this.trends()?.weekly??[];return{tooltip:{trigger:'axis'},grid:{left:8,right:12,top:12,bottom:26,containLabel:true},xAxis:{type:'category',data:d.map(p=>p.week_start??'')},yAxis:{type:'value'},series:[{type:'line',data:d.map(p=>p.tickets),smooth:true,symbol:'none',lineStyle:{width:3,color:'#4778c8'},areaStyle:{color:'rgba(71,120,200,.10)'}}]};});
readonly channelOption=computed<EChartsOption>(()=>{const d=this.breakdowns()?.by_channel??[];return{tooltip:{trigger:'item'},legend:{bottom:0},series:[{type:'pie',radius:['54%','76%'],label:{show:false},data:d.map(p=>({name:p.name,value:p.tickets}))}]};});
readonly subcategoryBars=computed(()=>this.breakdowns()?.by_subcategory??[]);readonly plantBars=computed(()=>this.breakdowns()?.by_plant??[]);readonly assigneeBars=computed(()=>this.breakdowns()?.by_assignee??[]);readonly attentionRows=computed(()=>(this.backlog()?.results??[]).slice(0,8));readonly hasData=computed(()=>(this.summary()?.total_tickets??0)>0||(this.summary()?.open_backlog??0)>0);
ngOnInit():void{this.refresh();}
showUpload():void{this.activeView.set('upload');this.uploadMessage.set('');this.uploadError.set('');if(this.uploadUsername()&&this.uploadPassword())this.loadUploadHistory();}
showOverview():void{this.activeView.set('overview');}
onFileSelected(event:Event):void{const input=event.target as HTMLInputElement;this.selectedFile.set(input.files?.[0]??null);this.uploadMessage.set('');this.uploadError.set('');}
loadUploadHistory():void{
 const headers=this.authHeaders();
 this.http.get<UploadBatch[]>(`${this.uploadBase}/uploads/`,{headers}).subscribe({
  next:rows=>this.uploadBatches.set(rows),
  error:e=>this.uploadError.set(e.status===401||e.status===403?'Authentication failed or this account is not a Django staff user.':'Could not load upload history.')
 });
}
submitUpload():void{
 const file=this.selectedFile();
 if(!file){this.uploadError.set('Choose a CSV, XLSX or XLSM file first.');return;}
 if(!this.uploadUsername().trim()||!this.uploadPassword()){this.uploadError.set('Enter your Django staff username and password.');return;}
 if(this.uploadType()==='FULL'&&!this.snapshotScope().trim()){this.uploadError.set('Snapshot scope is required for a full report.');return;}
 const form=new FormData();form.append('file',file);form.append('upload_type',this.uploadType());
 if(this.uploadType()==='FULL')form.append('snapshot_scope',this.snapshotScope().trim());
 this.uploading.set(true);this.uploadError.set('');this.uploadMessage.set('');
 this.http.post<UploadBatch>(`${this.uploadBase}/uploads/import/`,form,{headers:this.authHeaders()}).subscribe({
  next:batch=>{this.uploading.set(false);this.uploadMessage.set(`Import ${batch.status.toLowerCase().replaceAll('_',' ')}. ${batch.inserted_rows} inserted, ${batch.updated_rows} updated, ${batch.unchanged_rows} unchanged, ${batch.rejected_rows} rejected.`);this.selectedFile.set(null);this.loadUploadHistory();this.refresh();},
  error:e=>{this.uploading.set(false);const detail=e.error?.error??e.error?.detail??(typeof e.error==='string'?e.error:'');this.uploadError.set(e.status===401||e.status===403?'Authentication failed. Use a Django staff/superuser account.':detail||'Upload failed. Check the file format and required columns.');}
 });
}
private authHeaders():HttpHeaders{return new HttpHeaders({Authorization:'Basic '+btoa(`${this.uploadUsername()}:${this.uploadPassword()}`)});}
refresh():void{this.loading.set(true);this.error.set('');this.api.loadDashboard(this.appliedFilters()).subscribe({next:d=>{this.summary.set(d.summary);this.trends.set(d.trends);this.breakdowns.set(d.breakdowns);this.backlog.set(d.backlog);this.loading.set(false);},error:(e:unknown)=>{const c=e as{status?:number;message?:string;error?:{detail?:string}};this.error.set(c.status===0?'Could not reach the API. Check that Django is running and the API URL is correct.':c.error?.detail??c.message??'Dashboard data could not be loaded.');this.loading.set(false);}});}
applyFilters():void{const clean:DashboardFilters={};(Object.keys(this.filterForm)as(keyof typeof this.filterForm)[]).forEach(k=>{const v=this.filterForm[k].trim();if(v)clean[k]=v;});this.appliedFilters.set(clean);this.refresh();}
clearFilters():void{(Object.keys(this.filterForm)as(keyof typeof this.filterForm)[]).forEach(k=>this.filterForm[k]='');this.appliedFilters.set({});this.refresh();}
get maxSubcategory():number{return Math.max(1,...this.subcategoryBars().map(x=>x.tickets??0));}get maxPlant():number{return Math.max(1,...this.plantBars().map(x=>x.tickets??0));}get maxAssignee():number{return Math.max(1,...this.assigneeBars().map(x=>x.tickets??0));}
barWidth(v:number|undefined,m:number):string{return `${Math.max(2,((v??0)/m)*100)}%`;}statusClass(t:BacklogTicket):string{return t.overdue?'status status--overdue':t.status.toLowerCase()==='on_hold'?'status status--hold':'status status--open';}
}
