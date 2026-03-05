import { Component, OnDestroy, ViewChild, ElementRef } from "@angular/core";
import { CommonModule } from "@angular/common";
import { PricingService } from "@services/pricing.service";
import { Subject } from "rxjs";
import { takeUntil } from "rxjs/operators";

interface UploadStatus {
  status: "pending" | "processing" | "success" | "failure";
  percent?: number;
  current?: number;
  total?: number;
  message?: string;
  result?: any;
  error?: string;
}

interface ImportResult {
  success: boolean;
  message: string;
  imported_records: number;
  total_in_file?: number;
  invalid_records?: number;
  duplicates_skipped?: number;
  errors?: string[];
}

interface UploadHistory {
  filename: string;
  status: "processing" | "completed" | "failed";
  timestamp: Date;
  result?: ImportResult;
  mainError?: string;
  isExpanded?: boolean;
}

@Component({
  selector: "app-upload",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./upload.component.html",
  styleUrls: ["./upload.component.css"],
})
export class UploadComponent implements OnDestroy {
  @ViewChild("fileInput") fileInput!: ElementRef<HTMLInputElement>;

  selectedFile: File | null = null;
  isUploading = false;
  uploadResponse: any = null;
  errorMessage: string | null = null;
  uploadProgress: UploadStatus | null = null;
  uploadTaskId: string | null = null;
  pollAttempts = 0;
  maxPollAttempts = 60; // 60 seconds max polling (60 * 1 second intervals)
  uploadHistory: UploadHistory[] = []; // Track all uploads
  selectedUploadForDetails: UploadHistory | null = null; // Track selected upload for details view
  showFormatModal = false; // Track CSV format modal state

  private destroy$ = new Subject<void>();

  constructor(private pricingService: PricingService) {}

  toggleFormatModal(): void {
    this.showFormatModal = !this.showFormatModal;
  }

  closeFormatModal(): void {
    this.showFormatModal = false;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  triggerFileSelection(): void {
    if (this.fileInput) {
      this.fileInput.nativeElement.click();
    }
  }

  onFileSelected(event: any): void {
    const files = event.target.files;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
      this.errorMessage = null;
      this.uploadResponse = null;
      this.uploadProgress = null;
      this.uploadTaskId = null;

      // Auto-upload when file is selected
      this.uploadFile();
    }
  }

  uploadFile(): void {
    if (!this.selectedFile) {
      this.errorMessage = "Please select a file first";
      return;
    }

    this.isUploading = true;
    this.errorMessage = null;
    this.uploadProgress = { status: "pending" };

    // Step 1: Submit file for processing
    this.pricingService.uploadCSV(this.selectedFile).subscribe({
      next: (response: any) => {
        // Check if there's an error in the response
        if (response.error) {
          this.errorMessage = response.error;
          this.isUploading = false;
          this.uploadProgress = null;
          return;
        }

        this.uploadTaskId = response.task_id;
        this.uploadProgress = { status: "processing", percent: 0 };
        this.pollAttempts = 0; // Reset poll attempts

        // Step 2: Poll for status
        this.pollUploadStatus();
      },
      error: (error) => {
        const errorMsg =
          error.error?.error || "Upload submission failed. Please try again.";
        this.errorMessage = errorMsg;
        this.isUploading = false;
        this.uploadProgress = null;
      },
    });
  }

