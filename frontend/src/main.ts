import {bootstrapApplication} from '@angular/platform-browser';
import {provideHttpClient} from '@angular/common/http';
import {provideEcharts} from 'ngx-echarts';
import {AppComponent} from './app/app.component';
bootstrapApplication(AppComponent,{providers:[provideHttpClient(),provideEcharts()]}).catch((error:unknown)=>console.error(error));
