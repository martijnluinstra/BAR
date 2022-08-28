BAR
===

BAR (Beverage Administration Register) is a simple web based system to maintain a counter for each user, which has been used to count the amount of beer each student has consumed during the introductory camp of study association Cover.

## Setup ##
For a development setup, Docker is the easiest solution. Simply run

```
docker compose up
```

and navigate to http://localhost:5000 in your nearest browser.

During the first startup, the `bar` container might quit and restart a few times before the `mariadb` container is fully initialised. After this, the `bar` container should automatically setup a database and start the development server.

If you want more control over the setup and its configuration, copy the `docker-compose.yml` file to `docker-compose.local.yml` and start the stack using the following command:

```
docker compose up -f docker-compose.local.yml
```

Check `config.py.docker` for all available configuration options and environment variables.
