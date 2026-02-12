# Real-Time Task Tracking Dashboard for Kimi + CLAWS.BOT

**Goal:** Web-based dashboard to assign, track, and monitor all AI tasks in real-time

---

## 🎯 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │   React Dashboard (http://localhost:3000)        │  │
│  │   - Task queue visualization                     │  │
│  │   - Real-time agent status                       │  │
│  │   - Live logs streaming                          │  │
│  │   - Evidence viewer (screenshots, diffs)         │  │
│  └────────────────┬─────────────────────────────────┘  │
└────────────────────┼─────────────────────────────────────┘
                     │ WebSocket
                     ↓
┌─────────────────────────────────────────────────────────┐
│            FastAPI Backend (port 4000)                   │
│  - Task queue management (Redis)                        │
│  - Agent orchestration                                  │
│  - WebSocket broadcast (task updates)                   │
│  - Evidence storage                                     │
└──────┬──────────────┬──────────────┬────────────────────┘
       ↓              ↓              ↓
┌─────────────┐  ┌──────────┐  ┌─────────────┐
│ Kimi API    │  │ Kimi MCP │  │ Browser MCP │
│ (port 8000) │  │ (8010)   │  │ (8011)      │
└─────────────┘  └──────────┘  └─────────────┘
```

---

## 📋 Features

### 1. Task Queue Management
- **Create Task:** Form to submit new tasks with priority
- **View Queue:** List of pending, active, completed tasks
- **Task Details:** Expand to see logs, agent assignments, evidence
- **Cancel Task:** Stop running tasks
- **Retry Failed:** Rerun tasks that errored

### 2. Real-Time Agent Status
- **Agent Grid:** Visual cards showing each agent's status
- **Status Indicators:**
  - 🟢 Idle (available)
  - 🟡 Busy (working on task)
  - 🔴 Error (failed, needs attention)
  - ⚫ Offline (not running)
- **Agent Details:** Click to see current task, performance metrics
- **Manual Control:** Start/stop specific agents

### 3. Live Log Streaming
- **Real-Time Logs:** WebSocket stream of all agent output
- **Filtering:** By agent, task, log level (info, warn, error)
- **Search:** Full-text search through logs
- **Download:** Export logs as JSON/CSV

### 4. Evidence Viewer
- **Screenshot Gallery:** View screenshots from browser tests
- **Visual Diffs:** Side-by-side comparison with baseline
- **Metrics Dashboard:** Accessibility, performance, code quality
- **Download Bundle:** ZIP of all evidence for a task

### 5. Analytics & Reporting
- **Performance Graphs:** Task completion time, success rate
- **Agent Utilization:** Which agents are most used
- **Cost Tracking:** $0.00 for Kimi, API costs for fallbacks
- **Historical Trends:** Task volume over time

---

## 🛠️ Tech Stack

### Frontend
- **React 18** + TypeScript
- **Vite** (fast dev server)
- **TailwindCSS** (styling)
- **React Query** (data fetching)
- **Socket.io-client** (WebSocket)
- **Recharts** (graphs)
- **React Hot Toast** (notifications)

### Backend
- **FastAPI** (Python API framework)
- **Socket.io** (WebSocket server)
- **Redis** (task queue + pub/sub)
- **SQLite** (task history + analytics)
- **Pydantic** (validation)

### Infrastructure
- **Docker** (optional containerization)
- **Nginx** (optional reverse proxy)

---

## 📁 Project Structure

```
kimi/
├── dashboard/                    # NEW
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── TaskQueue.tsx
│   │   │   │   ├── AgentStatus.tsx
│   │   │   │   ├── LiveLogs.tsx
│   │   │   │   ├── EvidenceViewer.tsx
│   │   │   │   └── Analytics.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useWebSocket.ts
│   │   │   │   ├── useTasks.ts
│   │   │   │   └── useAgents.ts
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── backend/
│       ├── dashboard_api.py      # FastAPI app
│       ├── task_queue.py         # Redis queue manager
│       ├── websocket_manager.py  # WebSocket broadcast
│       └── models.py             # Pydantic models
│
├── server/                       # EXISTING
│   ├── api/main.py              # Kimi API (port 8000)
│   ├── mcp_toolhost.py          # MCP (port 8010)
│   └── browser_mcp.py           # Browser (port 8011)
│
└── start-dashboard.sh           # NEW - start dashboard + services
```

---

## 🚀 Implementation Plan (2 Days)

### Day 1: Backend (4-6 hours)

#### Phase 1: Task Queue (2 hours)
1. Install Redis: `brew install redis` or Docker
2. Create `dashboard/backend/task_queue.py`:
   - `add_task(task_data)` → Returns task_id
   - `get_task(task_id)` → Returns task status
   - `list_tasks(filter)` → Returns all tasks
   - `update_task(task_id, status, progress)` → Update task
   - `cancel_task(task_id)` → Cancel running task

3. Create task database (SQLite):
```sql
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  description TEXT,
  status TEXT,  -- pending, running, completed, failed
  progress REAL,  -- 0.0 to 1.0
  agent TEXT,
  created_at TIMESTAMP,
  completed_at TIMESTAMP,
  result TEXT,
  error TEXT
);
```

#### Phase 2: WebSocket Server (1 hour)
Create `dashboard/backend/websocket_manager.py`:
- Broadcast task updates to all connected clients
- Stream logs in real-time
- Push agent status changes

#### Phase 3: Dashboard API (1 hour)
Create `dashboard/backend/dashboard_api.py`:
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import socketio

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# REST endpoints
@app.get("/api/tasks")
async def list_tasks(): ...

@app.post("/api/tasks")
async def create_task(task: TaskCreate): ...

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str): ...

@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str): ...

@app.get("/api/agents")
async def list_agents(): ...

@app.get("/api/evidence/{task_id}")
async def get_evidence(task_id: str): ...

# WebSocket events
@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")

# Background task: monitor agents and broadcast status
async def broadcast_agent_status():
    while True:
        status = get_all_agent_status()
        await sio.emit('agent_status', status)
        await asyncio.sleep(1)
```

