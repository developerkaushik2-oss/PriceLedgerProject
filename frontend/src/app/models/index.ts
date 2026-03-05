export interface PricingRecord {
  id: string;
  store_id: string;
  store_name: string;
  country: string;
  sku: string;
  product_name: string;
  price: number;
  currency: string;
  date: string;
  updated_at: string;
  updated_by: string;
  source_file: string;
}

export interface SearchFilters {
  store_id?: string;
  sku?: string;
  product_name?: string;
  price_min?: number;
  price_max?: number;
  date_from?: string;
  date_to?: string;
  country?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  pages: number;
  current_page: number;
  per_page: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  task_id: string;
  status: string;
  status_url: string;
  imported_records?: number;
  errors?: string[];
}

export interface Statistics {
  total_stores: number;
  total_products: number;
  total_pricing_records: number;
  average_price: number;
  latest_import: string;
}

export interface CountryStats {
  country: string;
  record_count: number;
  avg_price: number;
  min_price: number;
  max_price: number;
}
