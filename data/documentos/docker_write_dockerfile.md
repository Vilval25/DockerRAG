# Write your first Dockerfile

Dominio: docker

Fuente: https://docs.docker.com/learn/content/write-your-first-dockerfile/

You’ve written an app, and it runs on your machine. Getting it to run anywhere
else means a list of instructions: install this version of Node.js, run
`npm ci`, hope the native SQLite module compiles, then start the server. Every
teammate and every CI runner follows that list a little differently, and some
of them get it wrong.

A **Dockerfile** turns that list into a file the computer follows the same
way every time. Docker reads it and produces an **image**: your app, its
dependencies, and the runtime it needs, packaged together. Anyone with Docker
can run that image and get exactly what you built.

In this guide, you’ll write a Dockerfile for a small to-do app, build it into
an image, run it, and call its API to prove it works.

## Before you start

You can follow this whole guide in your browser. The terminals on this page
are simulations: click through them to see what each command does.

To follow along on your own machine, you need:

* **Docker.** Install
  [Docker Desktop or Docker Engine](https://docs.docker.com/get-started/get-docker/).
* **Git,** to clone the sample app.

You don’t need Node.js. Everything the app needs comes from the image.

If containers and images are new to you, read
[What is a container?](/learn/content/what-is-a-container/) first. This
guide assumes you know that a container starts from an image.

## What a Dockerfile is

A Dockerfile is a plain text file, named `Dockerfile` with no extension. Each
line starts with an **instruction** in capitals, followed by its arguments.
Docker runs the instructions from top to bottom, and the result is an image.

Most Dockerfiles follow the same three steps:

1. **Start from a base image** that already has your language’s runtime.
2. **Copy in your app** and **install its dependencies.**
3. **Describe how it runs:** the port it listens on and the command that
   starts it.

Six instructions cover that:

| Instruction | What it does |
| --- | --- |
| `FROM` | Picks the base image to build on top of. Every Dockerfile starts with one. |
| `WORKDIR` | Sets the directory inside the image that later instructions work in. Creates it if it’s missing. |
| `COPY` | Copies files from your project into the image. |
| `RUN` | Runs a command during the build, such as installing packages. Its results are saved in the image. |
| `EXPOSE` | Records which port the app listens on. It’s documentation; it doesn’t publish the port. |
| `CMD` | Sets the default command a container runs when it starts from the image. |

The difference between `RUN` and `CMD` trips people up. `RUN` happens once,
at **build** time, and its output is baked into the image. `CMD` happens
every time a container **starts**, and the image only remembers what the
command is.

## Step 1: Get the app

The sample app is a to-do list with a Node.js backend and a React frontend.
Clone it and change into it:

Your machine

```
git clone https://github.com/docker/getting-started-todo-app
```

```
Cloning into 'getting-started-todo-app'...
```

```
cd getting-started-todo-app
```

The parts that matter for this guide:

* `backend/` is the API server: an Express app in `backend/src/`, with its
  dependencies listed in `backend/package.json` and pinned in
  `backend/package-lock.json`. It stores to-dos in a SQLite database.
* `client/` is the React frontend. You won’t build it in this guide.
* `Dockerfile` is the repository’s own Dockerfile.
* `.dockerignore` lists files Docker should leave out of a build. More on it
  in Step 3.

The repository already has a complete, production-ready Dockerfile. You’re
going to **replace** it with your own, so you can see how one is put together
from nothing. Don’t worry about losing it: `git restore Dockerfile` brings
the original back at any time. It’s a longer, multi-stage version of what
you’re about to write, and worth reading once you’ve finished.

## Step 2: Write the Dockerfile

Open `Dockerfile` in your editor, delete everything in it, and build it up
one instruction at a time.

Start from an image that already has Node.js installed:

```
FROM node:22
```

`node:22` is the Docker Official Image for Node.js 22, from Docker Hub. It
comes with Node.js, npm, and the compilers some npm packages need to build
native code, which is what lets `sqlite3` install cleanly.

Pick a directory inside the image for the app to live in:

```
WORKDIR /usr/local/app
```

Every relative path after this line is relative to `/usr/local/app`, inside
the image.

Copy the backend into that directory:

```
COPY backend ./
```

The first argument is a path in your project. The second is a path in the
image, and `./` means the working directory. After this line, the image has
`/usr/local/app/package.json`, `/usr/local/app/src/`, and the rest of
`backend/`.

Install the dependencies:

```
RUN npm ci
```

This runs inside the image during the build. `npm ci` installs exactly the
versions in `package-lock.json`, so every build gets the same packages.

Finally, describe how the app runs:

```
EXPOSE 3000
CMD ["node", "src/index.js"]
```

The app listens on port 3000, so `EXPOSE` records that. `CMD` is the command
a container runs when it starts. Write it in this bracketed form, called the
*exec form*: Docker runs `node` directly, without a shell in between, so the
app receives stop signals and shuts down cleanly.

The whole file:

```
FROM node:22
WORKDIR /usr/local/app
COPY backend ./
RUN npm ci
EXPOSE 3000
CMD ["node", "src/index.js"]
```

Save it. Make sure your editor didn’t add an extension: the file must be
called exactly `Dockerfile`.

## Step 3: Build the image

From the project’s root directory, build the image:

Your machine

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

```
docker image ls todo-app
```

```
IMAGE             ID             DISK USAGE   CONTENT SIZE   EXTRA
todo-app:latest   7f779016ff2d       1.87GB          449MB
```

The first build takes a minute or so, most of it in `npm ci`. If you’ve never
pulled `node:22`, Docker downloads it first, which adds a little more.

Read the output from the `[1/4]` line down. Each of your four build steps is
numbered. `EXPOSE` and `CMD` don’t get a number, because they don’t produce
files, only settings recorded in the image. Your timings and IDs will differ.

The command has two parts worth knowing:

* **`-t todo-app`** tags the image with a name, so you can refer to it as
  `todo-app` instead of by its ID. Docker adds the tag `latest` when you
  don’t give one, which is why the image is `todo-app:latest`.
* **The `.` at the end** is the **build context**, which the next section
  explains.

tip

**See every build in Docker Desktop.** If you use Docker Desktop, the
[Builds view](https://docs.docker.com/desktop/use-desktop/builds/) lists
your builds, with each one’s logs, timing, and the Dockerfile it used.

### The build context and `.dockerignore`

Docker doesn’t read your files directly. The build runs in a component called
the **builder**, and `docker build` sends it a copy of a directory, the build
context. The `.` means “the current directory”. `COPY` can only reach files
inside the context, which is why `COPY backend ./` works and `COPY ../secret ./`
wouldn’t.

Everything in the context gets sent, whether the Dockerfile uses it or not.
A context full of build output, logs, or a local `node_modules` folder makes
every build slower, and anything secret in it, such as a `.env` file, is one
careless `COPY` away from ending up in the image.

A `.dockerignore` file in the context’s root keeps files out. It works like
`.gitignore`. The one in this repository has a single line:

```
node_modules
```

That’s why the build output shows only a couple of hundred kilobytes of
context: your source code, without any `node_modules`. A local
`node_modules` stays on your machine, and `npm ci` installs a clean set
inside the image instead. Build again and Docker sends only what changed, so
later builds show even less.

note

**A plain name matches only at the root.** `node_modules` excludes
`./node_modules`, but not `./backend/node_modules`. If you ran `npm install`
inside `backend/`, that folder would still be sent to the builder. Write
`**/node_modules` to match it at any depth. See
[Build context](https://docs.docker.com/build/concepts/context/#dockerignore-files)
for the full pattern syntax.

## Step 4: Run it and call the API

Start a container from your image, publishing the app’s port to the same
port on your machine:

Your machine

```
docker run -d --name todo -p 3000:3000 todo-app
```

```
1c5898e8a5aedcef267aa6a0133675d4caadbca870765d5329d57dc4479eac43
```

```
docker logs todo
```

```
Using sqlite database at /etc/todos/todo.db
Listening on port 3000
```

`-d` runs it in the background, `--name todo` names the container, and
`-p 3000:3000` connects port 3000 on your machine to port 3000 in the
container. Remember that `EXPOSE` didn’t do this: only `-p` publishes a port.
The logs show the app started and is using SQLite. To learn more about these
flags, see [Run your first container](/learn/content/run-your-first-container/).

Now prove the image works. Ask the API for its greeting, add a to-do, and
read it back:

Your machine

```
curl http://localhost:3000/api/greeting
```

```
{"greeting":"Hello world!"}
```

```
curl -X POST http://localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Write a Dockerfile"}'
```

```
{"id":"a05e4e2a-3f50-438d-a878-8986f53a98bc","name":"Write a Dockerfile","completed":false}
```

```
curl http://localhost:3000/api/items
```

```
[{"id":"a05e4e2a-3f50-438d-a878-8986f53a98bc","name":"Write a Dockerfile","completed":false}]
```

Your code, its dependencies, and Node.js are all inside the image, and none
of them needed installing on your machine.

Now open <http://localhost:3000> in your browser, or ask for it with `curl`:

Your machine

```
curl http://localhost:3000/
```

```
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error</title>
</head>
<body>
<pre>Cannot GET /</pre>
</body>
</html>
```

A 404. This is expected, and it’s a limit of the Dockerfile you wrote, not a
broken step. The backend serves the web page from `backend/src/static/`, and
that folder is empty until someone builds the React frontend in `client/`.
Your Dockerfile never does. Building the frontend needs a second set of tools
that the running app doesn’t, which is exactly what a multi-stage build is
for. [Shrink your image with multi-stage builds](/learn/content/shrink-your-image-with-multi-stage-builds/)
adds it.

## The default command: CMD and ENTRYPOINT

`CMD` is only a **default**. Anything you type after the image name in
`docker run` replaces it. Ask the image which Node.js it has, instead of
starting the server:

Your machine

```
docker run --rm todo-app node --version
```

```
v22.23.4
```

```
docker image inspect --format '{{json .Config.Entrypoint}} {{json .Config.Cmd}}' todo-app
```

```
["docker-entrypoint.sh"] ["node","src/index.js"]
```

`--rm` removes the container as soon as it exits. The second command shows
the two settings that together decide what a container runs:

* **`ENTRYPOINT`** is the executable that always runs. Your Dockerfile
  didn’t set one; it came from `node:22`, whose `docker-entrypoint.sh` does a
  little setup and then runs whatever it’s given.
* **`CMD`** is the arguments handed to the entrypoint, and the part
  `docker run` replaces. Your `CMD` is `node src/index.js`.

Use `CMD` for the normal way to start your app, as you did here. Reach for
`ENTRYPOINT` when the image is a wrapper around one program, such as a CLI
tool, so that `docker run my-tool --help` passes `--help` to the tool. You
can still replace an entrypoint with `docker run --entrypoint`.

Two more instructions you’ll meet often:

* **`ENV`** sets an environment variable in the image, for later build steps
  and for every container. For example, `ENV NODE_ENV=production` tells many
  Node.js libraries to run in production mode.
* **`USER`** sets which user later instructions and the container run as.
  Your image runs as `root`, the default. The `node:22` image includes a
  non-root `node` user, but adding `USER node` here on its own breaks the
  app: it fails with `EACCES: permission denied, mkdir '/etc/todos'`,
  because only `root` can create the database directory. The user you switch
  to must be able to write wherever the app writes.

See the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
for every instruction and its options.

## Clean up

Remove the container. `-f` stops it first:

Your machine

```
docker rm -f todo
```

```
todo
```

Keep the `todo-app` image and your Dockerfile if you’re carrying on, because
the next guide starts from this Dockerfile. When you want the repository’s
original Dockerfile back, run `git restore Dockerfile`.

## What you built, and its limits

Your six-line Dockerfile turns the backend’s source into an image that runs
anywhere Docker does. It works, but it isn’t finished:

* **It serves only the API.** The frontend never gets built.
* **Rebuilds are slow.** Change one line of `backend/src/` and the build
  reruns `npm ci` from scratch.
* **It’s big.** The image carries compilers, npm’s dev dependencies, and the
  rest of a full Debian system, about 1.87 GB on disk, none of which the app
  needs to run.
* **It runs as root.** That needs the app’s data directory set up for
  another user, which is beyond this path.

The rest of this path fixes the first three, one at a time.
