"""GitHub API client for fetching issues and comments."""

import httpx


class GitHubClient:
    """Async GitHub API client with pagination support."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.timeout = httpx.Timeout(
            connect=5.0,
            read=10.0,
            write=5.0,
            pool=5.0,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_closed_issues(
        self,
        owner: str,
        repo: str,
        max_issues: int = 1000,
    ) -> list[dict]:
        """Fetch closed issues with pagination."""
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {"state": "closed", "per_page": 100}
        issues: list[dict] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while len(issues) < max_issues:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._headers(),
                )
                if response.status_code == 429:
                    raise RuntimeError("GitHub API rate limit exceeded")
                if response.status_code == 403:
                    raise RuntimeError(
                        "GitHub API access forbidden (check token or secondary rate limit)"
                    )
                if response.status_code == 404:
                    raise RuntimeError("Repository not found or not public")
                if response.status_code >= 500:
                    raise RuntimeError(
                        f"GitHub API server error ({response.status_code})"
                    )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Unexpected GitHub API response ({response.status_code})"
                    )

                data = response.json()
                if not isinstance(data, list):
                    raise RuntimeError("Unexpected GitHub API response format")

                issues.extend(data)
                if len(issues) >= max_issues:
                    issues = issues[:max_issues]
                    break

                # Follow pagination via Link header
                link_header = response.headers.get("link", "")
                next_url = None
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>").strip()
                        break
                if not next_url:
                    break
                url = next_url
                params = {}  # URL already contains params

        return issues

    async def get_issue_comments(self, comments_url: str) -> list[dict]:
        """Fetch comments for an issue with pagination."""
        comments: list[dict] = []
        url = comments_url

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while url and len(comments) < 10000:  # safety limit
                response = await client.get(url, headers=self._headers())
                if response.status_code == 429:
                    raise RuntimeError("GitHub API rate limit exceeded")
                if response.status_code == 403:
                    raise RuntimeError(
                        "GitHub API access forbidden (check token or secondary rate limit)"
                    )
                if response.status_code >= 500:
                    raise RuntimeError(
                        f"GitHub API server error ({response.status_code})"
                    )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Unexpected GitHub API response ({response.status_code})"
                    )

                data = response.json()
                if not isinstance(data, list):
                    raise RuntimeError("Unexpected GitHub API response format")

                comments.extend(data)

                # Follow pagination via Link header
                link_header = response.headers.get("link", "")
                next_url = None
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>").strip()
                        break
                url = next_url

        return comments