#### Phase 4: Integration with CLAWS.BOT (2 hours)
Modify CLAWS.BOT to report to dashboard:
1. When task starts → POST to `/api/tasks`
2. As task progresses → WebSocket emit progress
3. When task completes → POST result + evidence
4. If task fails → POST error

### Day 2: Frontend (4-6 hours)

#### Phase 1: Project Setup (30 min)
```bash
cd dashboard/frontend
npm create vite@latest . -- --template react-ts
npm install socket.io-client @tanstack/react-query recharts react-hot-toast
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### Phase 2: Task Queue Component (1.5 hours)
Create `TaskQueue.tsx`:
- Fetch tasks from API
- Display in table/cards with status badges
- Real-time updates via WebSocket
- Forms to create new task
- Action buttons (cancel, retry, view details)

#### Phase 3: Agent Status Component (1 hour)
Create `AgentStatus.tsx`:
- Grid of agent cards
- Color-coded status indicators
- Click to see details
- Auto-refresh via WebSocket

#### Phase 4: Live Logs Component (1 hour)
Create `LiveLogs.tsx`:
- Connect to WebSocket log stream
- Auto-scroll to bottom
- Syntax highlighting for code
- Filter by agent/level
- Search functionality

#### Phase 5: Evidence Viewer (1.5 hours)
Create `EvidenceViewer.tsx`:
- Screenshot gallery (lightbox)
- Visual diff slider (before/after)
- Metrics display (accessibility, performance)
- Download button for evidence bundle

#### Phase 6: Analytics Dashboard (30 min)
Create `Analytics.tsx`:
- Bar chart: Tasks over time
- Pie chart: Success vs. failure rate
- Line graph: Average task duration
- Agent utilization breakdown

---

## 🎨 UI Design (Mockup)

```
┌─────────────────────────────────────────────────────────────┐
│  Kimi + CLAWS.BOT Dashboard                    [User] [⚙️]  │
├─────────────────────────────────────────────────────────────┤
│  📋 Tasks   🤖 Agents   📊 Analytics   📜 Logs   🔍 Evidence│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Tasks                                    [+ New Task]        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟢 #1: Create React login form              [⋮]        │ │
│  │    Status: Running (Progress: 65%)                     │ │
│  │    Agent: Code Generator                               │ │
│  │    Time: 2m 15s / ~3m 30s est.                        │ │
│  │    [View Logs] [View Evidence] [Cancel]               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟡 #2: Security review of auth module        [⋮]       │ │
│  │    Status: Pending (Queue position: 1)                │ │
│  │    Agent: (Waiting)                                    │ │
│  │    [Start Now] [Cancel]                               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ✅ #3: Image generation for blog post        [⋮]       │ │
│  │    Status: Completed (100%)                           │ │
│  │    Agent: Image Generator                             │ │
│  │    Time: 1m 45s                                       │ │
│  │    [View Result] [Download Evidence]                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Agent Status                                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ 🟢 Code Gen │ 🟡 Security │ 🟢 Browser  │ ⚫ Swarm     │ │
│  │   Busy      │   Idle      │   Idle      │   Offline   │ │
│  │   Task #1   │   Ready     │   Ready     │   (Start)   │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
│                                                               │
│  Recent Activity                                              │
│  • 2m ago: Task #1 started (Code Generator)                  │
│  • 5m ago: Task #3 completed ✅                              │
│  • 8m ago: Screenshot captured (mobile viewport)             │
│  • 10m ago: Visual diff: 2.3% change                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Plan

