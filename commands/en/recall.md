Search CogniLayer memory for: $ARGUMENTS

If query is empty:
1. Call project_context to display DNA
2. Call session_bridge with action "load" for last bridge
3. Show recent changes from change log

If query is specified:
1. Call memory_search with this query
2. If few results, try file_search
3. If results reference another project, state it explicitly
