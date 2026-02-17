# FastAPI API Gateway
Gateway with smart routing and token-bucket rate limiting for efficient API querying and 
request handling.
## Getting Started
Requires Python >=3.10 and [Redis server](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/#install-redis-open-source)
### Dependencies
I recommend installing the dependencies listed in the requirements file.
Run ```pip install -r requirements.txt``` or your package manager equivalent (I used uv, 
so it'd be ```uv add -r requirements.txt```) from the root directory to install.

For more dependency info, see [requirements.txt](requirements.txt) and [pyproject.toml (\[project\] dependencies)](pyproject.toml).
### Testing
To run the tests, run pytest from the root directory. 