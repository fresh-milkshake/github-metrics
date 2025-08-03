import os
import sys
import requests
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

load_dotenv(override=True)


class GitHubReleasesAnalyzer:
    def __init__(self, username: str, token: Optional[str] = None):
        self.username = username
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_base = "https://api.github.com"
        self.console = Console()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Releases-Analyzer",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_user_repos(self) -> List[Dict]:
        repos = []
        page = 1
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Fetching repository list...", total=None)
            while True:
                url = f"{self.api_base}/users/{self.username}/repos"
                params = {"page": page, "per_page": 100, "type": "owner"}
                try:
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    page_repos = response.json()
                    if not page_repos:
                        break
                    repos.extend(page_repos)
                    page += 1
                    progress.update(
                        task, description=f"Fetched {len(repos)} repositories..."
                    )
                except requests.exceptions.RequestException as e:
                    self.console.print(f"[red]Error fetching repositories: {e}[/red]")
                    break
        return repos

    def get_repo_releases(self, repo_name: str) -> List[Dict]:
        releases = []
        page = 1
        while True:
            url = f"{self.api_base}/repos/{self.username}/{repo_name}/releases"
            params = {"page": page, "per_page": 100}
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                page_releases = response.json()
                if not page_releases:
                    break
                releases.extend(page_releases)
                page += 1
            except requests.exceptions.RequestException as e:
                self.console.print(
                    f"[red]Error fetching releases for {repo_name}: {e}[/red]"
                )
                break
        return releases

    def analyze_downloads(self, releases: List[Dict]) -> Dict:
        total_downloads = 0
        total_assets = 0
        releases_with_downloads = 0
        asset_details = []
        for release in releases:
            release_downloads = 0
            release_assets = len(release.get("assets", []))
            for asset in release.get("assets", []):
                download_count = asset.get("download_count", 0)
                release_downloads += download_count
                total_downloads += download_count
                asset_details.append(
                    {
                        "release_name": release.get(
                            "name", release.get("tag_name", "Unknown")
                        ),
                        "asset_name": asset.get("name", "Unknown"),
                        "downloads": download_count,
                        "size": asset.get("size", 0),
                        "content_type": asset.get("content_type", "Unknown"),
                    }
                )
            total_assets += release_assets
            if release_downloads > 0:
                releases_with_downloads += 1
        return {
            "total_downloads": total_downloads,
            "total_assets": total_assets,
            "releases_with_downloads": releases_with_downloads,
            "total_releases": len(releases),
            "asset_details": asset_details,
        }

    def display_results(self, repo_name: str, analysis: Dict):
        if analysis["total_releases"] == 0:
            return
        stats_text = Text()
        stats_text.append(
            f"📦 Total releases: {analysis['total_releases']}\n", style="cyan"
        )
        stats_text.append(
            f"📊 Releases with downloads: {analysis['releases_with_downloads']}\n",
            style="green",
        )
        stats_text.append(
            f"📁 Total files: {analysis['total_assets']}\n", style="yellow"
        )
        stats_text.append(
            f"⬇️ Total downloads: {analysis['total_downloads']:,}", style="bold magenta"
        )
        panel = Panel(stats_text, title=f"📂 {repo_name}", border_style="blue")
        self.console.print(panel)
        if analysis["asset_details"]:
            table = Table(title=f"📋 Download details for {repo_name}")
            table.add_column("Release", style="cyan")
            table.add_column("File", style="green")
            table.add_column("Downloads", style="magenta", justify="right")
            table.add_column("Size", style="yellow", justify="right")
            table.add_column("Type", style="dim")
            sorted_assets = sorted(
                analysis["asset_details"], key=lambda x: x["downloads"], reverse=True
            )
            for asset in sorted_assets:
                size_mb = asset["size"] / (1024 * 1024) if asset["size"] > 0 else 0
                table.add_row(
                    asset["release_name"],
                    asset["asset_name"],
                    f"{asset['downloads']:,}",
                    f"{size_mb:.1f} MB" if size_mb > 0 else "N/A",
                    asset["content_type"],
                )
            self.console.print(table)
        self.console.print()

    def run_analysis(self):
        self.console.print(
            Panel(
                f"🔍 Analyzing GitHub releases for user: [bold blue]{self.username}[/bold blue]",
                border_style="green",
            )
        )
        self.console.print()
        repos = self.get_user_repos()
        if not repos:
            self.console.print(
                "[red]❌ Failed to fetch repositories or user not found[/red]"
            )
            return
        self.console.print(f"[green]✅ Found {len(repos)} repositories[/green]\n")
        total_stats = {
            "total_downloads": 0,
            "total_assets": 0,
            "releases_with_downloads": 0,
            "total_releases": 0,
            "repos_with_releases": 0,
        }
        repos_with_releases = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Analyzing repositories...", total=len(repos))
            for repo in repos:
                repo_name = repo["name"]
                progress.update(task, description=f"Analyzing {repo_name}...")
                releases = self.get_repo_releases(repo_name)
                if releases:
                    analysis = self.analyze_downloads(releases)
                    total_stats["total_downloads"] += analysis["total_downloads"]
                    total_stats["total_assets"] += analysis["total_assets"]
                    total_stats["releases_with_downloads"] += analysis[
                        "releases_with_downloads"
                    ]
                    total_stats["total_releases"] += analysis["total_releases"]
                    total_stats["repos_with_releases"] += 1
                    repos_with_releases.append((repo_name, analysis))
                progress.advance(task)
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold green]📊 ANALYSIS RESULTS[/bold green]")
        self.console.print("=" * 60)
        overall_stats = Text()
        overall_stats.append(
            f"📂 Repositories with releases: {total_stats['repos_with_releases']}\n",
            style="cyan",
        )
        overall_stats.append(
            f"📦 Total releases: {total_stats['total_releases']}\n", style="green"
        )
        overall_stats.append(
            f"📊 Releases with downloads: {total_stats['releases_with_downloads']}\n",
            style="yellow",
        )
        overall_stats.append(
            f"📁 Total files: {total_stats['total_assets']}\n", style="blue"
        )
        overall_stats.append(
            f"⬇️  Total downloads: {total_stats['total_downloads']:,}",
            style="bold magenta",
        )
        self.console.print(
            Panel(overall_stats, title="🎯 OVERALL STATISTICS", border_style="green")
        )
        self.console.print()
        if repos_with_releases:
            self.console.print("[bold blue]📋 DETAILS BY REPOSITORY:[/bold blue]\n")
            repos_with_releases.sort(
                key=lambda x: x[1]["total_downloads"], reverse=True
            )
            for repo_name, analysis in repos_with_releases:
                self.display_results(repo_name, analysis)
        if total_stats["total_downloads"] == 0:
            self.console.print("[yellow]⚠️  No downloads found in any release[/yellow]")


def main():
    if len(sys.argv) != 2:
        print("Usage: python github_releases_downloads.py <username>")
        print("Example: python github_releases_downloads.py octocat")
        print(
            "\nFor best performance, create a .env file with the GITHUB_TOKEN variable"
        )
        sys.exit(1)
    username = sys.argv[1]
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️  GITHUB_TOKEN not found in environment variables.")
        print(
            "   Create a .env file with the GITHUB_TOKEN variable to increase API limits"
        )
        print("   Without a token: 60 requests/hour, with a token: 5000 requests/hour")
        print()
    try:
        analyzer = GitHubReleasesAnalyzer(username, token)
        analyzer.run_analysis()
    except KeyboardInterrupt:
        print("\n\n[red]Analysis interrupted by user[/red]")
    except Exception as e:
        print(f"\n[red]An error occurred: {e}[/red]")


if __name__ == "__main__":
    main()
