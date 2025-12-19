.PHONY: update

update:
 git pull origin main
 docker compose down
 docker compose up -d --build
 docker system prune -a --volumes -f