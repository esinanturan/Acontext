from acontext_server.schema.message.openai import OpenAIMessages


def test_schema_message_openai():
    data = [
        {
            "role": "user",
            "content": "Read into the nano-code lib, and update tests accordingly",
        },
        {
            "content": "I'll help you read through the nano-code library and update the tests accordingly. Let me first explore the project structure to understand what we're working with.\n\n### Plan:\n1. Examine the directory structure to understand the codebase\n2. Look at existing tests to understand their structure\n3. Review the core library code that the tests are testing\n4. Update tests as needed to match the current implementation\n\nLet's start by exploring the project structure:",
            "refusal": None,
            "role": "assistant",
            "annotations": None,
            "audio": None,
            "function_call": None,
            "tool_calls": [
                {
                    "id": "toolu_01U4BkmkpBbLqSgTHduWGbiv",
                    "function": {
                        "arguments": '{"absolute_path":"/Users/gustavoye/Desktop/memodb_w/nano-code"}',
                        "name": "list_dir",
                        "parameters": None,
                    },
                    "type": "function",
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_01U4BkmkpBbLqSgTHduWGbiv",
            "content": "[Listed directory /Users/gustavoye/Desktop/memodb_w/nano-code]\n[dir] rwxr-xr-x     384B 2025-07-15 21:38 .git\n[dir] rwxr-xr-x      96B 2025-07-11 17:14 .github\n[dir] rwxr-xr-x      96B 2025-07-10 22:49 assets\n[dir] rwxr-xr-x     384B 2025-07-10 22:07 nano_code\n[dir] rwxr-xr-x     448B 2025-07-15 21:38 tests\n[file] rw-r--r--     137B 2025-07-11 16:54 .coveragerc\n[file] rw-r--r--    3.5KB 2025-07-12 21:49 .gitignore\n[file] rw-r--r--       5B 2025-06-27 15:00 .python-version\n[file] rw-r--r--    1.1KB 2025-07-15 21:03 LICENSE\n[file] rw-r--r--     556B 2025-07-12 21:50 pyproject.toml\n[file] rw-r--r--    8.2KB 2025-07-15 21:03 README.md\n[file] rw-r--r--  100.3KB 2025-07-15 20:46 uv.lock\n\nTotal: 5 directories, 7 files",
        },
        {
            "content": "Now let's look at the nano_code directory to understand the core library structure:",
            "refusal": None,
            "role": "assistant",
            "annotations": None,
            "audio": None,
            "function_call": None,
            "tool_calls": [
                {
                    "id": "toolu_018eTAZHhzMjbbmdSgN8YBTY",
                    "function": {
                        "arguments": '{"absolute_path":"/Users/gustavoye/Desktop/memodb_w/nano-code/nano_code"}',
                        "name": "list_dir",
                        "parameters": None,
                    },
                    "type": "function",
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_018eTAZHhzMjbbmdSgN8YBTY",
            "content": "[Listed directory /Users/gustavoye/Desktop/memodb_w/nano-code/nano_code]\n[dir] rwxr-xr-x      96B 2025-07-10 18:42 agent\n[dir] rwxr-xr-x     320B 2025-07-10 21:22 agent_tool\n[dir] rwxr-xr-x     160B 2025-07-11 11:35 core\n[dir] rwxr-xr-x     192B 2025-07-09 14:52 llm\n[dir] rwxr-xr-x     224B 2025-07-11 15:16 utils\n[file] rw-r--r--      22B 2025-07-11 15:03 __init__.py\n[file] rw-r--r--    3.2KB 2025-07-11 16:53 __main__.py\n[file] rw-r--r--     291B 2025-07-11 16:33 constants.py\n[file] rw-r--r--    1.5KB 2025-07-12 15:42 env.py\n\nTotal: 5 directories, 4 files",
        },
    ]

    data = OpenAIMessages(messages=data)
    print(data)
