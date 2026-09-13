# 📘 The Complete Git & GitHub Push / Pull Guide
### *A Practical, Step-by-Step Reference Manual with Explanations*

---

## 🧠 1. The Core Mental Model (How Git Actually Works)

Before running commands, it helps to understand that Git tracks your code across **four distinct zones**:

```
+------------------+         +------------------+         +------------------+         +--------------------+
|  Working Folder  |         |   Staging Area   |         | Local Repository |         | Remote Repository  |
|  (Your hard drive)|  --->   |     (Index)      |  --->   |  (.git folder)   |  --->   |     (GitHub)       |
|                  |         |                  |         |                  |         |                    |
|  Actual files    |         | Files ready to   |         | Permanent local  |         | Cloud copy online  |
|  you edit in IDE |         | be committed     |         | snapshots        |         | for everyone/backup|
+------------------+         +------------------+         +------------------+         +--------------------+
        |                             |                            |                             |
        +-------- git add ----------->+                            |                             |
                                      +------- git commit -------->+                             |
                                                                   +--------- git push --------->+
                                                                   +<-------- git pull ----------+
```

| Zone | What it is | Command to move to next zone |
|------|------------|------------------------------|
| **1. Working Directory** | The folder on your PC where you create and edit files. | `git add <files>` |
| **2. Staging Area (Index)** | The preparation area. Tells Git: *"Include these specific changes in the next snapshot."* | `git commit -m "..."` |
| **3. Local Repository** | Stored inside hidden `.git` folder. A permanent, timestamped history saved on your machine. | `git push <remote> <branch>` |
| **4. Remote Repository** | The cloud copy on GitHub (`https://github.com/raj0072me/kos-crypto-alert.git`). | `git pull` brings it back to you. |

---

## 🚀 2. Step-by-Step: How to PUSH Changes to GitHub

Whenever you add a feature, edit files, or fix a bug, follow these **4 standard steps**:

### Step 1: Check Current Status
See what has been modified, created, or deleted:

```bash
git status
```

* **Red files**: Files changed in your working folder, but not yet staged.
* **Green files**: Files already staged and ready to be committed.
* **Untracked (`??`)**: New files that Git has never tracked before.

*(Optional)* If you want to see line-by-line differences of what you edited:
```bash
git diff
```

---

### Step 2: Stage Your Changes (`git add`)
Move modified files into the Staging Area.

* **To stage everything (new, edited, and deleted files):**
  ```bash
  git add .
  ```
* **Or to stage one specific file:**
  ```bash
  git add admin_panel.py
  ```

> **What happens under the hood?**
> Git calculates the SHA hash of the file contents, compresses them, and writes index pointers in `.git/index`. It does **not** upload to the internet yet.

---

### Step 3: Create a Snapshot Commit (`git commit`)
Package everything in the staging area into a permanent local snapshot with a descriptive note.

```bash
git commit -m "Add edit user dialog and NeonDB cloud sync"
```

> **What happens under the hood?**
> Git takes a snapshot of the exact state of all staged files, assigns it a unique 40-character commit ID (e.g. `a1b2c3d`), records your name, email, timestamp, and stores it in your local repository.

---

### Step 4: Upload to GitHub (`git push`)
Send your local commits to your GitHub cloud repository.

```bash
git push <remote-name> <branch-name>
```

For your project, push to `main`:
```bash
git push kos-alert main
```
*(Or if your primary remote is named `origin`: `git push origin main`)*

> **What happens under the hood?**
> Git negotiates with GitHub over HTTPS, uploads the missing data chunks (packfiles), and updates the remote branch pointer on GitHub's servers to match your latest commit.

---

## 📥 3. Step-by-Step: How to PULL Changes from GitHub

Use `git pull` when:
- You work across multiple computers (e.g., PC at office and laptop at home).
- Collaborators pushed new commits.
- You made edits directly via GitHub web UI.

### Step 1: Check your local status first
Before pulling, make sure your current local directory doesn't have uncommitted edits that might conflict:

```bash
git status
```
*If you have uncommitted changes, either commit them first (`git add .` && `git commit -m "..."`) or stash them (`git stash`).*

