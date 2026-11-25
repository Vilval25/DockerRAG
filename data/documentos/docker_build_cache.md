# Image layers and the build cache

Dominio: docker

Fuente: https://docs.docker.com/learn/content/how-image-layers-and-the-build-cache-work/

You change one line in a route handler, rebuild your image, and wait 40
seconds while `npm ci` installs every dependency again. Nothing about your
dependencies changed. So why did Docker redo the slowest step?

The answer is in how an image is put together. Each instruction in a
Dockerfile produces a **layer**, and Docker reuses a layer from an earlier
build only when nothing it depends on has changed. Once you know which
changes break that reuse, you can order a Dockerfile so everyday edits
rebuild in a fraction of a second.

In this guide, you’ll build the image for a small to-do app, look at its
layers, watch one source edit rerun `npm ci`, and then reorder the Dockerfile
so the same edit skips it.

## Before you start

You can follow this whole guide in your browser. The terminals on this page
are simulations: click through them to see what each command does and what it
prints.

To run it for real on your own machine, you need:

* **Docker,** either Docker Desktop or Docker Engine. See
  [Get Docker](https://docs.docker.com/get-started/get-docker/).
* **Git,** to clone the sample app.

Your output will differ in the details: IDs, digests, timings, and sizes
depend on your machine and the current `node:22` image.

### Get the sample app and a starting Dockerfile

The sample is a to-do app with a Node.js backend. Clone it and change into
its directory:

```
$ git clone https://github.com/docker/getting-started-todo-app
$ cd getting-started-todo-app
```

The repository ships its own `Dockerfile`, a complete production version with
several stages. Replace its contents with this short one, which builds only
the backend API:

```
FROM node:22
WORKDIR /usr/local/app
COPY backend ./
RUN npm ci
EXPOSE 3000
CMD ["node", "src/index.js"]
```

It starts from the official Node.js image, copies the whole `backend`
directory in, installs the dependencies, and starts the server. This is the
Dockerfile written in
[Write your first Dockerfile](/learn/content/write-your-first-dockerfile/).
When you’re done, `git restore Dockerfile` brings back the original.

## Step 1: Build the image

Build the image and tag it `todo-app`:

getting-started-todo-app

```
docker build -t todo-app .
```

```
[+] Building 45.3s (9/9) FINISHED                docker:default
 => [internal] load build definition from Dockerfile       0.0s
 => => transferring dockerfile: 141B                       0.0s
 => [internal] load metadata for docker.io/library/node:2  0.0s
 => [internal] load .dockerignore                          0.0s
 => => transferring context: 52B                           0.0s
 => [1/4] FROM docker.io/library/node:22@sha256:82693da96  4.3s
 => => resolve docker.io/library/node:22@sha256:82693da96  0.0s
 => [internal] load build context                          0.0s
 => => transferring context: 237.95kB                      0.0s
 => [2/4] WORKDIR /usr/local/app                           0.2s
 => [3/4] COPY backend ./                                  0.0s
 => [4/4] RUN npm ci                                      37.3s
 => exporting to image                                     3.5s
 => => exporting layers                                    2.6s
 => => exporting manifest sha256:68724f3029c38a41ec4dec67  0.0s
 => => exporting config sha256:4b020f2d0b8a6009119f56fc5d  0.0s
 => => exporting attestation manifest sha256:b50cf535b760  0.0s
 => => exporting manifest list sha256:7f779016ff2dd746ba8  0.0s
 => => naming to docker.io/library/todo-app:latest         0.0s
 => => unpacking to docker.io/library/todo-app:latest      0.9s
```

The numbered lines, `[1/4]` to `[4/4]`, are the four instructions that change
the image’s filesystem. `RUN npm ci` takes almost all of the time. If you
didn’t have `node:22` yet, your build also downloads it first. Docker cuts long
lines to fit your terminal, so a wider window shows more of each one.

If you built this same Dockerfile in
[Write your first Dockerfile](/learn/content/write-your-first-dockerfile/),
every step says `CACHED` instead and the build finishes almost instantly.
That’s the build cache, and Step 3 explains it.

## Step 2: Look at the layers

An image isn’t one big file. It’s an ordered stack of **layers**, each one a
set of filesystem changes: files added, changed, or deleted. Each Dockerfile
instruction that changes files produces one layer, and once a layer is
created, it never changes.

`docker image history` lists an image’s layers, newest first. The `--format`
option here keeps just two columns: the instruction that made each layer and
the layer’s size.

getting-started-todo-app

```
docker image history --format 'table {{.CreatedBy}}\t{{.Size}}' todo-app
```

```
CREATED BY                                      SIZE
CMD ["node" "src/index.js"]                     0B
EXPOSE [3000/tcp]                               0B
RUN /bin/sh -c npm ci # buildkit                202MB
COPY backend ./ # buildkit                      332kB
WORKDIR /usr/local/app                          16.4kB
CMD ["node"]                                    0B
ENTRYPOINT ["docker-entrypoint.sh"]             0B
COPY docker-entrypoint.sh /usr/local/bin/ # …   20.5kB
RUN /bin/sh -c set -ex   && export GNUPGHOME…   5.41MB
ENV YARN_VERSION=1.22.22                        0B
RUN /bin/sh -c ARCH= && dpkgArch="$(dpkg --p…   210MB
ENV NODE_VERSION=22.23.4                        0B
RUN /bin/sh -c groupadd --gid 1000 node   &&…   69.6kB
RUN /bin/sh -c set -ex;  apt-get update;  ap…   592MB
RUN /bin/sh -c set -eux;  apt-get update;  a…   200MB
RUN /bin/sh -c set -eux;  apt-get update;  a…   51.6MB
# debian.sh --arch 'arm64' out/ 'bookworm' '…   155MB
```

Read it from the bottom up:

* **The bottom twelve rows are `node:22`.** Your `FROM` line didn’t copy
  Node.js into your image. It started your image on top of the Node.js
  image’s layers, which in turn start from a Debian base.
* **The top five rows are your Dockerfile,** one row per instruction.
* **`RUN npm ci` is the big one,** at 202MB of `node_modules`. `COPY backend ./`
  is only 332kB.
* **`EXPOSE` and `CMD` are 0B.** They set metadata, such as the default
  command, and don’t change any files.

Without `--format`, you also get an `IMAGE` column, where every row but the
top one says `<missing>`. That isn’t an error: only the top row is a whole
image with its own ID, and the rows below it are layers.

tip

**See layers in Docker Desktop.** In the **Images** view, select an image to
open its detail page, which shows the image history and the layers that make
up the image.

### Layers are shared between images

Every layer is stored by a digest of its contents, so two identical layers are
the same layer, stored once. Any image built `FROM node:22` reuses the exact
layers that `node:22` has, rather than a copy of them.

You can see it. Pull `node:22` so it has a name to inspect. You already have
its layers from the build, so nothing new downloads. Then list each image’s
layer digests. The `slice . 7 19` in the format keeps 12 characters of each
digest, after the `sha256:` prefix, so the lists are easy to compare:

getting-started-todo-app

```
docker pull node:22
```

```
22: Pulling from library/node
Digest: sha256:82693da96a4e38b8c0e2bf0c5df58fcb86d2d25e5a235c07748f09bfa38567c2
Status: Downloaded newer image for node:22
docker.io/library/node:22
```

```
docker image inspect --format '{{range .RootFS.Layers}}{{println (slice . 7 19)}}{{end}}' node:22
```

```
c02bc3f14703
9ade96a84784
d20b95c67d4c
66aa398e3433
289984d07238
7332fdc533b1
111410733367
0338d381cd70
```

```
docker image inspect --format '{{range .RootFS.Layers}}{{println (slice . 7 19)}}{{end}}' todo-app
```

```
c02bc3f14703
9ade96a84784
d20b95c67d4c
66aa398e3433
289984d07238
7332fdc533b1
111410733367
0338d381cd70
d369ca573aa2
acf2a9b942d7
70f4234dee13
```

The first eight digests are identical: those are the `node:22` layers, shared.
`todo-app` adds three of its own on top, for `WORKDIR`, `COPY`, and
`RUN npm ci`. Ten images built on `node:22` store its 1.2GB once, and pulling
another one downloads only the layers you don’t have yet.

### A container adds one writable layer

Image layers are read-only, so where does a running container write? When
Docker starts a container, it adds a thin **writable layer** on top of the
image’s layers and presents the whole stack as one filesystem. Reads fall
through to the highest layer that has the file. Writes, including changes to
files that came from the image, land in the writable layer.

Start a container from the image and see it. `docker diff` lists what the
container has changed relative to its image, which is exactly what’s in its
writable layer:

getting-started-todo-app

```
docker run -d --name todo -p 3000:3000 todo-app
```

```
8f72471d84f325ce2d4e6b460f1aa1c04f725da673e0cfc593f936b254854152
```

```
docker diff todo
```

```
C /etc
A /etc/todos
A /etc/todos/todo.db
```

```
docker ps -s --filter name=todo --format 'table {{.Names}}\t{{.Image}}\t{{.Size}}'
```

```
NAMES   IMAGE      SIZE
todo    todo-app   20.5kB (virtual 1.42GB)
```

```
docker rm -f todo
```

```
todo
```

On startup, the app created its SQLite database at `/etc/todos/todo.db`
(`A` for added, `C` for changed). That file lives only in this container’s
writable layer: 20.5kB on top of a 1.42GB image that every container from
`todo-app` shares. Removing the container deletes its writable layer and the
database with it, while the image stays exactly as it was.

tip

To keep data such as that database after its container is removed, store it
in a volume. See
[Keep data with volumes and bind mounts](/learn/content/keep-data-with-volumes-and-bind-mounts/).

## Step 3: Watch the cache at work

Because layers never change, Docker can keep the result of each build step in
its **build cache** and reuse it the next time. Build again without changing
anything:

getting-started-todo-app

```
docker build -t todo-app .
```

```
[+] Building 0.0s (9/9) FINISHED                 docker:default
 => [internal] load build definition from Dockerfile       0.0s
 => => transferring dockerfile: 141B                       0.0s
 => [internal] load metadata for docker.io/library/node:2  0.0s
 => [internal] load .dockerignore                          0.0s
 => => transferring context: 52B                           0.0s
 => [1/4] FROM docker.io/library/node:22@sha256:82693da96  0.0s
 => => resolve docker.io/library/node:22@sha256:82693da96  0.0s
 => [internal] load build context                          0.0s
 => => transferring context: 1.16kB                        0.0s
 => CACHED [2/4] WORKDIR /usr/local/app                    0.0s
 => CACHED [3/4] COPY backend ./                           0.0s
 => CACHED [4/4] RUN npm ci                                0.0s
 => exporting to image                                     0.0s
 => => exporting layers                                    0.0s
 => => exporting manifest sha256:68724f3029c38a41ec4dec67  0.0s
 => => exporting config sha256:4b020f2d0b8a6009119f56fc5d  0.0s
 => => exporting attestation manifest sha256:36ad2941af4a  0.0s
 => => exporting manifest list sha256:e6a550685bbf22158c0  0.0s
 => => naming to docker.io/library/todo-app:latest         0.0s
 => => unpacking to docker.io/library/todo-app:latest      0.0s
```

Every step is `CACHED`, and the build finishes almost instantly. Now make the change
from the start of this guide. Open `backend/src/routes/getGreeting.js` and
change its greeting:

```
- const GREETING = 'Hello world!';
+ const GREETING = 'Hello from my own image!';
```

Before you rebuild, predict: which steps run again?

getting-started-todo-app

```
docker build -t todo-app .
```

```
[+] Building 41.0s (9/9) FINISHED                docker:default
 => [internal] load build definition from Dockerfile       0.0s
 => => transferring dockerfile: 141B                       0.0s
 => [internal] load metadata for docker.io/library/node:2  0.0s
 => [internal] load .dockerignore                          0.0s
 => => transferring context: 52B                           0.0s
 => [1/4] FROM docker.io/library/node:22@sha256:82693da96  0.0s
 => => resolve docker.io/library/node:22@sha256:82693da96  0.0s
 => [internal] load build context                          0.0s
 => => transferring context: 1.31kB                        0.0s
 => CACHED [2/4] WORKDIR /usr/local/app                    0.0s
 => [3/4] COPY backend ./                                  0.1s
 => [4/4] RUN npm ci                                      37.4s
 => exporting to image                                     3.5s
 => => exporting layers                                    2.6s
 => => exporting manifest sha256:99e896900b30ab2735cec547  0.0s
 => => exporting config sha256:c7977a8a2b83abb3ecacde3545  0.0s
 => => exporting attestation manifest sha256:756827e0190b  0.0s
 => => exporting manifest list sha256:46c7a4ca950e4b321cd  0.0s
 => => naming to docker.io/library/todo-app:latest         0.0s
 => => unpacking to docker.io/library/todo-app:latest      0.8s
```

`COPY backend ./` ran again, which makes sense: one of the files it copies
changed. But `RUN npm ci` ran again too, for almost 40 seconds, even though
`package.json` and `package-lock.json` didn’t change.

That’s the rule of the build cache:

* **A step reruns when the step itself or its inputs change.** For `COPY`,
  the inputs are the files it copies: Docker checksums their contents and
  metadata such as permissions. For `RUN`, the input is the command text.
* **Once a step reruns, every step after it reruns too.** Each layer is built
  on top of the one before it. A new `COPY` layer means `npm ci` is running on
  a different filesystem, so its cached result no longer applies.

`COPY backend ./` copies your source code and your dependency list in one
step, so every source edit invalidates it, and `npm ci` goes with it.

Try it on both versions of the Dockerfile. Pick a tab, change a file, and see
which steps come from the cache. The timings are from the real builds on this
page.

## Step 4: Copy the dependency list first

The fix is to split the copy in two. Copy only the files `npm ci` needs,
install, and copy your source code afterward. Replace the Dockerfile with:

```
FROM node:22
WORKDIR /usr/local/app
COPY backend/package.json backend/package-lock.json ./
RUN npm ci
COPY backend/src ./src
EXPOSE 3000
CMD ["node", "src/index.js"]
```

Now `npm ci` depends only on `package.json` and `package-lock.json`. Source
edits change the last `COPY`, which comes after the install. As a bonus, the
tests in `backend/spec/` no longer end up in the image at all.

Build it. You changed the Dockerfile, so this build runs `npm ci` once more:

getting-started-todo-app

```
docker build -t todo-app .
```

```
[+] Building 40.9s (10/10) FINISHED              docker:default
 => [internal] load build definition from Dockerfile       0.0s
 => => transferring dockerfile: 205B                       0.0s
 => [internal] load metadata for docker.io/library/node:2  0.0s
 => [internal] load .dockerignore                          0.0s
 => => transferring context: 52B                           0.0s
 => [1/5] FROM docker.io/library/node:22@sha256:82693da96  0.0s
 => => resolve docker.io/library/node:22@sha256:82693da96  0.0s
 => [internal] load build context                          0.0s
 => => transferring context: 761B                          0.0s
 => CACHED [2/5] WORKDIR /usr/local/app                    0.0s
 => [3/5] COPY backend/package.json backend/package-lock.  0.1s
 => [4/5] RUN npm ci                                      37.3s
 => [5/5] COPY backend/src ./src                           0.0s
 => exporting to image                                     3.4s
 => => exporting layers                                    2.6s
 => => exporting manifest sha256:f89d853025ea032b89aaa3ab  0.0s
 => => exporting config sha256:447d86c153b83797c1aa6cb30b  0.0s
 => => exporting attestation manifest sha256:8d84ad15c9a0  0.0s
 => => exporting manifest list sha256:4dff38849d91dee3390  0.0s
 => => naming to docker.io/library/todo-app:latest         0.0s
 => => unpacking to docker.io/library/todo-app:latest      0.9s
```

## Step 5: Prove the edit skips the install

Edit the greeting in `backend/src/routes/getGreeting.js` again:

```
- const GREETING = 'Hello from my own image!';
+ const GREETING = 'Hello again from my own image!';
```

Rebuild:

getting-started-todo-app

```
docker build -t todo-app .
```

```
[+] Building 0.1s (10/10) FINISHED               docker:default
 => [internal] load build definition from Dockerfile       0.0s
 => => transferring dockerfile: 205B                       0.0s
 => [internal] load metadata for docker.io/library/node:2  0.0s
 => [internal] load .dockerignore                          0.0s
 => => transferring context: 52B                           0.0s
 => [1/5] FROM docker.io/library/node:22@sha256:82693da96  0.0s
 => => resolve docker.io/library/node:22@sha256:82693da96  0.0s
 => [internal] load build context                          0.0s
 => => transferring context: 917B                          0.0s
 => CACHED [2/5] WORKDIR /usr/local/app                    0.0s
 => CACHED [3/5] COPY backend/package.json backend/packag  0.0s
 => CACHED [4/5] RUN npm ci                                0.0s
 => [5/5] COPY backend/src ./src                           0.1s
 => exporting to image                                     0.0s
 => => exporting layers                                    0.0s
 => => exporting manifest sha256:29a4694587cba5ccc847dc75  0.0s
 => => exporting config sha256:5d5b78917b3fb38c8536dce5b2  0.0s
 => => exporting attestation manifest sha256:492a9bbea4fa  0.0s
 => => exporting manifest list sha256:7b17aea2e02c4ccbdf7  0.0s
 => => naming to docker.io/library/todo-app:latest         0.0s
 => => unpacking to docker.io/library/todo-app:latest      0.0s
```

`RUN npm ci` is `CACHED`, and only `COPY backend/src ./src` ran. The same edit
that cost 41 seconds before now builds in a fraction of a second.

A fast build is only useful if the change made it in. Run the new image and
ask the API for its greeting:

getting-started-todo-app

```
docker run -d --name todo -p 3000:3000 todo-app
```

```
5fe97add814d077b15456f44155168d08e00bb25e44c2c86fda1844028cf61bc
```

```
curl http://localhost:3000/api/greeting
```

```
{"greeting":"Hello again from my own image!"}
```

The new greeting is there, served from fresh source code on top of the
`node_modules` layer from the earlier build.

tip

**See cache usage in Docker Desktop.** The **Builds** view lists your recent
builds. Open one, and the **Build timing** section of its **Info** tab charts
how much of the build came from the cache.

## What to remember

The build cache works step by step, from the top of the Dockerfile down. So
order your instructions from what changes least to what changes most:

1. The base image, then system packages and tools.
2. Your dependency manifests, such as `package.json` and the lockfile, and
   the install step that reads them.
3. Your source code, last.

Two limits are worth knowing:

* **A cached `RUN` doesn’t notice the outside world change.** Docker compares
  the command text, not what the command would download. `RUN apt-get update`
  or an install of “the latest” version keeps its cached result until a step
  before it changes, or you build with `--no-cache`.
* **Copy only what the image needs.** Anything a `COPY` includes is an input
  to that step. List large or noisy directories, such as `node_modules`, in
  `.dockerignore` so they never reach the build at all. The sample repository’s
  `.dockerignore` already excludes `node_modules`.

## Clean up

Remove the container, and bring back the repository’s original files:

getting-started-todo-app

```
docker rm -f todo
```

```
todo
```

```
git restore Dockerfile backend/src/routes/getGreeting.js
```

The original `Dockerfile` is a complete, multi-stage production version. It
uses the same trick you just learned: each stage copies its `package.json`
and lockfile before installing.
