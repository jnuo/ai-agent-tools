"""GitHub repository analytics via gh CLI."""

from .auth import run_gh_api


def get_repo_stats(repo: str) -> dict:
    """Get repository metadata.

    Args:
        repo: Repository in 'owner/name' format

    Returns:
        dict with stars, forks, watchers, open_issues, description
    """
    data = run_gh_api(f"repos/{repo}")
    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("subscribers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "description": data.get("description", ""),
    }


def get_traffic(repo: str) -> dict:
    """Get traffic data (views + clones, last 14 days).

    Args:
        repo: Repository in 'owner/name' format

    Returns:
        dict with 'views' and 'clones' arrays, each containing
        {timestamp, count, uniques} entries
    """
    views = run_gh_api(f"repos/{repo}/traffic/views")
    clones = run_gh_api(f"repos/{repo}/traffic/clones")

    return {
        "views": views.get("views", []),
        "clones": clones.get("clones", []),
    }


def get_referrers(repo: str) -> list[dict]:
    """Get popular referrers.

    Args:
        repo: Repository in 'owner/name' format

    Returns:
        List of dicts with referrer, count, uniques
    """
    return run_gh_api(f"repos/{repo}/traffic/popular/referrers")