---

### Step 2: Run Git Pull

```bash
git pull <remote-name> <branch-name>
```

For your project:
```bash
git pull kos-alert main
```

> **What actually happens when you run `git pull`?**
> `git pull` is a shortcut that automatically performs two operations:
> 1. **`git fetch`**: Downloads new commits and branches from GitHub into your local `.git` storage (without touching your working files).
> 2. **`git merge`**: Merges those downloaded changes directly into your current working files and branch.

---

## 🔍 4. Understanding Remotes (`git remote`)

A "remote" is simply a named nickname for a cloud URL.

### View your configured remotes:
```bash
git remote -v
```
Output example:
```
kos-alert   https://github.com/raj0072me/kos-crypto-alert.git (fetch)
kos-alert   https://github.com/raj0072me/kos-crypto-alert.git (push)
origin      https://github.com/robopol/crypto_checker.git (fetch)
origin      https://github.com/robopol/crypto_checker.git (push)
```

### How to add a remote:
```bash
git remote add <name> <url>
```

### How to change an existing remote URL:
```bash
git remote set-url <name> <new-url>
```

### How to remove an unused remote:
```bash
git remote remove <name>
```

---

## ⚠️ 5. Common Scenarios & Troubleshooting

### Scenario A: GitHub Rejects Push ("Updates were rejected because the remote contains work...")
This occurs when GitHub has newer commits that your local computer doesn't have yet (for example, if you edited README on github.com).

**Solution:**
1. Pull the latest changes first:
   ```bash
   git pull kos-alert main --rebase
   ```
2. Then push:
   ```bash
   git push kos-alert main
   ```

---

### Scenario B: Merge Conflict
If you and someone else edited the exact same line in the same file, Git will pause and ask you to choose.

You will see markers inside the conflicting file like this:
```python
<<<<<<< HEAD (Your Local Change)
ADMIN_PHONE = "9899654695"
=======
ADMIN_PHONE = "9899000000"
>>>>>>> 1a2b3c4d (Incoming Change from GitHub)
```

**How to resolve:**
1. Open the file in your IDE.
2. Delete the markers (`<<<<<<<`, `=======`, `>>>>>>>`) and keep the correct code.
3. Save the file.
4. Stage and commit the resolution:
   ```bash
   git add .
   git commit -m "Resolve merge conflict in config"
   git push kos-alert main
   ```

---

### Scenario C: Unstaging a file you accidentally added
If you ran `git add secret.json` and don't want it staged:
```bash
git restore --staged secret.json
```

---

### Scenario D: Undoing uncommitted changes to a file
To revert a file back to the last committed version:
```bash
git restore filename.py
```

---

### Scenario E: GitHub Authentication on Windows
When pushing for the first time on Windows:
1. Windows will open a **GitHub Sign In** browser popup via **Git Credential Manager**.
2. Click **Sign in with your browser** and authorize.
3. Windows saves the secure token in Windows Credential Vault permanently. You won't be prompted again.

---

## 📋 6. Everyday Git Cheat Sheet

| Task | Command |
|------|---------|
| Check current status | `git status` |
| View line differences | `git diff` |
| Stage all modified files | `git add .` |
| Commit with message | `git commit -m "Your description"` |
| Push to remote | `git push <remote> <branch>` |
| Pull from remote | `git pull <remote> <branch>` |
| View commit history | `git log --oneline -n 10` |
| View remote URLs | `git remote -v` |
| Discard uncommitted edits | `git restore <file>` |
| Switch or create branch | `git checkout -b <new-branch>` |

---

## 🎯 7. Quick Walkthrough: Pushing Your Latest Project Code

To push all current updates (NeonDB sync, Admin Panel, Edit User dialog, and updated `.spec`) to your repo right now:

```bash
# 1. View files to be updated
git status

# 2. Stage all files
git add .

# 3. Commit with a clear message
git commit -m "feat: add NeonDB cloud sync, admin panel, user edit dialog, and standalone portable exe"

# 4. Push to your GitHub repository
git push kos-alert main
```