  private pollUploadStatus(): void {
    if (!this.uploadTaskId) return;

    this.pricingService.getUploadStatus(this.uploadTaskId).subscribe({
      next: (response: any) => {
        const status: UploadStatus = {
          status: response.status,
          percent: response.percent || 0,
          current: response.current,
          total: response.total,
          message: response.message,
          result: response.result,
          error: response.error,
        };
        this.uploadProgress = status;

        if (status.status === "success") {
          // Upload complete - keep progress bar showing 100%
          const result = status.result || {};

          // Ensure all fields are populated
          this.uploadResponse = {
            success: result.success !== false,
            message: result.message || "Upload processing complete",
            imported_records: result.imported_records || 0,
            total_in_file: result.total_in_file || 0,
            invalid_records: result.invalid_records || 0,
            duplicates_skipped: result.duplicates_skipped || 0,
            errors: result.errors || [],
          };

          // Ensure total_in_file is calculated if missing
          if (
            !this.uploadResponse.total_in_file &&
            this.uploadResponse.imported_records !== undefined
          ) {
            this.uploadResponse.total_in_file =
              this.uploadResponse.imported_records +
              (this.uploadResponse.duplicates_skipped || 0) +
              (this.uploadResponse.invalid_records || 0);
          }

          this.isUploading = false;
          this.selectedFile = null;
          this.uploadTaskId = null;

          // Determine if this is success or failure (all or nothing rule for duplicates)
          const isRejected =
            !this.uploadResponse.success &&
            this.uploadResponse.duplicates_skipped > 0;

          // Update progress bar
          this.uploadProgress = {
            status: isRejected ? "failure" : "success",
            percent: 100,
            current: 100,
            total: 100,
            message: isRejected
              ? "Upload rejected"
              : "Upload completed successfully!",
            result: this.uploadResponse,
          };

          // Add to upload history
          const filename = this.selectedFile
            ? (this.selectedFile as File).name
            : "unknown";
          this.addToUploadHistory(
            filename,
            isRejected ? "failed" : "completed",
            this.uploadResponse,
            isRejected ? this.uploadResponse.message : undefined,
          );
        } else if (status.status === "failure") {
          // Upload failed
          this.errorMessage = status.error || "Upload failed during processing";
          this.isUploading = false;
          this.uploadTaskId = null;

          // Update progress to show failure state
          this.uploadProgress = {
            status: "failure",
            percent: 0,
            error: this.errorMessage,
          };

          // Add to upload history
          const failedFilename = this.selectedFile
            ? (this.selectedFile as File).name
            : "unknown";
          this.addToUploadHistory(
            failedFilename,
            "failed",
            undefined,
            this.errorMessage,
          );
        } else if (
          status.status === "processing" ||
          status.status === "pending"
        ) {
          this.pollAttempts++;

          // Timeout after max attempts
          if (this.pollAttempts >= this.maxPollAttempts) {
            this.errorMessage =
              "Upload processing timeout - please refresh to check status";
            this.isUploading = false;
            this.uploadTaskId = null;
            this.uploadProgress = {
              status: "failure",
              percent: 0,
              error: this.errorMessage,
            };
            return;
          }

          // Still processing, poll again in 1 second
          const delay = this.pollAttempts < 5 ? 500 : 1000; // Faster polling at first
          setTimeout(() => this.pollUploadStatus(), delay);
        } else {
          // Unrecognized status, poll again
          setTimeout(() => this.pollUploadStatus(), 1000);
        }
      },
      error: (error) => {
        const errorMsg =
          error.error?.error ||
          error.message ||
          "Failed to check upload status.";
        this.errorMessage = errorMsg;
        this.isUploading = false;
        this.uploadTaskId = null;
      },
    });
  }

  getProgressPercentage(): number {
    if (!this.uploadProgress) return 0;
    return this.uploadProgress.percent || 0;
  }

  getProgressMessage(): string {
    if (!this.uploadProgress) return "";

    switch (this.uploadProgress.status) {
      case "pending":
        return "Queued for processing...";
      case "processing":
        return (
          this.uploadProgress.message ||
          `Processing... ${this.uploadProgress.percent}%`
        );
      case "success":
        const result = this.uploadResponse;
        if (result) {
          const total = result.total_in_file || result.imported_records;
          const invalid = result.invalid_records || 0;
          const duplicates = result.duplicates_skipped || 0;
          let msg = `✓ Upload completed! ${result.imported_records}/${total} records imported`;
          let details = [];
          if (invalid > 0) details.push(`${invalid} invalid`);
          if (duplicates > 0) details.push(`${duplicates} duplicates`);
          if (details.length > 0) {
            msg += ` (${details.join(", ")} skipped)`;
          }
          return msg;
        }
        return "Upload completed successfully!";
      case "failure":
        const failureResult = this.uploadResponse;
        if (failureResult && failureResult.duplicates_skipped > 0) {
          return `❌ Upload rejected: ${failureResult.duplicates_skipped} duplicate record(s) found (all or nothing rule)`;
        }
        return "❌ Upload processing failed";
      default:
        return "Processing...";
    }
  }

  // Upload history management
  private addToUploadHistory(
    filename: string,
    status: "processing" | "completed" | "failed",
    result?: ImportResult,
    mainError?: string,
  ): void {
    const historyItem: UploadHistory = {
      filename,
      status,
      timestamp: new Date(),
      result,
      mainError,
      isExpanded: false,
    };

    this.uploadHistory.unshift(historyItem); // Add to beginning of array
  }

  onUploadHistoryRowClick(upload: UploadHistory): void {
    // Only allow clicks on failed uploads
    if (upload.status === "failed") {
      if (this.selectedUploadForDetails === upload) {
        this.selectedUploadForDetails = null;
        upload.isExpanded = false;
      } else {
        // Clear previous selection
        if (this.selectedUploadForDetails) {
          this.selectedUploadForDetails.isExpanded = false;
        }
        this.selectedUploadForDetails = upload;
        upload.isExpanded = true;
      }
    }
  }

  isUploadClickable(upload: UploadHistory): boolean {
    return upload.status === "failed";
  }
}