### Unit Tests
- Task queue operations (add, get, update, cancel)
- WebSocket message broadcasting
- API endpoints (CRUD operations)

### Integration Tests
- Create task → Agent picks up → Completes → Evidence saved
- WebSocket real-time updates
- Multiple concurrent tasks

### E2E Tests (Playwright)
- User creates task via dashboard
- Watch real-time progress updates
- View evidence (screenshots, diffs)
- Cancel running task

---

## 📊 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Task creation | < 100ms | Add to Redis queue |
| WebSocket latency | < 50ms | Real-time updates |
| Log streaming | < 100ms | From agent to UI |
| Dashboard load time | < 2s | Initial page load |
| Concurrent tasks | 100+ | Redis queue handles this |
| Concurrent WebSocket clients | 1000+ | Socket.io handles this |

---

## 🔒 Security Considerations

### Authentication
- JWT-based auth (optional for multi-user)
- Session management
- Role-based access (admin, viewer)

### Authorization
- Task ownership (who created the task)
- Agent control (who can start/stop agents)
- Evidence access (download permissions)

### Network
- HTTPS for production
- WebSocket over TLS (wss://)
- CORS configuration
- Rate limiting

---

## 💰 Cost

**Zero.** Everything runs locally:
- FastAPI (free, open source)
- React + Vite (free, open source)
- Redis (free, open source)
- Socket.io (free, open source)
- No cloud hosting required

---

## 🚀 Quick Start (After Building)

### 1. Install Dependencies
```bash
# Backend
cd dashboard/backend
pip install fastapi uvicorn socketio python-socketio redis

# Frontend
cd dashboard/frontend
npm install
```

### 2. Start Redis
```bash
redis-server  # or docker run -p 6379:6379 redis
```

### 3. Start Dashboard Backend
```bash
cd dashboard/backend
uvicorn dashboard_api:socket_app --port 4000 --reload
```

### 4. Start Frontend
```bash
cd dashboard/frontend
npm run dev  # Opens on http://localhost:3000
```

### 5. Start All Kimi Services
```bash
cd /Users/andrewmorton/Documents/GitHub/kimi
./start-all.sh
```

### 6. Open Dashboard
Visit: http://localhost:3000

---

## 📝 Next Steps

**Do you want me to build this dashboard?**

If yes, I'll:
1. Wait for FastAPI to finish installing
2. Build the backend (task queue, WebSocket, API)
3. Build the frontend (React dashboard)
4. Wire it all together
5. Test end-to-end
6. Deploy locally

**Estimated time:** 4-6 hours (can use agent swarm to parallelize)

**Let me know if you want:**
- ✅ Full dashboard (Option 2 above)
- 🎯 Quick MVP (basic task list + status)
- 🔗 Integration with existing tool (n8n, Temporal)
