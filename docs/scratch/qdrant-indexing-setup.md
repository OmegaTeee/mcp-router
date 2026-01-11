## 1. Make Sure Colima Is Running

Run:

```bash
colima status
```

If it is not running, start it with Docker runtime:

```bash
colima stop            # optional, to reset
colima start --runtime docker
```

This should create `~/.colima/default/docker.sock` and start the Docker daemon inside Colima.[^2_3][^2_1]

## 2. Verify the socket path

Check that the socket now exists:

```bash
ls -l ~/.colima/default/docker.sock
```

If this file is missing even after `colima start --runtime docker`, something is wrong with the Colima VM and you may need to:

```bash
colima delete
colima start --runtime docker
```

Deleting recreates the VM and its socket.[^2_4][^2_1]

## 3. Point Docker to Colima

If you are using the Docker CLI directly, make sure the context or env matches Colima's socket:

```bash
docker context use colima
```

or set the environment variable:

```bash
export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
```

This aligns the Docker client with Colima's socket path.[^2_5][^2_6]

## 4. If a tool hardcodes the socket

Some tools assume `/var/run/docker.sock`. You can symlink Colima's socket:

```bash
sudo ln -sf "$HOME/.colima/default/docker.sock" /var/run/docker.sock
sudo chown "$(whoami)" /var/run/docker.sock
```

This makes `/var/run/docker.sock` point to Colima's socket and fixes many "no such file or directory" issues.[^2_7][^2_8][^2_9]

If you share which command or app produced this error (Docker CLI, qdrant, some dev tool), a more tailored fix (context/env or config snippet) can be provided.

<div align="center">⁂</div>

[^2_1]: https://linuxcommandlibrary.com/man/colima

[^2_2]: https://bahmni.atlassian.net/wiki/spaces/BAH/pages/3225583617/Running+Bahmni+Docker+using+Colima

[^2_3]: https://stackoverflow.com/questions/75448509/how-to-manage-colima-docker-effectively

[^2_4]: https://github.com/abiosoft/colima/issues/94

[^2_5]: https://github.com/abiosoft/colima/issues/958

[^2_6]: https://stackoverflow.com/questions/72557053/why-does-colima-failed-to-find-docker-daemon

[^2_7]: https://github.com/abiosoft/colima/discussions/139

[^2_8]: https://harivenu.com/article/using-lando-colima-macos-quick-fix-docker-socket-issues

[^2_9]: https://github.com/abiosoft/colima/issues/1309

[^2_10]: https://github.com/abiosoft/colima/issues/365

[^2_11]: https://stackoverflow.com/questions/29349112/var-run-docker-sock-no-such-file-or-directory-are-you-trying-to-connect-to-a

[^2_12]: https://ask.csdn.net/questions/8601411

[^2_13]: https://forums.docker.com/t/is-a-missing-docker-sock-file-a-bug/134351

[^2_14]: https://velog.io/@ahz/Docker-Cannot-connect-to-the-Docker-daemon-at-unix.colimadefaultdocker.sock.-Mac-M2

[^2_15]: https://www.reddit.com/r/docker/comments/yfhocb/cannot_connect_to_the_docker_daemon_at/

# How to Setup Qdrant Locally

The easiest way to run Qdrant locally is via Docker: pull the image, run the container with a mounted volume for data, then connect on port 6333 with your client of choice.[^1_1][^1_2]

> Below assumes you already have Docker installed.

## 1. Create a data directory

From your project or dev folder:

```bash
mkdir -p qdrant_storage
```

This will hold Qdrant's persisted data so you do not lose it when the container restarts.[^1_2][^1_1]

## 2. Pull the Qdrant image

```bash
docker pull qdrant/qdrant
```

This fetches the latest stable Qdrant server image from Docker Hub.[^1_1][^1_2]

## 3. Run Qdrant locally

Basic run (REST only):

```bash
docker run \
  -p 6333:6333 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant
```

- REST API and Web UI will be at `http://localhost:6333` (dashboard at `/dashboard`).[^1_2][^1_1]
- Data is stored in `./qdrant_storage` on your host.[^1_1][^1_2]

REST + gRPC (if you want gRPC clients):

```bash
docker run \
  -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant
```

## 4. Optional: custom config

If you want to tweak config (ports, storage path, limits), create a `custom_config.yaml`, then:

```bash
docker run \
  -p 6333:6333 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  -v "$(pwd)/custom_config.yaml:/qdrant/config/production.yaml" \
  qdrant/qdrant
```

Qdrant will start with your configuration instead of the default one.[^1_2]

## 5. Connect from code

### Python

```bash
pip install "qdrant-client[fastembed]"
```

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
```

The client will talk to your local Qdrant over REST on port 6333.[^1_5][^1_1]

### TypeScript/Node

```bash
npm install @qdrant/js-client-rest
```

```ts
import { QdrantClient } from "@qdrant/js-client-rest";

const client = new QdrantClient({ host: "localhost", port: 6333 });
```

This uses the REST API exposed on your mapped port.[^1_1]

## 6. Pure local (no server, dev only)

For quick prototyping in Python, you can run Qdrant in‑process:

```python
from qdrant_client import QdrantClient

# Pure in-memory DB
qdrant = QdrantClient(":memory:")

# Or embedded on disk
qdrant = QdrantClient(path="path/to/local_qdrant")
```

This avoids Docker entirely and is convenient for tests or small local experiments.[^1_5]

If you share your OS (macOS, Linux, Windows) and whether you prefer Docker or a native binary, a tailored command stack and a basic `docker-compose.yml` can be sketched.
If you share your OS (macOS, Linux, Windows) and whether you prefer Docker or a native binary, a tailored command stack and a basic `docker-compose.yml` can be sketched. For additional background and walkthroughs, see these resources:[^1_3][^1_4][^1_6][^1_7][^1_8][^1_9][^1_10]
<div align="center">⁂</div>

[^1_1]: https://qdrant.tech/documentation/quickstart/

[^1_2]: https://qdrant.tech/documentation/guides/installation/

[^1_3]: https://scaibu.medium.com/how-to-get-started-with-qdrant-locally-94b127e75fb9

[^1_4]: https://airbyte.com/tutorials/beginners-guide-to-qdrant

[^1_5]: https://blog.futuresmart.ai/comprehensive-guide-to-qdrant-vector-db-installation-and-setup

[^1_6]: https://github.com/orgs/qdrant/discussions/2772

[^1_7]: https://stackoverflow.com/questions/79451505/how-can-i-install-qdrant-without-docker

[^1_8]: https://www.youtube.com/watch?v=mHrwS6ZoNKc

[^1_9]: https://www.youtube.com/watch?v=uywdHX9Nnxg

[^1_10]: https://community.n8n.io/t/qdrant-api-key-from-self-hosted-ai-starter-kitq/53700

---

That error means Colima's Docker VM (and its socket) is not running or not where your Docker client expects it to be.[^2_1][^2_2]

Errors indicating Docker cannot connect to the daemon or its socket usually mean Colima's Docker VM (and its socket) is not running or not where your Docker client expects it to be.[^2_1][^2_2]
