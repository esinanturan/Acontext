<div align="center">
  <a href="https://discord.gg/rpZs5TaSuV">
      <img alt="Show Acontext header banner" src="./assets/Acontext-header-banner.png">
  </a>
  <p>
    <h3>Scale Context, Learn Experience</h3>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/acontext/"><img src="https://img.shields.io/pypi/v/acontext.svg"></a>
    <a href="https://www.npmjs.com/package/@acontext/acontext"><img src="https://img.shields.io/npm/v/@acontext/acontext.svg?logo=npm&logoColor=fff&style=flat&labelColor=2C2C2C&color=28CF8D"></a>
    <a href="https://github.com/memodb-io/acontext/actions/workflows/core-test.yaml"><img src="https://github.com/memodb-io/acontext/actions/workflows/core-test.yaml/badge.svg"></a>
    <a href="https://github.com/memodb-io/acontext/actions/workflows/api-test.yaml"><img src="https://github.com/memodb-io/acontext/actions/workflows/api-test.yaml/badge.svg"></a>
    <a href="https://github.com/memodb-io/acontext/actions/workflows/cli-test.yaml"><img src="https://github.com/memodb-io/acontext/actions/workflows/cli-test.yaml/badge.svg"></a>
  </p>
  <p align="center">
    <a href="https://x.com/acontext_io"><img src="https://img.shields.io/twitter/follow/acontext_io?style=social" alt="Twitter Follow"></a>
    <a href="https://discord.gg/rpZs5TaSuV"><img src="https://dcbadge.limes.pink/api/server/rpZs5TaSuV?style=flat" alt="Discord"></a>
  </p>
  <div align="center">
    <!-- Keep these links. Translations will automatically update with the README. -->
    <a href="https://zdoc.app/de/memodb-io/Acontext">Deutsch</a> | 
    <a href="https://zdoc.app/es/memodb-io/Acontext">Español</a> | 
    <a href="https://zdoc.app/fr/memodb-io/Acontext">Français</a> | 
    <a href="https://zdoc.app/ja/memodb-io/Acontext">日本語</a> | 
    <a href="https://zdoc.app/ko/memodb-io/Acontext">한국어</a> | 
    <a href="https://zdoc.app/pt/memodb-io/Acontext">Português</a> | 
    <a href="https://zdoc.app/ru/memodb-io/Acontext">Русский</a> | 
    <a href="https://zdoc.app/zh/memodb-io/Acontext">中文</a>
  </div>
  <br/>
</div>





Acontext is a context data platform that:

- **Stores** contexts & artifacts
- **Observes** agent tasks and user feedback.
- Enables agent **self-learning** by collecting experiences (SOPs) into long-term memory.
- Offers a **local Dashboard** to view messages, tasks, artifacts and experiences.



<div align="center">
    <picture>
      <img alt="Acontext Learning" src="./assets/acontext_dataflow.png" width="100%">
    </picture>
  <p>Store Contexts, Observe Tasks, then Learn Skills</p>
</div>





We're building it because we believe Acontext can help you:

- **Build a more scalable agent product**
- **Improve your agent success rate and reduce running steps**

so that your agent can be more stable and provide greater value to your users.



# 🌲 Core Concepts

