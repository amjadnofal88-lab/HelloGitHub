import pandas as pd
import requests

GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # ← حطّ token هون
USERNAME = "octocat"
OUTPUT_FILE = "github_repos.xlsx"


def build_headers():
    placeholder = "ghp_xxxxxxxxxxxx"
    if GITHUB_TOKEN and GITHUB_TOKEN != placeholder:
        return {"Authorization": f"token {GITHUB_TOKEN}"}
    return {}


def fetch_repos(username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    response = requests.get(url, headers=build_headers(), timeout=20)
    if response.status_code == 200:
        return response.json()
    if response.status_code in (401, 403):
        print("GitHub API access denied or rate-limited. Set a valid GITHUB_TOKEN and retry.")
        return []
    response.raise_for_status()


def main():
    repos = fetch_repos(USERNAME)
    rows = [
        {
            "name": repo.get("name"),
            "url": repo.get("html_url"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language"),
            "updated_at": repo.get("updated_at"),
        }
        for repo in repos
    ]
    pd.DataFrame(rows).to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"Saved {len(rows)} repos to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
