# commands.md
I note some commands that might come handy. Nothing is related to the codebase.

## Docker Build Cache Remove
- `docker builder prune --force`
- `docker system prune --all --volumes --force` (Very aggressive)

## Docker Build & Push
- Docker build command: `docker build -t ghcr.io/ridwan0110/sarab_bot:<version> .`
- Add `latest` tag in docker images: `docker tag ghcr.io/ridwan0110/sarab_bot:<version> ghcr.io/ridwan0110/sarab_bot:latest`
- Push to ghcr.io: `docker push ghcr.io/ridwan0110/sarab_bot:<version>`

## Other commands
- View dangling images in docker: `docker images -f 'dangling=true'`
