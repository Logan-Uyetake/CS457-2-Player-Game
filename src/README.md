# CS457-2-Player-Game

Terminal-based, two-player Connect Four using TCP sockets and newline-delimited
JSON messages.

## Run locally

Start the server in one terminal:

```text
python server.py -p 8080
```

Connect two clients from separate terminals:

```text
python client.py -i localhost -p 8080
python client.py -i localhost -p 8080
```

Clients may provide a display name with `-n NAME`; otherwise they are prompted
for one. Enter a column number (`0` through `6`) on your turn, or `q` to forfeit.
The first player to connect plays `X` and takes the first turn.

The client resolves the supplied hostname through DNS and reports resolution
failures without printing a traceback. For router-based deployment, configure
the DNS record `server.uyetake.edu` as described in `sow_template.md`.

The TCP protocol and board logic are implemented in `protocol_handler.py` and
`gamestate.py`. The server binds to `0.0.0.0` and uses one worker thread per
connected client.