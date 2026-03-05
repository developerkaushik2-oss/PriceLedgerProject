import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { environment } from "@environments/environment";
import { Statistics, CountryStats } from "@models/index";

@Injectable({
  providedIn: "root",
})
export class StatsService {
  private apiUrl = `${environment.apiUrl}/stats`;

  constructor(private http: HttpClient) {}

  /**
   * Get general statistics overview
   */
  getOverview(): Observable<Statistics> {
    return this.http.get<Statistics>(`${this.apiUrl}/overview`);
  }

  /**
   * Get statistics grouped by country
   */
  getByCountry(): Observable<CountryStats[]> {
    return this.http.get<CountryStats[]>(`${this.apiUrl}/by_country`);
  }
}
