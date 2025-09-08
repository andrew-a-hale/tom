# Tom

Tom is a Raspberry PI server.

## Services

- Chat -- Slack Integration
  - Commands
    - chess
      - start
      - stop
      - fen
      - turn
      - moves
      - last
      - state
      - render
    - diag
      - temp
- Chess -- Remote Chess Recorder
  - Track Game State
  - Notifications via Slack
  - FEN Output (can import into chess.com)
  - Validation with python-chess

### Chat

Slack Chat Bot. Example `/tom start`

### Chess

Service to track a chess board using a video feed. The goal of tracking is to
calculate a FEN for a current position, track the move sequence, and send /
receive messages from Slack.
