# GitHub Releases Metrics

![python](https://img.shields.io/badge/python-3.10-blue)
![GitHub](https://img.shields.io/badge/GitHub-API-white)

A Python script to analyze download statistics for all releases across all repositories of a GitHub user.

## Installation

1. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2. Fill in the `.env` file with your GitHub token:

    ```bash
    GITHUB_TOKEN=your_github_token
    ```

> [!TIP]
> You can get your GitHub token from [here](https://github.com/settings/tokens). You need to create a token with the `public_repo` scope.

## Usage

```bash
python github-metrics.py <username>
```

## Output

The script summarizes overall statistics such as repositories with releases, total releases, releases with downloads, total files, and total downloads. For each repository, it shows detailed stats and a table of files with their release name, file name, download count, size, and type.
