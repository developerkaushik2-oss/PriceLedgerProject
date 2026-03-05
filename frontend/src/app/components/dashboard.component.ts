import { Component, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { StatsService } from "@services/stats.service";
import { Statistics, CountryStats } from "@models/index";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./dashboard.component.html",
  styleUrls: ["./dashboard.component.css"],
})
export class DashboardComponent implements OnInit {
  stats: Statistics | null = null;
  countryStats: CountryStats[] = [];
  isLoading = false;
  errorMessage: string | null = null;

  constructor(private statsService: StatsService) {}

  ngOnInit(): void {
    this.loadStats();
  }

  loadStats(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.statsService.getOverview().subscribe({
      next: (data) => {
        this.stats = data;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.error || "Failed to load statistics";
        this.isLoading = false;
      },
    });

    this.statsService.getByCountry().subscribe({
      next: (data) => {
        this.countryStats = data;
      },
      error: (error) => {
        console.error("Failed to load country stats:", error);
      },
    });
  }
}
