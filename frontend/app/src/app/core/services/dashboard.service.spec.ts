import {HttpClient} from '@angular/common/http';
import {TestBed} from '@angular/core/testing';
import {DashboardService} from './dashboard.service';

describe('DashboardService',()=>{
  it('consulta el resumen del tenant',()=>{
    const http=jasmine.createSpyObj<HttpClient>('HttpClient',['get']);
    TestBed.configureTestingModule({providers:[DashboardService,{provide:HttpClient,useValue:http}]});
    TestBed.inject(DashboardService).getSummary();
    expect(http.get).toHaveBeenCalledWith('/api/dashboard');
  });
});
