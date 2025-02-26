#if repo is private the add token with link as shown below
#foramt: repo_url, branch, start command

configs = [
  RepoConfig("https://<token>@github.com/123/somebot/", "master", "python3 main.py"),
  RepoConfig("https://github.com/xyz/123-Bot.git", "main", "python3 bot.py")
]
