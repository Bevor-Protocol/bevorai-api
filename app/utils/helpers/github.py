from github import Github

# Authentication is defined via github.Auth
from github import Auth

# using an access token
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))

# Public Web Github
g = Github(auth=auth)

def get_repo_tree(repo_url):
    """
    Takes a GitHub repo URL and extracts the repo tree using GitHub API
    Args:
        repo_url: Full GitHub repository URL (e.g. https://github.com/owner/repo)
    Returns:
        JSON response containing the repository tree
    """
    # Parse owner and repo from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    
    # Get the repository object
    repo_obj = g.get_repo(f"{owner}/{repo}")
    
    # Get default branch's commit SHA
    tree_sha = repo_obj.get_commits()[0].sha
    
    # Get the tree directly using PyGithub
    tree = repo_obj.get_git_tree(tree_sha, recursive=True)
    return tree

def traverse_tree(tree):
    sol_files = []
    for item in tree.tree:
        if item.path.endswith('.sol'):
            sol_files.append(item.path)
    return sol_files

def get_raw_content(tree, repo_obj):
    """
    Converts tree paths to raw GitHub URLs and downloads content
    Returns dictionary of {path: content}
    """
    raw_contents = {}
    for item in tree.tree:
        if item.path.endswith('.sol'):
            try:
                # Get raw content
                response = repo_obj.get_contents(item.path).decoded_content.decode()
                raw_contents[item.path] = response
            except Exception as e:
                print(f"Error downloading {item.path}: {e}")
                
    return raw_contents


def get_solidity_source(repo_url: str) -> str:
    """
    Takes a GitHub repo URL and returns all Solidity source code as a string
    Args:
        repo_url: Full GitHub repository URL (e.g. https://github.com/owner/repo)
    Returns:
        String containing all Solidity source code concatenated together
    """
    try:
        # Parse owner and repo from URL
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        
        # Get the repository object
        repo_obj = g.get_repo(f"{owner}/{repo}")
        
        tree = get_repo_tree(repo_url)
        
        # Get list of Solidity files
        sol_files = traverse_tree(tree)
        
        # Get raw contents of all Solidity files
        contents = get_raw_content(tree, repo_obj)
        
        # Concatenate all source code together with file labels
        all_source = ""
        for path, content in contents.items():
            all_source += f"//**** File: {path} ****\n"
            all_source += content + "\n\n"
            
        return all_source
            
    except Exception as e:
        raise Exception(f"Error getting Solidity source: {e}")
    finally:
        # To close connections after use
        g.close()