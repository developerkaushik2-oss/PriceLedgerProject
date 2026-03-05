import { Component, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { ReactiveFormsModule, FormGroup, FormBuilder } from "@angular/forms";
import { FormsModule } from "@angular/forms";
import { PricingService } from "@services/pricing.service";
import { PricingRecord, SearchFilters, PaginatedResponse } from "@models/index";

@Component({
  selector: "app-search",
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: "./search.component.html",
  styleUrls: ["./search.component.css"],
})
export class SearchComponent implements OnInit {
  searchForm!: FormGroup;
  editForm!: FormGroup;
  results: PaginatedResponse<PricingRecord> | null = null;
  isLoading = false;
  errorMessage: string | null = null;
  editingRecord: any = null;
  currentPage = 1;
  itemsPerPage = 10;
  Math = Math;

  constructor(
    private pricingService: PricingService,
    private fb: FormBuilder,
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.initializeEditForm();
    this.search();
  }

  private initializeEditForm(): void {
    this.editForm = this.fb.group({
      price: [""],
      change_reason: [""],
    });
  }

  initializeForm(): void {
    this.searchForm = this.fb.group({
      store_id: [""],
      sku: [""],
      product_name: [""],
      country: [""],
      price_min: [""],
      price_max: [""],
      date_from: [""],
      date_to: [""],
    });
  }

  public search() {
    this.isLoading = true;
    this.errorMessage = null;
    // Send form values directly to backend, let backend apply filters
    const formValues = this.searchForm.value;
    this.pricingService
      .searchRecords(formValues, this.currentPage, this.itemsPerPage)
      .subscribe({
        next: (data: PaginatedResponse<PricingRecord>) => {
          this.results = data;
          this.isLoading = false;
        },
        error: (error) => {
          this.errorMessage = error.error?.error || "Search failed";
          this.isLoading = false;
        },
      });
  }

  clearFilters(): void {
    this.searchForm.reset();
    this.currentPage = 1;
    this.itemsPerPage = 10;
    this.search();
  }

  changePageSize(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.itemsPerPage = parseInt(target.value, 10);
    this.currentPage = 1;
    this.search();
  }

  nextPage(): void {
    if (this.results && this.currentPage < this.results.pages) {
      this.currentPage++;
      this.search();
    }
  }

  previousPage(): void {
    if (this.results && this.currentPage > 1) {
      this.currentPage--;
      this.search();
    }
  }

  editRecord(record: PricingRecord): void {
    this.editingRecord = { ...record };
    this.editForm.patchValue({
      price: record.price,
      change_reason: "",
    });
  }

  saveEdit(): void {
    if (!this.editingRecord) return;
    const editData = {
      price: this.editForm.get("price")?.value || this.editingRecord.price,
      change_reason: this.editForm.get("change_reason")?.value,
    };
    this.pricingService
      .updateRecord(this.editingRecord.id, editData)
      .subscribe({
        next: () => {
          alert("Record updated successfully");
          this.editingRecord = null;
          this.editForm.reset();
          this.search();
        },
        error: (error) => {
          this.errorMessage = error.error?.error || "Update failed";
        },
      });
  }

  cancelEdit(): void {
    this.editingRecord = null;
  }

  deleteRecord(record: PricingRecord): void {
    if (!confirm("Are you sure you want to delete this record?")) return;
    this.pricingService.deleteRecord(record.id).subscribe({
      next: () => {
        alert("Record deleted successfully");
        this.search();
      },
      error: (error) => {
        this.errorMessage = error.error?.error || "Delete failed";
      },
    });
  }
}
