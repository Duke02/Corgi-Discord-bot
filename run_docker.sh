docker build -t corgi-bot .
docker run -dit --rm --name bot-corgi -v corgi-db:/app/db corgi-bot
