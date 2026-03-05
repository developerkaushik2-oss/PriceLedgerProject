import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { RouterModule } from "@angular/router";
import { UploadComponent } from "./components/upload.component";
import { SearchComponent } from "./components/search.component";
import { DashboardComponent } from "./components/dashboard.component";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    UploadComponent,
    SearchComponent,
    DashboardComponent,
  ],
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.css"],
})
export class AppComponent {
  activeTab = "dashboard";

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    window.scrollTo(0, 0);
  }
}