- [**Session**](https://docs.acontext.io/store/messages/multi-provider) - A conversation thread that stores messages with multi-modal support. 
  - [**Task**](https://docs.acontext.io/observe/agent_tasks) - extracted automatically from conversations. Tasks move through `pending` → `running` → `success`/`failed` states. 
- [**Disk**](https://docs.acontext.io/store/disk) - File storage for agent artifacts.
- [**Space**](https://docs.acontext.io/learn/skill-space) - A knowledge repository (like Notion) for agent, where learned skills are stored. 
  - [**Experience Agent**](https://docs.acontext.io/learn/advance/experience-agent) - Background AI agents that extract tasks and learn skills. 

### How They Work Together

```bash
┌──────┐    ┌────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│ User │◄──►│ Your Agent │◄──►│ Session (stores msgs)   │    │ Disk (stores artifacts) │
└──────┘    └─────▲──────┘    └────────────┬────────────┘    └───────────▲─────────────┘
                  │                        │                             │
                  │                        │                   ┌─────────┴─────────┐
                  │                        │                   │ Agent reads/writes│
                  │                        │                   │ files as needed   │
                  │                        │                   └───────────────────┘
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Task Extraction              │
                  │         │ (by Experience Agent)        │
                  │         └──────────────┬───────────────┘
                  │                        │
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Task Completion              │
                  │         └──────────────┬───────────────┘
                  │                        │
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Space Connected?             │
                  │         └──────────────┬───────────────┘
                  │                        │ Yes
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Skill Learning               │
                  │         │ (by Experience Agent)        │
                  │         └──────────────┬───────────────┘
                  │                        │
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Skill Blocks (stored)        │
                  │         └──────────────┬───────────────┘
                  │                        │
                  │                        ▼
                  │         ┌──────────────────────────────┐
                  │         │ Search & Reuse in Future     │
                  │         └──────────────┬───────────────┘
                  │                        │
                  └────────────────────────┘
                     Skills guide agent behavior
```


# 🚀 How to Start It?

We have an `acontext-cli` to help you do quick proof-of-concept. Download it first in your terminal:

```bash
curl -fsSL https://install.acontext.io | sh
```

You should have [docker](https://www.docker.com/get-started/) installed and an OpenAI API Key to start an Acontext backend on your computer:

```bash
acontext docker up
```

> [📖 local setup](https://docs.acontext.io/local#start-acontext-server-locally) Acontext requires at least an OpenAI API key.  We recommend `gpt-5.1` or `gpt-4.1` as the LLM model



Once it's done, you can access the following endpoints:

- Acontext API Base URL: http://localhost:8029/api/v1
- Acontext Dashboard: http://localhost:3000/



<div align="center">
    <picture>
      <img alt="Dashboard" src="./docs/images/dashboard/BI.png" width="80%">
    </picture>
  <p>Dashboard of Success Rate and other Metrics</p>
</div>




# 🧐 How to Use It?

Download end-to-end scripts with `acontext`:

- **OpenAI SDK + Acontext**

```bash
acontext create my-proj --template-path "python/openai_basic"
```
- **OpenAI Agent SDK + Acontext**

```bash
# Coming Soon!
```

- **Agno + Acontext**

```bash
acontext create my-proj --template-path "python/agno_basic"
```

- **vercel/ai-sdk + Acontext**

```bash
# Coming Soon!
```



## Step by Step Explanation

<details>
<summary>Click to Open</summary>


We're maintaining Python [![pypi](https://img.shields.io/pypi/v/acontext.svg)](https://pypi.org/project/acontext/) and Typescript [![npm](https://img.shields.io/npm/v/@acontext/acontext.svg?logo=npm&logoColor=fff&style=flat&labelColor=2C2C2C&color=28CF8D)]("https://www.npmjs.com/package/@acontext/acontext") SDKs. The snippets below are using Python.

## Install SDKs

```
pip install acontext # for Python
npm i @acontext/acontext # for Typescript
```



## Initialize Client

```python
from acontext import AcontextClient

client = AcontextClient(
    base_url="http://localhost:8029/api/v1"
    api_key="sk-ac-your-root-api-bearer-token"
)
client.ping()

# yes, the default api_key is sk-ac-your-root-api-bearer-token
```

> [📖 async client doc](https://docs.acontext.io/settings/core)



## Store

Acontext can manage agent sessions and artifacts.

### Save Messages [📖](https://docs.acontext.io/api-reference/session/send-message-to-session)

Acontext offers persistent storage for message data. When you call `session.send_message`, Acontext will persist the message and start to monitor this session:

<details>
<summary>Code Snippet</summary>

```python
session = client.sessions.create()

messages = [
    {"role": "user", "content": "I need to write a landing page of iPhone 15 pro max"},
    {
        "role": "assistant",
        "content": "Sure, my plan is below:\n1. Search for the latest news about iPhone 15 pro max\n2. Init Next.js project for the landing page\n3. Deploy the landing page to the website",
    }
]

# Save messages
for msg in messages:
    client.sessions.send_message(session_id=session.id, blob=msg, format="openai")
```

> [📖](https://docs.acontext.io/store/messages/multi-modal) We also support multi-modal message storage and anthropic SDK.


</details>

### Load Messages [📖](https://docs.acontext.io/api-reference/session/get-messages-from-session)

Obtain your session messages using `sessions.get_messages`

<details>
<summary>Code Snippet</summary>

```python
r = client.sessions.get_messages(session.id)
new_msg = r.items

new_msg.append({"role": "user", "content": "How you doing?"})
r = openai_client.chat.completions.create(model="gpt-4.1", messages=new_msg)
print(r.choices[0].message.content)
client.sessions.send_message(session_id=session.id, blob=r.choices[0].message)
```

</details>

<div align="center">
    <picture>
      <img alt="Session" src="./docs/images/dashboard/message_viewer.png" width="80%">
    </picture>
  <p>You can view sessions in your local Dashboard</p>
</div>


### Artifacts [📖](https://docs.acontext.io/store/disk)

Create a disk for your agent to store and read artifacts using file paths:

<details>
<summary>Code Snippet</summary>

```python
from acontext import FileUpload

disk = client.disks.create()

file = FileUpload(
    filename="todo.md",
    content=b"# Sprint Plan\n\n## Goals\n- Complete user authentication\n- Fix critical bugs"
)
artifact = client.disks.artifacts.upsert(
    disk.id,
    file=file,
    file_path="/todo/"
)


print(client.disks.artifacts.list(
    disk.id,
    path="/todo/"
))

result = client.disks.artifacts.get(
    disk.id,
    file_path="/todo/",
    filename="todo.md",
    with_public_url=True,
    with_content=True
)
print(f"✓ File content: {result.content.raw}")
print(f"✓ Download URL: {result.public_url}")        
```
</details>



<div align="center">
    <picture>
      <img alt="Artifacts" src="./docs/images/dashboard/artifact_viewer.png" width="80%">
    </picture>
  <p>You can view artifacts in your local Dashboard</p>
</div>



## Observe [📖](https://docs.acontext.io/observe)

For every session, Acontext will automatically launch a background agent to track the task progress and user feedback. It's like a background TODO agent.

You can use the SDK to retrieve the current state of the agent session.

<details>
<summary>Full Script</summary>

```python
from acontext import AcontextClient

# Initialize client
client = AcontextClient(
    base_url="http://localhost:8029/api/v1", api_key="sk-ac-your-root-api-bearer-token"
)

# Create a project and session
session = client.sessions.create()

# Conversation messages
messages = [
    {"role": "user", "content": "I need to write a landing page of iPhone 15 pro max"},
    {
        "role": "assistant",
        "content": "Sure, my plan is below:\n1. Search for the latest news about iPhone 15 pro max\n2. Init Next.js project for the landing page\n3. Deploy the landing page to the website",
    },
    {
        "role": "user",
        "content": "That sounds good. Let's first collect the message and report to me before any landing page coding.",
    },
    {
        "role": "assistant",
        "content": "Sure, I will first collect the message then report to you before any landing page coding.",
      	"tool_calls": [
            {
                "id": "call_001",
                "type": "function",
                "function": {
                    "name": "search_news",
                    "arguments": "{\"query\": \"iPhone news\"}"
                }
            }
        ]
    },
]

# Send messages in a loop
for msg in messages:
    client.sessions.send_message(session_id=session.id, blob=msg, format="openai")

# Wait for task extraction to complete
client.sessions.flush(session.id)

# Display extracted tasks
tasks_response = client.sessions.get_tasks(session.id)
print(tasks_response)
for task in tasks_response.items:
    print(f"\nTask #{task.order}:")
    print(f"  ID: {task.id}")
    print(f"  Title: {task.data['task_description']}")
    print(f"  Status: {task.status}")

    # Show progress updates if available
    if "progresses" in task.data:
        print(f"  Progress updates: {len(task.data['progresses'])}")
        for progress in task.data["progresses"]:
            print(f"    - {progress}")

    # Show user preferences if available
    if "user_preferences" in task.data:
        print("  User preferences:")
        for pref in task.data["user_preferences"]:
            print(f"    - {pref}")

```
> `flush` is a blocking call, it will wait for the task extraction to complete.
> You don't need to call it in production, Acontext has a buffer mechanism to ensure the task extraction is completed right on time.

</details>

Example Task Return:

```txt
Task #1:
  Title: Search for the latest news about iPhone 15 Pro Max and report findings to the user before any landing page coding.
  Status: running
  Progress updates: 1
    - User clarified preference for reporting the collected news before starting coding, and I confirmed that the first step will be reporting before moving on to landing page development.
  User preferences:
    - user expects a report on latest news about iPhone 15 pro max before any coding work on the landing page.

Task #2:
  Title: Initialize a Next.js project for the iPhone 15 Pro Max landing page.
  Status: pending

Task #3:
  Title: Deploy the completed landing page to the website.
  Status: pending
```



You can view the session tasks' statuses in the Dashboard:

<div align="center">
    <picture>
      <img alt="Acontext Learning" src="./docs/images/dashboard/session_task_viewer.png" width="80%">
    </picture>
  <p>A Task Demo</p>
</div>



## Self-learning

Acontext can gather a bunch of sessions and learn skills (SOPs) on how to call tools for certain tasks.

### Learn Skills to a `Space` [📖](https://docs.acontext.io/learn/skill-space)

A `Space` can store skills, experiences, and memories in a Notion-like system. You first need to connect a session to `Space` to enable the learning process:

```python
# Step 1: Create a Space for skill learning
space = client.spaces.create()
print(f"Created Space: {space.id}")

# Step 2: Create a session attached to the space
session = client.sessions.create(space_id=space.id)

# ... push the agent working context
```

The learning happens in the background and is not real-time (delay around 10-30s). 

What Acontext will do in the background:

```mermaid
graph LR
    A[Task Completed] --> B[Task Extraction]
    B --> C{Space Connected?}
    C -->|Yes| D[Queue for Learning]
    C -->|No| E[Skip Learning]
    D --> F[Extract SOP]
    F --> G{Hard Enough?}
    G -->|No - Too Simple| H[Skip Learning]
    G -->|Yes - Complex| I[Store as Skill Block]
    I --> J[Available for Future Sessions]
```

Eventually, SOP blocks with tool-call pattern will be saved to `Space`. You can view every `Space` in the Dashboard:

<div align="center">
    <picture>
      <img alt="A Space Demo" src="./docs/images/dashboard/skill_viewer.png" width="80%">
    </picture>
  <p>A Space Demo</p>
</div>




### Search Skills from a `Space` [📖](https://docs.acontext.io/learn/search-skills)

To search skills from a `Space` and use them in the next session:

```python
result = client.spaces.experience_search(
    space_id=space.id,
    query="I need to implement authentication",
  	mode="fast"
)
```

Acontext supports `fast` and `agentic` modes for search. The former uses embeddings to match skills. The latter uses an Experience Agent to explore the entire `Space` and tries to cover every skill needed.

The return is a list of sop blocks, which look like below:

```json
{
    "use_when": "star a github repo",
    "preferences": "use personal account. star but not fork",
    "tool_sops": [
        {"tool_name": "goto", "action": "goto the user given github repo url"},
        {"tool_name": "click", "action": "find login button if any, and start to login first"},
        ...
    ]
}
```

</details>







# 🔍 Document

To understand what Acontext can do better, please view [our docs](https://docs.acontext.io/)



# ❤️ Stay Updated

Star Acontext on Github to support and receive instant notifications 

![click_star](./assets/star_acontext.gif)



# 🤝 Stay Together

Join the community for support and discussions:

-   [Discuss with Builders on Acontext Discord](https://discord.gg/rpZs5TaSuV) 👻 
-  [Follow Acontext on X](https://x.com/acontext_io) 𝕏 



# 🌟 Contributing

- Check our [roadmap.md](./ROADMAP.md) first.
- Read [contributing.md](./CONTRIBUTING.md)



# 📑 LICENSE

This project is currently licensed under [Apache License 2.0](LICENSE).



# 🥇 Badges

![Made with Acontext](./assets/badge-made-with-acontext.svg) ![Made with Acontext (dark)](./assets/badge-made-with-acontext-dark.svg)

```md
[![Made with Acontext](https://assets.memodb.io/Acontext/badge-made-with-acontext.svg)](https://acontext.io)

[![Made with Acontext](https://assets.memodb.io/Acontext/badge-made-with-acontext-dark.svg)](https://acontext.io)
```