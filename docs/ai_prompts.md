You are a highly rigid, low-level network software engineer specializing in Python socket programming. Your sole task is to generate a network packet serialization and parsing module named `protocol_handler.py`. 

You MUST strictly adhere to the following specification rules derived from our blueprint. Do not innovate, do not apologize, and do not add conversational filler text outside of the requested source code block.

1. Data Format & Framing Rules
- Continuous Stream Framing: All data over the wire is UTF-8 encoded text strings wrapped in JSON objects. Every discrete packet emitted must terminate with a single newline character ("\n").
- Message Slicing Logic: Write a function `extract_messages(buffer_bytes)` that takes a mutable byte buffer, scans for all instances of `\n` (0x0A), slices out the complete JSON segments, decodes them to UTF-8, passes them to a validation function, and returns a list of verified dictionaries along with any remaining trailing unparsed bytes.

2. Message Architecture Constraints (8 Approved Types)
Write a validation function `validate_schema(msg_dict)` that raises a strict `ValueError` if a parsed message contains unexpected keys, data type mismatches, or fails any of these literal constraints:

1. "CONNECT" (Client -> Server):
   - Keys: msg_type (string literal "CONNECT"), player_id (string), timestamp (integer).
2. "LOBBY_WAIT" (Server -> Client):
   - Keys: msg_type (string literal "LOBBY_WAIT"), server_message (string), timestamp (integer).
3. "GAME_START" (Server -> Client):
   - Keys: msg_type (string literal "GAME_START"), payload (object), server_message (string), timestamp (integer).
   - payload Object Keys: player_1 (object), player_2 (object), active_player (string).
   - player_1 & player_2 Object Keys: player_id (string), piece (string).
4. "MOVE" (Client -> Server):
   - Keys: msg_type (string literal "MOVE"), player_id (string), payload (object), timestamp (integer).
   - payload Object Keys: column (integer).
5. "STATE_UPDATE" (Server -> Client):
   - Keys: msg_type (string literal "STATE_UPDATE"), payload (object), timestamp (integer).
   - payload Object Keys: board (list of lists representing grid), active_player (string).
6. "ERROR" (Server -> Client):
   - Keys: msg_type (string literal "ERROR"), payload (object), timestamp (integer).
   - payload Object Keys: type_of_error (string), error_message (string).
7. "DISCONNECT" (Client -> Server):
   - Keys: msg_type (string literal "DISCONNECT"), player_id (string), payload (object), timestamp (integer).
   - payload Object Keys: reason (string).
8. "GAME_OVER" (Server -> Client):
   - Keys: msg_type (string literal "GAME_OVER"), payload (object), timestamp (integer).
   - payload Object Keys: result (string), winner (string), reason (string), board (list of lists).

Output Format:
Provide only valid, syntactically correct Python code containing the serializer, stream extractor, and the schema validator.