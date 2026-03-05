import { Injectable } from "@angular/core";
import { HttpClient, HttpParams } from "@angular/common/http";
import { Observable, takeUntil, EMPTY } from "rxjs";
import { webSocket } from "rxjs/webSocket";
import { environment } from "@environments/environment";
import {
  PricingRecord,
  SearchFilters,
  PaginatedResponse,
  UploadResponse,
  Statistics,
  CountryStats,
} from "@models/index";

@Injectable({
  providedIn: "root",
})
export class PricingService {
  private apiUrl = `${environment.apiUrl}/pricing`;
  private wsUrl = `${environment.apiUrl?.replace(/^http/, "ws")}/ws`;

  constructor(private http: HttpClient) {}

  /**
   * Helper method to build HTTP parameters from filter object
   */
  private buildParams(
    filters: SearchFilters,
    page: number,
    perPage: number,
  ): HttpParams {
    return new HttpParams({
      fromObject: {
        page: page.toString(),
        per_page: perPage.toString(),
        ...(Object.fromEntries(
          Object.entries(filters).filter(
            ([_, value]) => value != null && value !== "",
          ),
        ) as Record<string, string>),
      },
    });
  }

  /**
   * Upload CSV file with pricing data (async)
   * Returns task_id for tracking progress
   */
  public uploadCSV(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.http.post<UploadResponse>(
      `${this.apiUrl}/upload_csv`,
      formData,
    );
  }

  /**
   * Get upload task status
   */
  public getUploadStatus(taskId: string) {
    return this.http.get<UploadResponse>(
      `${this.apiUrl}/upload_status/${taskId}`,
    );
  }

  /**
   * WebSocket connection for real-time upload status updates
   * Automatically connects and receives updates until task completes or connection closes
   */
  public watchUploadStatus(taskId: string, cancelSignal?: Observable<void>) {
    const wsUploadUrl = `${this.wsUrl}/upload-status/${taskId}`;
    return webSocket<UploadResponse>(wsUploadUrl).pipe(
      takeUntil(cancelSignal || EMPTY),
    );
  }

  /**
   * Search pricing records with filters
   */
  public searchRecords(
    filters: SearchFilters,
    page: number = 1,
    perPage: number = 50,
  ) {
    const params = this.buildParams(filters, page, perPage);
    return this.http.get<PaginatedResponse<PricingRecord>>(
      `${this.apiUrl}/search`,
      {
        params,
      },
    );
  }

  /**
   * Get a specific pricing record
   */
  public getRecord(recordId: string) {
    return this.http.get<PricingRecord>(`${this.apiUrl}/record/${recordId}`);
  }

  /**
   * Update a pricing record
   */
  public updateRecord(recordId: string, data: any) {
    return this.http.put<PricingRecord>(
      `${this.apiUrl}/record/${recordId}`,
      data,
    );
  }

  /**
   * Delete a pricing record
   */
  public deleteRecord(recordId: string) {
    return this.http.delete<void>(`${this.apiUrl}/record/${recordId}`);
  }
}
