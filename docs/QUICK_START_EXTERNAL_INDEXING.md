# Quick Start: Index External Projects

## TL;DR

### Your Situation: Projects in `D:\GitProjects`

**✅ No configuration needed!** The default works automatically.

Just restart the container and index:

```bash
# Restart container to load new mount configuration
docker-compose restart context-server

# Index your Boarding House project
ast_index_directory("D:\\GitProjects\\Boarding_House\\src", recursive=true)
```

The system automatically maps `D:\GitProjects\Boarding_House` → `/external/Boarding_House` in the container.

---

## For Other Locations

If your projects are in a different location (e.g., `C:\Users\username\projects`):

### Step 1: Configure

Edit `.env` file (create if it doesn't exist):

```bash
EXTERNAL_PROJECTS_PATH=C:/Users/username/projects
```

### Step 2: Restart

```bash
docker-compose restart context-server
```

### Step 3: Index

```python
ast_index_directory("C:\\Users\\username\\projects\\MyProject\\src", recursive=true)
```

---

## Supported Path Formats

All of these work:

```python
# Windows backslash
"D:\\GitProjects\\Boarding_House\\src"

# Windows forward slash  
"D:/GitProjects/Boarding_House/src"

# Git Bash/WSL style
"/d/gitprojects/Boarding_House/src"

# Container path (if you know it)
"/external/Boarding_House/src"
```

---

## How It Works

1. **Default mount**: `../..` (parent of Context repo) → `/external` in container
2. **For Context at** `D:\GitProjects\Context`:
   - Mounts `D:\GitProjects` at `/external`
   - `D:\GitProjects\Boarding_House` becomes `/external/Boarding_House`
3. **Path resolution**: Automatically converts your host paths to container paths

---

## Troubleshooting

**Error: "Directory does not exist"**

The error message will tell you exactly what to do:

```
Path not accessible in container. 
To index external projects, set EXTERNAL_PROJECTS_PATH in .env file. 
Example: EXTERNAL_PROJECTS_PATH=D:/GitProjects (or C:/Users/username/projects). 
Then restart the container with: docker-compose restart context-server
```

Follow the instructions in the error message.

---

## Full Documentation

See [EXTERNAL_PROJECTS_SETUP.md](./EXTERNAL_PROJECTS_SETUP.md) for complete details.

